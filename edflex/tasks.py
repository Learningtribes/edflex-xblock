import logging
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
    EDFLEX_BASE_API_URL,
    get_edflex_configuration_for_org
)

log = logging.getLogger(__name__)

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


@periodic_task(run_every=crontab(**fetch_edflex_data_cron))
def fetch_edflex_data():
    if EDFLEX_CLIENT_ID and EDFLEX_CLIENT_SECRET and EDFLEX_BASE_API_URL:
        fetch_resources(EDFLEX_CLIENT_ID, EDFLEX_CLIENT_SECRET, EDFLEX_BASE_API_URL)

    for site_configuration in SiteConfiguration.objects.filter(enabled=True):
        client_id = site_configuration.get_value('EDFLEX_CLIENT_ID')
        client_secret = site_configuration.get_value('EDFLEX_CLIENT_SECRET')
        base_api_url = site_configuration.get_value('EDFLEX_BASE_API_URL')

        if client_id and client_secret and base_api_url:
            fetch_resources(client_id, client_secret, base_api_url)


def fetch_resources(client_id, client_secret, base_api_url):
    edflex_client = EdflexOauthClient({
        'client_id': client_id,
        'client_secret': client_secret,
        'base_api_url': base_api_url
    })
    r_catalogs = edflex_client.get_catalogs()

    for catalog in r_catalogs:
        resource_ids = []
        r_catalog = edflex_client.get_catalog(catalog['id'])

        for resource in r_catalog['items']:
            r_resource = edflex_client.get_resource(resource['resource']['id'])

            if r_resource:
                resource, created = Resource.objects.update_or_create(
                    catalog_id=catalog['id'],
                    resource_id=r_resource['id'],
                    defaults={
                        'title': r_resource['title'],
                        'r_type': r_resource['type'],
                        'language': r_resource['language']
                    },
                )
                resource_ids.append(resource.id)
                resource.categories.clear()

                for r_category in r_resource.get('categories', []):
                    category, created = Category.objects.update_or_create(
                        category_id=r_category['id'],
                        defaults={'name': r_category['name']}
                    )
                    resource.categories.add(category)

        Resource.objects.filter(
            catalog_id=catalog['id']
        ).exclude(
            id__in=resource_ids
        ).delete()


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
