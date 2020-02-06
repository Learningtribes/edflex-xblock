import mock
import requests_oauthlib

from unittest import TestCase
from requests import HTTPError
from django.core.exceptions import ImproperlyConfigured

from .api import EdflexOauthClient
from .utils import get_edflex_configuration
from .tasks import fetch_edflex_data, resources_update


@mock.patch('edflex.utils.get_edflex_configuration', return_value={
    'client_id': '100',
    'client_secret': 'test_client_secret',
    'base_api_url': "https://test.base.url"
})
class TestEdflexOauthClient(TestCase):

    @mock.patch('edflex.api.EdflexOauthClient.fetch_token', return_value='mocked_token')
    def test_init(self, mock_fetch_token, mock_get_edflex_configuration):
        test_instance = EdflexOauthClient(mock_get_edflex_configuration())
        self.assertEqual(test_instance.client_id, '100')
        self.assertEqual(test_instance.client_secret, 'test_client_secret')
        self.assertEqual(test_instance.base_api_url, 'https://test.base.url')
        mock_fetch_token.assert_called_once()
        self.assertIsInstance(test_instance.oauth_client, requests_oauthlib.oauth2_session.OAuth2Session)

    @mock.patch('edflex.api.urljoin', return_value='https://test.base.url/api/oauth/v2/token')
    def test_fetch_token(self, mock_urljoin, mock_get_edflex_configuration):
        mock_token = mock.patch('edflex.api.EdflexOauthClient.fetch_token', return_value='mocked_token')
        mock_token.start()
        test_instance = EdflexOauthClient(mock_get_edflex_configuration())
        mock_token.stop()

        mock_auth_fetch_token = test_instance.oauth_client.fetch_token = mock.Mock()

        test_instance.fetch_token()
        mock_urljoin.assert_called_with('https://test.base.url', '/api/oauth/v2/token')
        mock_auth_fetch_token.assert_called_with(client_secret='test_client_secret',
                                                 token_url='https://test.base.url/api/oauth/v2/token', client_id='100')

    @mock.patch('edflex.api.EdflexOauthClient.fetch_token', return_value='mocked_token')
    @mock.patch('edflex.api.urljoin', return_value='https://test.base.url/api/selection/catalogs')
    def test_get_catalogs(self, mock_urljoin, mock_token, mock_get_edflex_configuration):
        test_instance = EdflexOauthClient(mock_get_edflex_configuration())
        mock_get = test_instance.oauth_client.get = mock.Mock(
            return_value=mock.Mock(status_code=200, json=mock.Mock(return_value={'value': ['content_key']})))
        test_catalogs_result = test_instance.get_catalogs()
        mock_urljoin.assert_called_with(test_instance.base_api_url, test_instance.CATALOGS_URL)
        mock_get.assert_called_once_with(url='https://test.base.url/api/selection/catalogs',
                                         headers={'content-type': 'application/json'})
        self.assertEqual(test_catalogs_result, {'value': ['content_key']})

    @mock.patch('edflex.api.EdflexOauthClient.fetch_token', return_value='mocked_token')
    @mock.patch('edflex.api.urljoin', return_value='https://test.base.url/api/selection/catalogs')
    def test_get_catalogs_error(self, mock_urljoin, mock_token, mock_get_edflex_configuration):
        test_instance = EdflexOauthClient(mock_get_edflex_configuration())
        mock_get = test_instance.oauth_client.get = mock.Mock(
            return_value=mock.Mock(status_code=400, raise_for_status=mock.Mock(side_effect=HTTPError)))
        test_catalogs_result = test_instance.get_catalogs()
        mock_urljoin.assert_called_with(test_instance.base_api_url, test_instance.CATALOGS_URL)
        mock_get.assert_called_once_with(url='https://test.base.url/api/selection/catalogs',
                                         headers={'content-type': 'application/json'})
        self.assertEqual(test_instance.CATALOGS_URL, '/api/selection/catalogs')
        self.assertEqual(test_catalogs_result, [])
        self.assertRaises(HTTPError)

    @mock.patch('edflex.api.EdflexOauthClient.fetch_token', return_value='mocked_token')
    @mock.patch('edflex.api.urljoin', return_value='https://test.base.url/api/selection/catalogs/1')
    def test_get_catalog(self, mock_urljoin, mock_token, mock_get_edflex_configuration):
        test_instance = EdflexOauthClient(mock_get_edflex_configuration())
        mock_get = test_instance.oauth_client.get = mock.Mock(
            return_value=mock.Mock(status_code=200, json=mock.Mock(return_value={'value': ['content_key']})))
        catalog_id = '1'

        test_catalog_result = test_instance.get_catalog(catalog_id)
        mock_urljoin.assert_called_with('https://test.base.url', '/api/selection/catalogs/1')
        mock_get.assert_called_once_with(url='https://test.base.url/api/selection/catalogs/1',
                                         headers={'content-type': 'application/json'})
        self.assertEqual(test_instance.CATALOG_URL, '/api/selection/catalogs/{id}')
        self.assertEqual(test_catalog_result, {'value': ['content_key']})

    @mock.patch('edflex.api.EdflexOauthClient.fetch_token', return_value='mocked_token')
    @mock.patch('edflex.api.urljoin', return_value='https://test.base.url/api/selection/catalogs/1')
    def test_get_catalog_error(self, mock_urljoin, mock_token, mock_get_edflex_configuration):
        test_instance = EdflexOauthClient(mock_get_edflex_configuration())
        mock_get = test_instance.oauth_client.get = mock.Mock(
            return_value=mock.Mock(status_code=400, raise_for_status=mock.Mock(side_effect=HTTPError)))
        catalog_id = '1'

        test_catalog_result = test_instance.get_catalog(catalog_id)
        mock_urljoin.assert_called_with('https://test.base.url', '/api/selection/catalogs/1')
        mock_get.assert_called_once_with(url='https://test.base.url/api/selection/catalogs/1',
                                         headers={'content-type': 'application/json'})
        self.assertEqual(test_instance.CATALOG_URL, '/api/selection/catalogs/{id}')
        self.assertEqual(test_catalog_result, {'items': []})
        self.assertRaises(HTTPError)

    @mock.patch('edflex.api.EdflexOauthClient.fetch_token', return_value='mocked_token')
    @mock.patch('edflex.api.urljoin', return_value='https://test.base.url/api/resource/resources/1')
    def test_get_resource(self, mock_urljoin, mock_token, mock_get_edflex_configuration):
        test_instance = EdflexOauthClient(mock_get_edflex_configuration())
        mock_get = test_instance.oauth_client.get = mock.Mock(
            return_value=mock.Mock(status_code=200, json=mock.Mock(return_value={'value': ['content_key']})))
        resource_id = '1'

        test_get_resource_result = test_instance.get_resource(resource_id)
        mock_urljoin.assert_called_with('https://test.base.url', '/api/resource/resources/1')
        mock_get.assert_called_once_with(url='https://test.base.url/api/resource/resources/1',
                                         headers={'content-type': 'application/json'})
        self.assertEqual(test_instance.RESOURCE_URL, '/api/resource/resources/{id}')
        self.assertEqual(test_get_resource_result['value'], ['content_key'])
        self.assertEqual(test_get_resource_result, {'value': ['content_key']})

    @mock.patch('edflex.api.EdflexOauthClient.fetch_token', return_value='mocked_token')
    @mock.patch('edflex.api.urljoin', return_value='https://test.base.url/api/resource/resources/1')
    def test_get_resource_error(self, mock_urljoin, mock_token, mock_get_edflex_configuration):
        test_instance = EdflexOauthClient(mock_get_edflex_configuration())
        mock_get = test_instance.oauth_client.get = mock.Mock(
            return_value=mock.Mock(status_code=400, raise_for_status=mock.Mock(side_effect=HTTPError)))
        resource_id = '1'

        test_get_resource_result = test_instance.get_resource(resource_id)
        mock_urljoin.assert_called_with('https://test.base.url', '/api/resource/resources/1')
        mock_get.assert_called_once_with(url='https://test.base.url/api/resource/resources/1',
                                         headers={'content-type': 'application/json'})
        self.assertEqual(test_instance.RESOURCE_URL, '/api/resource/resources/{id}')
        self.assertEqual(test_get_resource_result, None)
        self.assertRaises(HTTPError)


class TestUtils(TestCase):

    @mock.patch('openedx.core.djangoapps.site_configuration.helpers.get_value', return_value='test_value')
    def test_get_edflex_configuration(self, mock_get_value):
        edflex_configuration_result = get_edflex_configuration()
        self.assertEqual(edflex_configuration_result, {'client_id': 'test_value',
                                                       'client_secret': 'test_value',
                                                       'base_api_url': 'test_value'})

    @mock.patch('edflex.utils.get_edflex_configuration',
                return_value=mock.Mock(status_code=400, raise_for_status=mock.Mock(side_effect=ImproperlyConfigured)))
    def test_get_edflex_configuration_error(self, mock_get_edflex_configuration):
        mock_get_edflex_configuration()
        self.assertRaises(ImproperlyConfigured)


class TestTasks(TestCase):

    def setUp(self):
        mock_get_edflex_configuration = mock.Mock(return_value={
            'client_id': '100',
            'client_secret': 'test_client_secret',
            'base_api_url': "https://test.base.url"
        })
        mock_fetch_token = mock.patch('edflex.api.EdflexOauthClient.fetch_token', return_value='mocked_token')
        mock_fetch_token.start()
        self.test_instance = EdflexOauthClient(mock_get_edflex_configuration())

    @mock.patch('edflex.tasks.settings', return_value=mock.Mock(status_code=200, json=mock.Mock(
        return_value={'EDFLEX_CLIENT_ID': '1', 'EDFLEX_CLIENT_SECRET': 'secret', 'EDFLEX_BASE_API_URL': 'baseurl'})))
    @mock.patch('edflex.tasks.resources_update')
    def test_fetch_edflex_data_with_site_configurations_and_settings(self, mock_resources_update, mock_settings):
        with mock.patch('openedx.core.djangoapps.site_configuration.models.SiteConfiguration.objects.filter',
                        return_value=[mock.Mock(), mock.Mock(), mock.Mock()]):
            fetch_edflex_data()
            self.assertEqual(mock_resources_update.call_count, 4)

    @mock.patch('edflex.tasks.resources_update')
    def test_fetch_edflex_data_without_site_configurations_and_settings(self, mock_resources_update):
        fetch_edflex_data()
        self.assertEqual(mock_resources_update.call_count, 0)

    @mock.patch('edflex.models.Category.objects.update_or_create', return_value=(mock.MagicMock(), mock.MagicMock()))
    @mock.patch('edflex.models.Resource.objects.filter',
                return_value=mock.Mock(exclude=mock.Mock(return_value=mock.Mock(delete=mock.Mock()))))
    @mock.patch('edflex.models.Resource.objects.update_or_create', return_value=(mock.MagicMock(), mock.MagicMock()))
    @mock.patch('edflex.api.EdflexOauthClient.get_resource',
                return_value={'id': mock.Mock(), 'title': mock.Mock(), 'type': mock.Mock(), 'language': mock.Mock(),
                              'categories': [mock.MagicMock(), mock.MagicMock()]})
    @mock.patch('edflex.api.EdflexOauthClient.get_catalog', return_value={'items': [{'resource': {'id': 11}}]})
    @mock.patch('edflex.api.EdflexOauthClient.get_catalogs', return_value=[{'id': 1}, {'id': 2}, {'id': 3}])
    def test_resource_update_all_positive(self, mock_get_catalogs, mock_get_catalog, mock_get_resource,
                                          mock_resource_update_or_create, mock_resource_filter,
                                          mock_categories_update_or_create):
        resources_update(self.test_instance.client_id, self.test_instance.client_secret,
                         self.test_instance.base_api_url)

        mock_get_catalogs.assert_called()
        self.assertEqual(mock_get_catalog.call_count, 3)
        self.assertEqual(mock_get_resource.call_count, 3)
        self.assertEqual(mock_resource_update_or_create.call_count, 3)
        self.assertEqual(mock_categories_update_or_create.call_count, 6)
        mock_resource_filter.assert_called_with(catalog_id=3)
        mock_resource_filter().exclude.assert_called()

    @mock.patch('edflex.models.Resource.objects.filter',
                return_value=mock.Mock(exclude=mock.Mock(return_value=mock.Mock(delete=mock.Mock()))))
    @mock.patch('edflex.models.Resource.objects.update_or_create', return_value=(mock.MagicMock(), mock.MagicMock()))
    @mock.patch('edflex.api.EdflexOauthClient.get_resource',
                return_value={'id': mock.Mock(), 'title': mock.Mock(), 'type': mock.Mock(), 'language': mock.Mock(),
                              'categories': []})
    @mock.patch('edflex.api.EdflexOauthClient.get_catalog', return_value={'items': [{'resource': {'id': 11}}]})
    @mock.patch('edflex.api.EdflexOauthClient.get_catalogs', return_value=[{'id': 1}, {'id': 2}, {'id': 3}])
    def test_resource_update_without_categories(self, mock_get_catalogs, mock_get_catalog, mock_get_resource,
                                                mock_resource_update_or_create, mock_resource_filter):
        resources_update(self.test_instance.client_id, self.test_instance.client_secret,
                         self.test_instance.base_api_url)

        mock_get_catalogs.assert_called()
        self.assertEqual(mock_get_catalog.call_count, 3)
        self.assertEqual(mock_get_resource.call_count, 3)
        self.assertEqual(mock_resource_update_or_create.call_count, 3)
        mock_resource_filter.assert_called_with(catalog_id=3)
        mock_resource_filter().exclude.assert_called()

    @mock.patch('edflex.models.Resource.objects.filter',
                return_value=mock.Mock(exclude=mock.Mock(return_value=mock.Mock(delete=mock.Mock()))))
    @mock.patch('edflex.api.EdflexOauthClient.get_resource', return_value={})
    @mock.patch('edflex.api.EdflexOauthClient.get_catalog', return_value={'items': [{'resource': {'id': 11}}]})
    @mock.patch('edflex.api.EdflexOauthClient.get_catalogs', return_value=[{'id': 1}, {'id': 2}, {'id': 3}])
    def test_resource_update_without_r_resource(self, mock_get_catalogs, mock_get_catalog, mock_get_resource,
                                                mock_resource_filter):
        resources_update(self.test_instance.client_id, self.test_instance.client_secret,
                         self.test_instance.base_api_url)

        mock_get_catalogs.assert_called()
        self.assertEqual(mock_get_catalog.call_count, 3)
        self.assertEqual(mock_get_resource.call_count, 3)
        mock_resource_filter.assert_called_with(catalog_id=3)
        mock_resource_filter().exclude.assert_called_with(id__in=[])

    @mock.patch('edflex.models.Category.objects.update_or_create', return_value=(mock.MagicMock(), mock.MagicMock()))
    @mock.patch('edflex.models.Resource.objects.filter',
                return_value=mock.Mock(exclude=mock.Mock(return_value=mock.Mock(delete=mock.Mock()))))
    @mock.patch('edflex.models.Resource.objects.update_or_create', return_value=(mock.MagicMock(), mock.MagicMock()))
    @mock.patch('edflex.api.EdflexOauthClient.get_resource',
                return_value={'id': mock.Mock(), 'title': mock.Mock(), 'type': mock.Mock(), 'language': mock.Mock(),
                              'categories': [mock.MagicMock(), mock.MagicMock()]})
    @mock.patch('edflex.api.EdflexOauthClient.get_catalog', return_value={'items': [{'resource': {'id': 11}}]})
    @mock.patch('edflex.api.EdflexOauthClient.get_catalogs', return_value=[])
    def test_resource_update_without_r_catalogs(self, mock_get_catalogs, mock_get_catalog, mock_get_resource,
                                                mock_resource_update_or_create, mock_resource_filter,
                                                mock_categories_update_or_create):
        resources_update(self.test_instance.client_id, self.test_instance.client_secret,
                         self.test_instance.base_api_url)

        mock_get_catalogs.assert_called()
        mock_get_catalog.assert_not_called()
        mock_get_resource.assert_not_called()
        mock_resource_update_or_create.assert_not_called()
        mock_categories_update_or_create.assert_not_called()
        mock_resource_filter.assert_not_called()
        mock_resource_filter().exclude.assert_not_called()
