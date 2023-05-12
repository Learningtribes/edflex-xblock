import logging
import emoji
from celery.decorators import periodic_task
from celery.schedules import crontab
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.djangoapps.site_configuration.models import SiteConfiguration
from xmodule.modulestore.django import modulestore
from xmodule.modulestore import ModuleStoreEnum
from courseware.courses import get_course

from .api import EdflexOauthClient
from .models import Category, Resource
from .utils import (
    EDFLEX_CLIENT_ID,
    EDFLEX_CLIENT_SECRET,
    EDFLEX_LOCALE,
    EDFLEX_BASE_API_URL,
    get_edflex_configuration_for_org
)

log = logging.getLogger('edflex_xblock')

# default 'At 01:00 on day-of-month 1'
EDFLEX_RESOURCES_UPDATE_CRON = settings.XBLOCK_SETTINGS.get('EdflexXBlock', {}).get('EDFLEX_RESOURCES_UPDATE_CRON', {})
update_resources_cron = {
    'minute': str(EDFLEX_RESOURCES_UPDATE_CRON.get('MINUTE', '0')),
    'hour': str(EDFLEX_RESOURCES_UPDATE_CRON.get('HOUR', '1')),
    'day_of_month': str(EDFLEX_RESOURCES_UPDATE_CRON.get('DAY_OF_MONTH', '1')),
    'month_of_year': str(EDFLEX_RESOURCES_UPDATE_CRON.get('MONTH_OF_YEAR', '*')),
    'day_of_week': str(EDFLEX_RESOURCES_UPDATE_CRON.get('DAY_OF_WEEK', '*')),
}

# default 'At 01:00 on Monday'
EDFLEX_RESOURCES_FETCH_CRON = settings.XBLOCK_SETTINGS.get('EdflexXBlock', {}).get('EDFLEX_RESOURCES_FETCH_CRON', {})
fetch_edflex_data_cron = {
    'minute': str(EDFLEX_RESOURCES_FETCH_CRON.get('MINUTE', '0')),
    'hour': str(EDFLEX_RESOURCES_FETCH_CRON.get('HOUR', '1')),
    'day_of_month': str(EDFLEX_RESOURCES_FETCH_CRON.get('DAY_OF_MONTH', '*')),
    'month_of_year': str(EDFLEX_RESOURCES_FETCH_CRON.get('MONTH_OF_YEAR', '*')),
    'day_of_week': str(EDFLEX_RESOURCES_FETCH_CRON.get('DAY_OF_WEEK', '1')),
}

# default 'At minute 0 past every hour.'
EDFLEX_NEW_RESOURCES_FETCH_CRON = settings.XBLOCK_SETTINGS.get(
    'EdflexXBlock', {}
).get(
    'EDFLEX_NEW_RESOURCES_FETCH_CRON', {}
)
fetch_new_edflex_data_cron = {
    'minute': str(EDFLEX_RESOURCES_FETCH_CRON.get('MINUTE', '0')),
    'hour': str(EDFLEX_RESOURCES_FETCH_CRON.get('HOUR', '*/1')),
    'day_of_month': str(EDFLEX_RESOURCES_FETCH_CRON.get('DAY_OF_MONTH', '*')),
    'month_of_year': str(EDFLEX_RESOURCES_FETCH_CRON.get('MONTH_OF_YEAR', '*')),
    'day_of_week': str(EDFLEX_RESOURCES_FETCH_CRON.get('DAY_OF_WEEK', '*')),
}


@periodic_task(run_every=crontab(**fetch_edflex_data_cron))
def fetch_edflex_data():
    if EDFLEX_CLIENT_ID and EDFLEX_CLIENT_SECRET and EDFLEX_BASE_API_URL:
        fetch_resources(EDFLEX_CLIENT_ID, EDFLEX_CLIENT_SECRET, EDFLEX_LOCALE, EDFLEX_BASE_API_URL)

    for site_configuration in SiteConfiguration.objects.filter(enabled=True):
        client_id = site_configuration.get_value('EDFLEX_CLIENT_ID')
        client_secret = site_configuration.get_value('EDFLEX_CLIENT_SECRET')
        locale = site_configuration.get_value('EDFLEX_LOCALE', EDFLEX_LOCALE)
        base_api_url = site_configuration.get_value('EDFLEX_BASE_API_URL')

        if client_id and client_secret and base_api_url:
            fetch_resources(client_id, client_secret, locale, base_api_url)


@periodic_task(run_every=crontab(**fetch_new_edflex_data_cron))
def fetch_new_edflex_data():
    if EDFLEX_CLIENT_ID and EDFLEX_CLIENT_SECRET and EDFLEX_BASE_API_URL:
        fetch_new_resources_and_delete_old_resources(
            EDFLEX_CLIENT_ID,
            EDFLEX_CLIENT_SECRET,
            EDFLEX_LOCALE,
            EDFLEX_BASE_API_URL
        )

    for site_configuration in SiteConfiguration.objects.filter(enabled=True):
        client_id = site_configuration.get_value('EDFLEX_CLIENT_ID')
        client_secret = site_configuration.get_value('EDFLEX_CLIENT_SECRET')
        locale = site_configuration.get_value('EDFLEX_LOCALE', EDFLEX_LOCALE)
        base_api_url = site_configuration.get_value('EDFLEX_BASE_API_URL')

        if client_id and client_secret and base_api_url:
            fetch_new_resources_and_delete_old_resources(client_id, client_secret, locale, base_api_url)


@periodic_task(run_every=crontab(**update_resources_cron))
def update_resources():
    user = get_user_model().objects.filter(
        Q(is_staff=True) | Q(is_superuser=True), is_active=True
    ).first()

    if user is None:
        log.error('The system must have a User is_active=True and staff or superuser')
        return

    for course_overview in CourseOverview.objects.all():
        try:
            course = get_course(course_overview.id, depth=4)
        except ValueError:
            continue

        try:
            edflex_client = EdflexOauthClient(get_edflex_configuration_for_org(course.location.org))
        except ImproperlyConfigured as er:
            log.error(er)
            continue

        for section in course.get_children():
            for subsection in section.get_children():
                for unit in subsection.get_children():
                    for xblock in unit.get_children():
                        if xblock.location.block_type == 'edflex':
                            resource_id = xblock.resource.get('id')
                            if resource_id:
                                resource = edflex_client.get_resource(resource_id)
                                if resource and xblock.resource != resource:
                                    xblock.resource = resource
                                    old_xblock_location = xblock.location
                                    xblock.location = xblock.location.for_branch(ModuleStoreEnum.BranchName.draft)
                                    xblock.save()
                                    modulestore().update_item(xblock, user.id, asides=[])
                                    xblock.location = old_xblock_location
                                    modulestore().publish(xblock.location, user.id)


def fetch_resources(client_id, client_secret, locale, base_api_url):
    edflex_client = EdflexOauthClient({
        'client_id': client_id,
        'client_secret': client_secret,
        'locale': locale,
        'base_api_url': base_api_url
    })
    r_catalogs = edflex_client.get_catalogs()
    category_ids = []

    for catalog in r_catalogs:
        resource_ids = []
        r_catalog = edflex_client.get_catalog(catalog['id'])

        for resource in r_catalog['items']:
            r_resource = edflex_client.get_resource(resource['resource']['id'])

            if r_resource:
                clean_title = emoji.get_emoji_regexp().sub(r'', r_resource['title']) if r_resource.get('title') else ''
                resource, created = Resource.objects.update_or_create(
                    catalog_id=catalog['id'],
                    resource_id=r_resource['id'],
                    defaults={
                        'title': clean_title,
                        'r_type': r_resource['type'],
                        'language': r_resource['language']
                    },
                )
                resource_ids.append(resource.id)
                resource.categories.clear()

                for r_category in r_resource.get('categories', []):
                    clean_name = emoji.get_emoji_regexp().sub(r'', r_category['name']) if r_category.get('name') else ''
                    category, created = Category.objects.update_or_create(
                        category_id=r_category['id'],
                        catalog_id=catalog['id'],
                        defaults={'name': clean_name,
                                  'catalog_title': catalog['title']}
                    )
                    resource.categories.add(category)
                    category_ids.append(category.id)

        Resource.objects.filter(
            catalog_id=catalog['id']
        ).exclude(
            id__in=resource_ids
        ).delete()

    Resource.objects.exclude(
        catalog_id__in=[catalog['id'] for catalog in r_catalogs]
    ).delete()

    Category.objects.exclude(
        id__in=category_ids
    ).delete()


def fetch_new_resources_and_delete_old_resources(client_id, client_secret, locale, base_api_url):
    edflex_client = EdflexOauthClient({
        'client_id': client_id,
        'client_secret': client_secret,
        'locale': locale,
        'base_api_url': base_api_url
    })
    r_catalogs = edflex_client.get_catalogs()

    for catalog in r_catalogs:
        resource_ids = []
        r_catalog = edflex_client.get_catalog(catalog['id'])

        for item_resource in r_catalog['items']:
            resource = Resource.objects.filter(
                resource_id=item_resource['resource']['id'],
                catalog_id=catalog['id']
            ).first()

            if resource is None:
                r_resource = edflex_client.get_resource(item_resource['resource']['id'])

                if r_resource:
                    clean_title = emoji.get_emoji_regexp().sub(r'', r_resource['title']) if r_resource.get('title') else ''
                    resource, created = Resource.objects.update_or_create(
                        catalog_id=catalog['id'],
                        resource_id=r_resource['id'],
                        defaults={
                            'title': clean_title,
                            'r_type': r_resource['type'],
                            'language': r_resource['language']
                        },
                    )
                    resource.categories.clear()

                    for r_category in r_resource.get('categories', []):
                        clean_name = emoji.get_emoji_regexp().sub(r'', r_category['name']) if r_category.get('name') else ''
                        category, created = Category.objects.update_or_create(
                            category_id=r_category['id'],
                            catalog_id=catalog['id'],
                            defaults={'name': clean_name,
                                      'catalog_title': catalog['title']}
                        )
                        resource.categories.add(category)

            resource_ids.append(resource.id)

        Resource.objects.filter(
            catalog_id=catalog['id']
        ).exclude(
            id__in=resource_ids
        ).delete()
