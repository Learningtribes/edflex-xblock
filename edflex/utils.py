from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers


def get_edflex_configuration():
    client_id = configuration_helpers.get_value(
        'EDFLEX_CLIENT_ID',
        getattr(settings, 'EDFLEX_CLIENT_ID', None)
    )
    client_secret = configuration_helpers.get_value(
        'EDFLEX_CLIENT_SECRET',
        getattr(settings, 'EDFLEX_CLIENT_SECRET', None)
    )
    base_api_url = configuration_helpers.get_value(
        'EDFLEX_BASE_API_URL',
        getattr(settings, 'EDFLEX_BASE_API_URL', None)
    )

    if not (client_id and client_secret and base_api_url):
        raise ImproperlyConfigured(
            'In order to use API for Edflex of the followings must be configured: '
            'EDFLEX_CLIENT_ID, EDFLEX_CLIENT_SECRET, EDFLEX_BASE_API_URL'
        )
    return {
        'client_id': client_id,
        'client_secret': client_secret,
        'base_api_url': base_api_url
    }
