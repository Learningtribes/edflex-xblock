from celery.decorators import periodic_task
from celery.schedules import crontab
from django.conf import settings
from openedx.core.djangoapps.site_configuration.models import SiteConfiguration

from .api import EdflexOauthClient
from .models import Category, Resource


cron_grade_settings = getattr(
    settings, 'EDFLEX_RESOURCES_UPDATE_CRON',
    {
        'minute': str(settings.FEATURES.get('EDFLEX_RESOURCES_UPDATE_CRON_MINUTE', '0')),
        'hour': str(settings.FEATURES.get('EDFLEX_RESOURCES_UPDATE_CRON_HOUR', '0')),
        'day_of_month': str(settings.FEATURES.get('EDFLEX_RESOURCES_UPDATE_CRON_DOM', '*')),
        'day_of_week': str(settings.FEATURES.get('EDFLEX_RESOURCES_UPDATE_CRON_DOW', '*')),
        'month_of_year': str(settings.FEATURES.get('EDFLEX_RESOURCES_UPDATE_CRON_MONTH', '1')),
    }
)


@periodic_task(run_every=crontab(**cron_grade_settings))
def fetch_edflex_data():
    client_id = getattr(settings, 'EDFLEX_CLIENT_ID', None)
    client_secret = getattr(settings, 'EDFLEX_CLIENT_SECRET', None)
    base_api_url = getattr(settings, 'EDFLEX_BASE_API_URL', None)

    if client_id and client_secret and base_api_url:
        resources_update(client_id, client_secret, base_api_url)

    for site_configuration in SiteConfiguration.objects.filter(enabled=True):
        client_id = site_configuration.get_value('EDFLEX_CLIENT_ID')
        client_secret = site_configuration.get_value('EDFLEX_CLIENT_SECRET')
        base_api_url = site_configuration.get_value('EDFLEX_BASE_API_URL')

        if client_id and client_secret and base_api_url:
            resources_update(client_id, client_secret, base_api_url)


def resources_update(client_id, client_secret, base_api_url):
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
