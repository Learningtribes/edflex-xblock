import logging
from urlparse import urljoin

from oauthlib.oauth2 import BackendApplicationClient
from requests import HTTPError
from requests_oauthlib import OAuth2Session


log = logging.getLogger(__name__)


class EdflexOauthClient(object):
    """
    Client to consume Edflex service API.
    """
    TOKEN_URL = '/api/oauth/v2/token'
    CATALOGS_URL = '/api/selection/catalogs'
    CATALOG_URL = '/api/selection/catalogs/{id}'
    RESOURCE_URL = '/api/resource/resources/{id}'

    def __init__(self, config):
        self.client_id = config['client_id']
        self.client_secret = config['client_secret']
        self.locale = config['locale']
        self.base_api_url = config['base_api_url']
        client = BackendApplicationClient(client_id=self.client_id)
        self.oauth_client = OAuth2Session(client=client)
        self.fetch_token()

    def fetch_token(self):
        token_url = urljoin(self.base_api_url, self.TOKEN_URL)
        self.oauth_client.fetch_token(
            token_url=token_url,
            client_id=self.client_id,
            client_secret=self.client_secret,
        )

    def get_catalogs(self):
        catalogs_url = urljoin(self.base_api_url, self.CATALOGS_URL)
        resp = self.oauth_client.get(
            url=catalogs_url,
            headers={'content-type': 'application/json'},
            params={'locale': self.locale}
        )
        try:
            resp.raise_for_status()
        except HTTPError as er:
            log.error(er)
            catalogs = []
        else:
            catalogs = resp.json()
        return catalogs

    def get_catalog(self, catalog_id):
        catalog_url = urljoin(self.base_api_url, self.CATALOG_URL.format(id=catalog_id))
        resp = self.oauth_client.get(
            url=catalog_url,
            headers={'content-type': 'application/json'},
            params={'locale': self.locale}
        )
        try:
            resp.raise_for_status()
        except HTTPError as er:
            log.error(er)
            catalog = {'items': []}
        else:
            catalog = resp.json()
        return catalog

    def get_resource(self, resource_id):
        resource_url = urljoin(self.base_api_url, self.RESOURCE_URL.format(id=resource_id))
        resp = self.oauth_client.get(
            url=resource_url,
            headers={'content-type': 'application/json'},
            params={'locale': self.locale}
        )
        try:
            resp.raise_for_status()
        except HTTPError as er:
            log.error(er)
            resource = None
        else:
            resource = resp.json()
        return resource
