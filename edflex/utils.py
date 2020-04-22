from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers

# default settings
EDFLEX_CLIENT_ID = settings.XBLOCK_SETTINGS.get('EdflexXBlock', {}).get('EDFLEX_CLIENT_ID')
EDFLEX_CLIENT_SECRET = settings.XBLOCK_SETTINGS.get('EdflexXBlock', {}).get('EDFLEX_CLIENT_SECRET')
EDFLEX_LOCALE = settings.XBLOCK_SETTINGS.get('EdflexXBlock', {}).get('EDFLEX_LOCALE', 'en')
EDFLEX_BASE_API_URL = settings.XBLOCK_SETTINGS.get('EdflexXBlock', {}).get('EDFLEX_BASE_API_URL')


def get_edflex_configuration_for_org(org):
    client_id = configuration_helpers.get_value_for_org(org, 'EDFLEX_CLIENT_ID')
    client_secret = configuration_helpers.get_value_for_org(org, 'EDFLEX_CLIENT_SECRET')
    locale = configuration_helpers.get_value_for_org(org, 'EDFLEX_LOCALE', EDFLEX_LOCALE)
    base_api_url = configuration_helpers.get_value_for_org(org, 'EDFLEX_BASE_API_URL')

    if not (client_id and client_secret and base_api_url):
        configuration = get_edflex_configuration()
        return configuration

    return {
        'client_id': client_id,
        'client_secret': client_secret,
        'locale': locale,
        'base_api_url': base_api_url
    }


def get_edflex_configuration():
    client_id = configuration_helpers.get_value('EDFLEX_CLIENT_ID', EDFLEX_CLIENT_ID)
    client_secret = configuration_helpers.get_value('EDFLEX_CLIENT_SECRET', EDFLEX_CLIENT_SECRET)
    locale = configuration_helpers.get_value('EDFLEX_LOCALE', EDFLEX_LOCALE)
    base_api_url = configuration_helpers.get_value('EDFLEX_BASE_API_URL', EDFLEX_BASE_API_URL)

    if not (client_id and client_secret and base_api_url):
        raise ImproperlyConfigured(
            'In order to use API for Edflex of the followings must be configured: '
            'EDFLEX_CLIENT_ID, EDFLEX_CLIENT_SECRET, EDFLEX_BASE_API_URL'
        )
    return {
        'client_id': client_id,
        'client_secret': client_secret,
        'locale': locale,
        'base_api_url': base_api_url
    }
