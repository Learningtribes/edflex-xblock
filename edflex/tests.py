import mock
import json
import requests_oauthlib

from unittest import TestCase

from django.core.exceptions import ImproperlyConfigured
from requests import HTTPError
from xblock.field_data import DictFieldData

from .api import EdflexOauthClient
from .utils import get_edflex_configuration, get_edflex_configuration_for_org
from .tasks import (
    fetch_edflex_data, fetch_resources, update_resources, fetch_new_edflex_data,
    fetch_new_resources_and_delete_old_resources
)
from .edflex import EdflexXBlock


@mock.patch('edflex.utils.get_edflex_configuration', return_value={
    'client_id': '100',
    'client_secret': 'test_client_secret',
    'locale': 'en',
    'base_api_url': "https://test.base.url"
})
class TestEdflexOauthClient(TestCase):

    @mock.patch('edflex.api.EdflexOauthClient.fetch_token', return_value='mocked_token')
    def test_init(self, mock_fetch_token, mock_get_edflex_configuration):
        # act:
        test_instance = EdflexOauthClient(mock_get_edflex_configuration())

        # assert:
        self.assertEqual(test_instance.client_id, '100')
        self.assertEqual(test_instance.client_secret, 'test_client_secret')
        self.assertEqual(test_instance.base_api_url, 'https://test.base.url')
        mock_fetch_token.assert_called_once()
        self.assertIsInstance(test_instance.oauth_client, requests_oauthlib.oauth2_session.OAuth2Session)

    @mock.patch('edflex.api.urljoin', return_value='https://test.base.url/api/oauth/v2/token')
    def test_fetch_token(self, mock_urljoin, mock_get_edflex_configuration):
        # arrange:
        mock_token = mock.patch('edflex.api.EdflexOauthClient.fetch_token', return_value='mocked_token')
        mock_token.start()
        test_instance = EdflexOauthClient(mock_get_edflex_configuration())
        mock_token.stop()
        mock_auth_fetch_token = test_instance.oauth_client.fetch_token = mock.Mock()

        # act:
        test_instance.fetch_token()

        # assert:
        mock_urljoin.assert_called_with('https://test.base.url', '/api/oauth/v2/token')
        mock_auth_fetch_token.assert_called_with(
            client_secret='test_client_secret',
            token_url='https://test.base.url/api/oauth/v2/token',
            client_id='100'
        )

    @mock.patch('edflex.api.EdflexOauthClient.fetch_token', return_value='mocked_token')
    @mock.patch('edflex.api.urljoin', return_value='https://test.base.url/api/selection/catalogs')
    def test_get_catalogs(self, mock_urljoin, mock_token, mock_get_edflex_configuration):
        # arrange:
        test_instance = EdflexOauthClient(mock_get_edflex_configuration())
        mock_get = test_instance.oauth_client.get = mock.Mock(
            return_value=mock.Mock(status_code=200,
                                   json=mock.Mock(return_value=[{"id": "catalog_id", "title": "Catalog"}]))
        )

        # act:
        test_catalogs_result = test_instance.get_catalogs()

        # assert:
        mock_urljoin.assert_called_with(test_instance.base_api_url, test_instance.CATALOGS_URL)
        mock_get.assert_called_once_with(
            url='https://test.base.url/api/selection/catalogs',
            headers={'content-type': 'application/json'},
            params={'locale': 'en'}
        )
        self.assertEqual(test_catalogs_result, [{"id": "catalog_id", "title": "Catalog"}])

    @mock.patch('edflex.api.EdflexOauthClient.fetch_token', return_value='mocked_token')
    @mock.patch('edflex.api.urljoin', return_value='https://test.base.url/api/selection/catalogs')
    def test_get_catalogs_error(self, mock_urljoin, mock_token, mock_get_edflex_configuration):
        # arrange:
        test_instance = EdflexOauthClient(mock_get_edflex_configuration())
        mock_get = test_instance.oauth_client.get = mock.Mock(
            return_value=mock.Mock(status_code=400, raise_for_status=mock.Mock(side_effect=HTTPError))
        )

        # act:
        test_catalogs_result = test_instance.get_catalogs()

        # assert:
        mock_urljoin.assert_called_with(test_instance.base_api_url, test_instance.CATALOGS_URL)
        mock_get.assert_called_once_with(
            url='https://test.base.url/api/selection/catalogs',
            headers={'content-type': 'application/json'},
            params={'locale': 'en'}
        )
        self.assertEqual(test_catalogs_result, [])

    @mock.patch('edflex.api.EdflexOauthClient.fetch_token', return_value='mocked_token')
    @mock.patch('edflex.api.urljoin', return_value='https://test.base.url/api/selection/catalogs/catalog_id')
    def test_get_catalog(self, mock_urljoin, mock_token, mock_get_edflex_configuration):
        # arrange:
        test_instance = EdflexOauthClient(mock_get_edflex_configuration())
        mock_get = test_instance.oauth_client.get = mock.Mock(
            return_value=mock.Mock(status_code=200, json=mock.Mock(
                return_value={
                    "id": "catalog_id",
                    "title": "Catalog",
                    "items": [
                        {
                            "position": 1,
                            "resource": {
                                "id": "resource_id"
                            }
                        }
                    ]
                }
            ))
        )

        # act:
        test_catalog_result = test_instance.get_catalog('catalog_id')

        # assert:
        mock_urljoin.assert_called_with('https://test.base.url', '/api/selection/catalogs/catalog_id')
        mock_get.assert_called_once_with(
            url='https://test.base.url/api/selection/catalogs/catalog_id',
            headers={'content-type': 'application/json'},
            params={'locale': 'en'}
        )
        self.assertEqual(
            test_catalog_result,
            {
                "id": "catalog_id",
                "title": "Catalog",
                "items": [
                    {
                        "position": 1,
                        "resource": {
                            "id": "resource_id"
                        }
                    }
                ]
            }
        )

    @mock.patch('edflex.api.EdflexOauthClient.fetch_token', return_value='mocked_token')
    @mock.patch('edflex.api.urljoin', return_value='https://test.base.url/api/selection/catalogs/catalog_id')
    def test_get_catalog_error(self, mock_urljoin, mock_token, mock_get_edflex_configuration):
        # arrange:
        test_instance = EdflexOauthClient(mock_get_edflex_configuration())
        mock_get = test_instance.oauth_client.get = mock.Mock(
            return_value=mock.Mock(status_code=400, raise_for_status=mock.Mock(side_effect=HTTPError)))

        # act:
        test_catalog_result = test_instance.get_catalog('catalog_id')

        # assert:
        mock_urljoin.assert_called_with('https://test.base.url', '/api/selection/catalogs/catalog_id')
        mock_get.assert_called_once_with(
            url='https://test.base.url/api/selection/catalogs/catalog_id',
            headers={'content-type': 'application/json'},
            params={'locale': 'en'}
        )
        self.assertEqual(test_catalog_result, {'items': []})

    @mock.patch('edflex.api.EdflexOauthClient.fetch_token', return_value='mocked_token')
    @mock.patch('edflex.api.urljoin', return_value='https://test.base.url/api/resource/resources/resource_id')
    def test_get_resource(self, mock_urljoin, mock_token, mock_get_edflex_configuration):
        # arrange:
        test_instance = EdflexOauthClient(mock_get_edflex_configuration())
        mock_get = test_instance.oauth_client.get = mock.Mock(
            return_value=mock.Mock(status_code=200, json=mock.Mock(
                return_value={
                    "id": "resource_id",
                    "type": "mooc",
                    "title": "Mooc of the year",
                    "provider_url": "https://www.my-mooc.com/fr/mooc/creative-box/",
                    "description": "<p>Description</p>",
                    "language": "fr",
                    "difficulty": "1",
                    "price": {
                        "amount": "34.2",
                        "currency": "EUR"
                    },
                    "is_certifying": "true",
                    "is_free_certification": "true",
                    "embed_url": "https://www.youtube.com/watch?v=-WMsMmLd0Q4",
                    "duration": "P19DT4H",
                    "categories": [
                    {
                      "id": "category_id",
                      "name": "Category 1"
                    }
                    ],
                    "image": {
                        "original": "https://...",
                        "small": "https://...",
                        "medium": "https://...",
                        "big": "https://..."
                    },
                    "note": {
                        "global": "4",
                        "content": "2",
                        "animation": "3",
                        "platform": "4",
                        "total_reviews": "16"
                    }
                }
            ))
        )

        # act:
        test_get_resource_result = test_instance.get_resource('resource_id')

        # assert:
        mock_urljoin.assert_called_with('https://test.base.url', '/api/resource/resources/resource_id')
        mock_get.assert_called_once_with(
            url='https://test.base.url/api/resource/resources/resource_id',
            headers={'content-type': 'application/json'},
            params={'locale': 'en'}
        )
        self.assertEqual(
            test_get_resource_result,
            {
                "id": "resource_id",
                "type": "mooc",
                "title": "Mooc of the year",
                "provider_url": "https://www.my-mooc.com/fr/mooc/creative-box/",
                "description": "<p>Description</p>",
                "language": "fr",
                "difficulty": "1",
                "price": {
                    "amount": "34.2",
                    "currency": "EUR"
                },
                "is_certifying": "true",
                "is_free_certification": "true",
                "embed_url": "https://www.youtube.com/watch?v=-WMsMmLd0Q4",
                "duration": "P19DT4H",
                "categories": [
                    {
                        "id": "category_id",
                        "name": "Category 1"
                    }
                ],
                "image": {
                    "original": "https://...",
                    "small": "https://...",
                    "medium": "https://...",
                    "big": "https://..."
                },
                "note": {
                    "global": "4",
                    "content": "2",
                    "animation": "3",
                    "platform": "4",
                    "total_reviews": "16"
                }
            }
        )

    @mock.patch('edflex.api.EdflexOauthClient.fetch_token', return_value='mocked_token')
    @mock.patch('edflex.api.urljoin', return_value='https://test.base.url/api/resource/resources/resource_id')
    def test_get_resource_error(self, mock_urljoin, mock_token, mock_get_edflex_configuration):
        # arrange:
        test_instance = EdflexOauthClient(mock_get_edflex_configuration())
        mock_get = test_instance.oauth_client.get = mock.Mock(
            return_value=mock.Mock(status_code=400, raise_for_status=mock.Mock(side_effect=HTTPError)))

        # act:
        test_get_resource_result = test_instance.get_resource('resource_id')

        # assert:
        mock_urljoin.assert_called_with('https://test.base.url', '/api/resource/resources/resource_id')
        mock_get.assert_called_once_with(
            url='https://test.base.url/api/resource/resources/resource_id',
            headers={'content-type': 'application/json'},
            params={'locale': 'en'}
        )
        self.assertEqual(test_get_resource_result, None)


class TestUtils(TestCase):

    @mock.patch('openedx.core.djangoapps.site_configuration.helpers.get_value', return_value='test_value')
    def test_get_edflex_configuration(self, mock_get_value):
        # act:
        edflex_configuration_result = get_edflex_configuration()

        # assert:
        self.assertEqual(mock_get_value.call_count, 4)
        self.assertEqual(
            edflex_configuration_result,
            {
                'client_id': 'test_value',
                'client_secret': 'test_value',
                'locale': 'test_value',
                'base_api_url': 'test_value'
            }
        )

    @mock.patch('openedx.core.djangoapps.site_configuration.helpers.get_value', return_value=None)
    def test_get_edflex_configuration_error(self, mock_get_value):
        # act + assert:
        with self.assertRaises(ImproperlyConfigured):
            get_edflex_configuration()
            self.assertEqual(mock_get_value.call_count, 3)

    @mock.patch('edflex.utils.get_edflex_configuration', return_value='configuration')
    @mock.patch('edflex.utils.configuration_helpers.get_value_for_org', return_value='value')
    def test_get_edflex_configuration_for_org(self, mock_get_value_for_org, mock_get_edflex_configuration):
        # act:
        result = get_edflex_configuration_for_org('name org')

        # assert:
        mock_get_edflex_configuration.assert_not_called()
        self.assertEqual(mock_get_value_for_org.call_count, 4)
        self.assertEqual(
            result,
            {
                'client_secret': 'value',
                'base_api_url': 'value',
                'client_id': 'value',
                'locale': 'value'
            }
        )

    @mock.patch('edflex.utils.get_edflex_configuration', return_value='configuration')
    @mock.patch('edflex.utils.configuration_helpers.get_value_for_org', return_value=None)
    def test_get_edflex_configuration_for_org_when_there_no_setting_for_org(
            self,
            mock_get_value_for_org,
            mock_get_edflex_configuration
    ):
        # act:
        result = get_edflex_configuration_for_org('name org')

        # assert:
        mock_get_edflex_configuration.assert_called()
        self.assertEqual(mock_get_value_for_org.call_count, 4)
        self.assertEqual(result, 'configuration')


class TestTasks(TestCase):

    @mock.patch('edflex.tasks.EDFLEX_CLIENT_ID', None)
    @mock.patch('edflex.tasks.EDFLEX_CLIENT_SECRET', None)
    @mock.patch('edflex.tasks.EDFLEX_BASE_API_URL', None)
    @mock.patch('edflex.tasks.fetch_resources')
    def test_fetch_edflex_data_with_site_configurations(self, mock_fetch_resources):
        # arrange:
        with mock.patch('openedx.core.djangoapps.site_configuration.models.SiteConfiguration.objects.filter',
                        return_value=[mock.Mock(), mock.Mock(), mock.Mock()]) as site_configuration_filter:
            # act:
            fetch_edflex_data()

            # assert:
            site_configuration_filter.assert_called_once_with(enabled=True)
            self.assertEqual(mock_fetch_resources.call_count, 3)

    @mock.patch('edflex.tasks.EDFLEX_CLIENT_ID', 'client_id')
    @mock.patch('edflex.tasks.EDFLEX_CLIENT_SECRET', 'client_secret')
    @mock.patch('edflex.tasks.EDFLEX_LOCALE', 'en')
    @mock.patch('edflex.tasks.EDFLEX_BASE_API_URL', 'base_api_url')
    @mock.patch('edflex.tasks.fetch_resources')
    @mock.patch('openedx.core.djangoapps.site_configuration.models.SiteConfiguration.objects.filter', return_value=[])
    def test_fetch_edflex_data_with_default_settings(self, mock_site_configuration_filter, mock_fetch_resources):
        # act:
        fetch_edflex_data()

        # assert:
        mock_site_configuration_filter.assert_called_once_with(enabled=True)
        mock_fetch_resources.assert_called_once_with('client_id', 'client_secret', 'en', 'base_api_url')

    @mock.patch('edflex.models.Resource.objects.exclude',
                return_value=mock.Mock(delete=mock.Mock()))
    @mock.patch('edflex.models.Category.objects.exclude',
                return_value=mock.Mock(delete=mock.Mock()))
    @mock.patch('edflex.models.Resource.objects.filter',
                return_value=mock.Mock(exclude=mock.Mock(return_value=mock.Mock(delete=mock.Mock()))))
    @mock.patch('edflex.models.Category.objects.update_or_create',
                return_value=(mock.Mock(id='obj_category_id'), mock.Mock()))
    @mock.patch('edflex.models.Resource.objects.update_or_create',
                return_value=(mock.Mock(id='obj_resource_id'), mock.Mock()))
    @mock.patch('edflex.tasks.EdflexOauthClient', return_value=mock.Mock(
        get_catalogs=mock.Mock(return_value=[{'id': 'catalog_id_1', 'title': 'Catalog title1'},
                                             {'id': 'catalog_id_2', 'title': 'Catalog title2'}
                                             ]),
        get_catalog=mock.Mock(return_value={'id': 'catalog_id',
                                            'title': 'Catalog title',
                                            'items': [
                                                {'resource': {'id': 'resource_id'}}
                                            ]}),
        get_resource=mock.Mock(return_value={'id': 'resource_id',
                                             'title': 'title',
                                             'type': 'type',
                                             'language': 'language',
                                             'categories': [
                                                 {'id': 'category_id', 'name': 'Category name'}
                                             ]})
    ))
    def test_fetch_resources(
            self,
            mock_edflex_oauth_client,
            mock_resources_update_or_create,
            mock_categories_update_or_create,
            mock_resource_filter,
            mock_category_exclude,
            mock_resource_exclude,
    ):
        # act:
        fetch_resources('client_id', 'client_secret', 'en', 'base_api_url')

        # assert:
        mock_edflex_oauth_client.assert_called_once_with(
            {
                'client_id': 'client_id',
                'client_secret': 'client_secret',
                'locale': 'en',
                'base_api_url': 'base_api_url'
            }
        )
        mock_edflex_oauth_client().get_catalogs.assert_called_once_with()
        self.assertEqual(mock_edflex_oauth_client().get_catalog.call_count, 2)
        mock_edflex_oauth_client().get_resource.assert_any_call('resource_id')

        self.assertEqual(mock_resources_update_or_create.call_count, 2)
        mock_resources_update_or_create.assert_any_call(
            catalog_id='catalog_id_1',
            resource_id='resource_id',
            defaults={
                'title': 'title',
                'r_type': 'type',
                'language': 'language'
            }
        )

        self.assertEqual(mock_categories_update_or_create.call_count, 2)
        mock_categories_update_or_create.assert_any_call(
            category_id='category_id',
            catalog_id='catalog_id_1',
            defaults={'name': 'Category name',
                      'catalog_title': 'Catalog title1'}
        )

        mock_resource_filter.assert_any_call(catalog_id='catalog_id_2')
        mock_resource_filter().exclude.assert_any_call(id__in=['obj_resource_id'])
        mock_resource_filter().exclude().delete.assert_called()

        mock_resource_exclude.assert_any_call(catalog_id__in=['catalog_id_1', 'catalog_id_2'])
        mock_resource_exclude().delete.assert_called()

        mock_category_exclude.assert_any_call(id__in=['obj_category_id', 'obj_category_id'])
        mock_category_exclude().delete.assert_called()

    @mock.patch('edflex.tasks.get_user_model', return_value=mock.Mock(
        objects=mock.Mock(filter=mock.Mock(return_value=mock.Mock(
            first=mock.Mock(return_value=mock.Mock(id='user_id'))
        )))
    ))
    @mock.patch('edflex.tasks.CourseOverview.objects.all', return_value=[mock.Mock(id='course_overview_id')])
    @mock.patch('edflex.tasks.modulestore', return_value=mock.Mock(
        update_item=mock.Mock(),
        publish=mock.Mock()
    ))
    @mock.patch('edflex.tasks.EdflexOauthClient', return_value=mock.Mock(
        get_resource=mock.Mock(return_value={'id': 'resource_id',
                                             'title': 'New title',
                                             'type': 'video',
                                             'language': 'en',
                                             'categories': [
                                                 {'id': 'category_id',
                                                  'name': 'Category name'}
                                             ]})
    ))
    @mock.patch('edflex.tasks.get_edflex_configuration_for_org')
    @mock.patch('edflex.tasks.get_course', return_value=mock.Mock(
        location=mock.Mock(org='course_org'),
        get_children=mock.Mock(return_value=[mock.Mock(
            get_children=mock.Mock(return_value=[mock.Mock(
                get_children=mock.Mock(return_value=[mock.Mock(
                    get_children=mock.Mock(return_value=[mock.Mock(
                        save=mock.Mock(),
                        location=mock.Mock(block_type='edflex', for_branch=mock.Mock()),
                        resource={'id': 'resource_id',
                                  'title': 'title',
                                  'type': 'video',
                                  'language': 'fr',
                                  'categories': [
                                      {'id': 'category_id',
                                       'name': 'Category name'}
                                  ]}
                    )])
                )])
            )])
        )])
    ))
    def test_update_resources(
            self,
            mock_get_course,
            mock_get_edflex_configuration_for_org,
            mock_edflex_oauth_client,
            mock_modulestore,
            mock_course_overview_all,
            mock_get_user_model,
    ):
        # act:
        update_resources()

        # assert:
        mock_get_user_model().objects.filter().first.assert_called_once_with()
        mock_course_overview_all.assert_called_once_with()

        mock_edflex_oauth_client.assert_called_once()
        mock_get_edflex_configuration_for_org.assert_called_once_with('course_org')

        mock_get_course.assert_called_with('course_overview_id', depth=4)
        mock_get_course().get_children.assert_called()

        section = mock_get_course().get_children()[0]
        section.get_children.assert_called()

        subsection = section.get_children()[0]
        subsection.get_children.assert_called()

        unit = subsection.get_children()[0]
        unit.get_children.assert_called()

        xblock = unit.get_children()[0]

        mock_edflex_oauth_client().get_resource.assert_called_with('resource_id')
        xblock.location.for_branch.assert_called_with('draft-branch')
        xblock.save.assert_called()
        mock_modulestore().update_item.assert_called_with(xblock, 'user_id', asides=[])
        mock_modulestore().publish.assert_called_with(xblock.location, 'user_id')
        self.assertEqual(
            xblock.resource,
            {
                'id': 'resource_id',
                'title': 'New title',
                'type': 'video',
                'language': 'en',
                'categories': [
                    {'id': 'category_id',
                     'name': 'Category name'}
                ]
            }
        )

    @mock.patch('edflex.tasks.get_user_model', return_value=mock.Mock(
        objects=mock.Mock(filter=mock.Mock(return_value=mock.Mock(
            first=mock.Mock(return_value=mock.Mock(id='user_id'))
        )))
    ))
    @mock.patch('edflex.tasks.CourseOverview.objects.all', return_value=[mock.Mock(id='course_overview_id')])
    @mock.patch('edflex.tasks.modulestore', return_value=mock.Mock(
        update_item=mock.Mock(),
        publish=mock.Mock()
    ))
    @mock.patch('edflex.tasks.EdflexOauthClient', return_value=mock.Mock(
        get_resource=mock.Mock(return_value={'id': 'resource_id',
                                             'title': 'title',
                                             'type': 'video',
                                             'language': 'fr',
                                             'categories': [
                                                 {'id': 'category_id',
                                                  'name': 'Category name'}
                                             ]})
    ))
    @mock.patch('edflex.tasks.get_edflex_configuration_for_org')
    @mock.patch('edflex.tasks.get_course', return_value=mock.Mock(
        location=mock.Mock(org='course_org'),
        get_children=mock.Mock(return_value=[mock.Mock(
            get_children=mock.Mock(return_value=[mock.Mock(
                get_children=mock.Mock(return_value=[mock.Mock(
                    get_children=mock.Mock(return_value=[mock.Mock(
                        save=mock.Mock(),
                        location=mock.Mock(block_type='edflex', for_branch=mock.Mock()),
                        resource={'id': 'resource_id',
                                  'title': 'title',
                                  'type': 'video',
                                  'language': 'fr',
                                  'categories': [
                                      {'id': 'category_id',
                                       'name': 'Category name'}
                                  ]}
                    )])
                )])
            )])
        )])
    ))
    def test_update_resources_when_resource_has_not_changed(
            self,
            mock_get_course,
            mock_get_edflex_configuration_for_org,
            mock_edflex_oauth_client,
            mock_modulestore,
            mock_course_overview_all,
            mock_get_user_model,
    ):
        # act:
        update_resources()

        # assert:
        mock_get_user_model().objects.filter().first.assert_called_once_with()
        mock_course_overview_all.assert_called_once_with()

        mock_edflex_oauth_client.assert_called_once()
        mock_get_edflex_configuration_for_org.assert_called_once_with('course_org')

        mock_get_course.assert_called_with('course_overview_id', depth=4)
        mock_get_course().get_children.assert_called()

        section = mock_get_course().get_children()[0]
        section.get_children.assert_called()

        subsection = section.get_children()[0]
        subsection.get_children.assert_called()

        unit = subsection.get_children()[0]
        unit.get_children.assert_called()

        xblock = unit.get_children()[0]

        mock_edflex_oauth_client().get_resource.assert_called_with('resource_id')
        xblock.location.for_branch.assert_not_called()
        xblock.save.assert_not_called()
        mock_modulestore().update_item.assert_not_called()
        mock_modulestore().publish.assert_not_called()

    @mock.patch('edflex.tasks.EDFLEX_CLIENT_ID', None)
    @mock.patch('edflex.tasks.EDFLEX_CLIENT_SECRET', None)
    @mock.patch('edflex.tasks.EDFLEX_BASE_API_URL', None)
    @mock.patch('edflex.tasks.fetch_new_resources_and_delete_old_resources')
    def test_fetch_new_edflex_data_with_site_configurations(self, mock_fetch_new_resources_and_delete_old_resources):
        # arrange:
        with mock.patch('openedx.core.djangoapps.site_configuration.models.SiteConfiguration.objects.filter',
                        return_value=[mock.Mock(), mock.Mock(), mock.Mock()]) as site_configuration_filter:
            # act:
            fetch_new_edflex_data()

            # assert:
            site_configuration_filter.assert_called_once_with(enabled=True)
            self.assertEqual(mock_fetch_new_resources_and_delete_old_resources.call_count, 3)

    @mock.patch('edflex.tasks.EDFLEX_CLIENT_ID', 'client_id')
    @mock.patch('edflex.tasks.EDFLEX_CLIENT_SECRET', 'client_secret')
    @mock.patch('edflex.tasks.EDFLEX_LOCALE', 'en')
    @mock.patch('edflex.tasks.EDFLEX_BASE_API_URL', 'base_api_url')
    @mock.patch('edflex.tasks.fetch_new_resources_and_delete_old_resources')
    @mock.patch('openedx.core.djangoapps.site_configuration.models.SiteConfiguration.objects.filter', return_value=[])
    def test_fetch_new_edflex_data_with_default_settings(
            self,
            mock_site_configuration_filter,
            mock_fetch_new_resources_and_delete_old_resources
    ):
        # act:
        fetch_new_edflex_data()

        # assert:
        mock_site_configuration_filter.assert_called_once_with(enabled=True)
        mock_fetch_new_resources_and_delete_old_resources.assert_called_once_with(
            'client_id', 'client_secret', 'en', 'base_api_url'
        )

    @mock.patch('edflex.models.Resource.objects.filter',
                return_value=mock.Mock(
                    exclude=mock.Mock(return_value=mock.Mock(delete=mock.Mock())),
                    first=mock.Mock(return_value=None)
                ))
    @mock.patch('edflex.models.Category.objects.update_or_create',
                return_value=(mock.Mock(id='obj_category_id'), mock.Mock()))
    @mock.patch('edflex.models.Resource.objects.update_or_create',
                return_value=(mock.Mock(id='obj_resource_id'), mock.Mock()))
    @mock.patch('edflex.tasks.EdflexOauthClient', return_value=mock.Mock(
        get_catalogs=mock.Mock(return_value=[{'id': 'catalog_id_1', 'title': 'Catalog title1'},
                                             {'id': 'catalog_id_2', 'title': 'Catalog title2'}
                                             ]),
        get_catalog=mock.Mock(return_value={'id': 'catalog_id',
                                            'title': 'Catalog title',
                                            'items': [
                                                {'resource': {'id': 'resource_id'}}
                                            ]}),
        get_resource=mock.Mock(return_value={'id': 'resource_id',
                                             'title': 'title',
                                             'type': 'type',
                                             'language': 'language',
                                             'categories': [
                                                 {'id': 'category_id', 'name': 'Category name'}
                                             ]})
    ))
    def test_fetch_new_resources_and_delete_old_resources(
            self,
            mock_edflex_oauth_client,
            mock_resources_update_or_create,
            mock_categories_update_or_create,
            mock_resource_filter,
    ):
        # act:
        fetch_new_resources_and_delete_old_resources('client_id', 'client_secret', 'en', 'base_api_url')

        # assert:
        mock_edflex_oauth_client.assert_called_once_with(
            {
                'client_id': 'client_id',
                'client_secret': 'client_secret',
                'locale': 'en',
                'base_api_url': 'base_api_url'
            }
        )
        mock_edflex_oauth_client().get_catalogs.assert_called_once_with()
        self.assertEqual(mock_edflex_oauth_client().get_catalog.call_count, 2)

        mock_resource_filter.assert_any_call(
            resource_id='resource_id',
            catalog_id='catalog_id_2'
        )
        mock_resource_filter().first.assert_called()
        mock_edflex_oauth_client().get_resource.assert_any_call('resource_id')

        self.assertEqual(mock_resources_update_or_create.call_count, 2)
        mock_resources_update_or_create.assert_any_call(
            catalog_id='catalog_id_1',
            resource_id='resource_id',
            defaults={
                'title': 'title',
                'r_type': 'type',
                'language': 'language'
            }
        )

        self.assertEqual(mock_categories_update_or_create.call_count, 2)
        mock_categories_update_or_create.assert_any_call(
            category_id='category_id',
            catalog_id='catalog_id_1',
            defaults={'name': 'Category name',
                      'catalog_title': 'Catalog title1'}
        )

        mock_resource_filter.assert_any_call(catalog_id='catalog_id_2')
        mock_resource_filter().exclude.assert_any_call(id__in=['obj_resource_id'])
        mock_resource_filter().exclude().delete.assert_called()

    @mock.patch('edflex.models.Resource.objects.filter',
                return_value=mock.Mock(
                    exclude=mock.Mock(return_value=mock.Mock(delete=mock.Mock())),
                    first=mock.Mock(return_value=(mock.Mock(id='old_resource_id')))
                ))
    @mock.patch('edflex.models.Category.objects.update_or_create')
    @mock.patch('edflex.models.Resource.objects.update_or_create')
    @mock.patch('edflex.tasks.EdflexOauthClient', return_value=mock.Mock(
        get_catalogs=mock.Mock(return_value=[{'id': 'catalog_id_1', 'title': 'Catalog title1'},
                                             {'id': 'catalog_id_2', 'title': 'Catalog title2'}
                                             ]),
        get_catalog=mock.Mock(return_value={'id': 'catalog_id',
                                            'title': 'Catalog title',
                                            'items': [
                                                {'resource': {'id': 'resource_id'}}
                                            ]}),
        get_resource=mock.Mock()
    ))
    def test_fetch_new_resources_and_delete_old_resources_when_no_new_resources(
            self,
            mock_edflex_oauth_client,
            mock_resources_update_or_create,
            mock_categories_update_or_create,
            mock_resource_filter,
    ):
        # act:
        fetch_new_resources_and_delete_old_resources('client_id', 'client_secret', 'en', 'base_api_url')

        # assert:
        mock_edflex_oauth_client.assert_called_once_with(
            {
                'client_id': 'client_id',
                'client_secret': 'client_secret',
                'locale': 'en',
                'base_api_url': 'base_api_url'
            }
        )
        mock_edflex_oauth_client().get_catalogs.assert_called_once_with()
        self.assertEqual(mock_edflex_oauth_client().get_catalog.call_count, 2)

        mock_resource_filter.assert_any_call(
            resource_id='resource_id',
            catalog_id='catalog_id_2'
        )
        mock_resource_filter().first.assert_called()
        mock_edflex_oauth_client().get_resource.assert_not_called()

        mock_resources_update_or_create.assert_not_called()

        mock_categories_update_or_create.assert_not_called()

        mock_resource_filter.assert_any_call(catalog_id='catalog_id_2')
        mock_resource_filter().exclude.assert_any_call(id__in=['old_resource_id'])
        mock_resource_filter().exclude().delete.assert_called()


class TestEdflex(TestCase):

    def create_one(self, **kwargs):
        field_data = DictFieldData(kwargs)
        block = EdflexXBlock(mock.Mock(), field_data, mock.Mock())
        block.location = mock.Mock(
            block_id='block_id',
            org='org',
            course='course',
            block_type='block_type'
        )
        return block

    def test_fields_xblock(self):
        # act:
        test_instance = self.create_one()

        # assert:
        self.assertEqual(test_instance.display_name, "External Resource")
        self.assertEqual(test_instance.format, None)
        self.assertEqual(test_instance.category, None)
        self.assertEqual(test_instance.catalog, None)
        self.assertEqual(test_instance.language, None)
        self.assertEqual(test_instance.resource, {})
        self.assertEqual(test_instance.weight, 1.0)
        self.assertEqual(test_instance.score, 0)
        self.assertEqual(test_instance.icon_class, 'problem')
        self.assertEqual(test_instance.count_stars, 5)
        self.assertEqual(test_instance.has_score, True)
        self.assertEqual(test_instance.has_author_view, True)
        self.assertEqual(
            test_instance.editable_fields,
            ['format', 'category', 'catalog', 'language', 'resource', 'weight']
        )

    @mock.patch('edflex.edflex.loader.render_django_template', return_value='html')
    @mock.patch('edflex.edflex.EdflexXBlock.update_student_context')
    @mock.patch('edflex.edflex.Fragment', return_value=mock.Mock(initialize_js=mock.Mock(),
                                                                 add_javascript_url=mock.Mock(),
                                                                 add_javascript=mock.Mock(),
                                                                 add_css=mock.Mock()))
    def test_student_view(self, mock_fragment, mock_update_student_context, mock_render_django_template):
        # arrange:
        test_instance = self.create_one(resource={'type': 'video'})

        # act:
        test_instance.student_view()

        # assert:
        mock_update_student_context.assert_called_with(
            {'svg_sprite': test_instance.resource_string('public/images/sprite.svg')})
        mock_fragment.assert_called_once()
        mock_render_django_template.assert_called_with(
            'static/html/edflex.html',
            {'svg_sprite': test_instance.resource_string('public/images/sprite.svg')}
        )
        mock_fragment().add_css.assert_called_with(
            test_instance.resource_string("static/css/edflex.css")
        )
        mock_fragment().add_javascript_url.assert_called_with(
            'https://www.youtube.com/iframe_api'
        )
        mock_fragment().add_javascript.assert_called_with(
            test_instance.resource_string("static/js/src/edflex.js")
        )
        mock_fragment().initialize_js.assert_called_with('EdflexXBlock')

    @mock.patch('edflex.edflex.loader.render_django_template', return_value='html')
    @mock.patch('edflex.edflex.EdflexXBlock.update_student_context')
    @mock.patch('edflex.edflex.Fragment',
                return_value=mock.Mock(initialize_js=mock.Mock(),
                                       add_javascript_url=mock.Mock(),
                                       add_javascript=mock.Mock(),
                                       add_css=mock.Mock()))
    def test_student_view_with_context_and_non_video_resource(
            self,
            mock_fragment,
            mock_update_student_context,
            mock_render_django_template
    ):
        # arrange:
        test_instance = self.create_one(resource={'type': 'mooc'})
        test_context = {
            'key': 'value',
            'svg_sprite': test_instance.resource_string('public/images/sprite.svg')
        }

        # act:
        test_instance.student_view(context=test_context)

        # assert:
        mock_update_student_context.assert_called_with(test_context)
        mock_fragment.assert_called_once()
        mock_render_django_template.assert_called_with('static/html/edflex.html', test_context)
        mock_fragment().add_css.assert_called_with(test_instance.resource_string("static/css/edflex.css"))
        mock_fragment().add_javascript_url.assert_not_called()
        mock_fragment().add_javascript.assert_called_with(test_instance.resource_string("static/js/src/edflex.js"))
        mock_fragment().initialize_js.assert_called_with('EdflexXBlock')

    def test_update_student_context(self):
        # arrange:
        test_instance = self.create_one(resource={'type': 'mooc'}, score=1)

        # act:
        result = test_instance.update_student_context(context={'key': 'value'})

        # assert:
        self.assertEqual(
            result,
            {
                'score': 1,
                'resource': {'type': 'mooc'},
                'stars': {
                    'total_reviews': None,
                    'average': '-',
                    'full': [],
                    'empty': [0, 1, 2, 3, 4],
                    'half': []
                },
                'key': 'value'
            }
        )

    @mock.patch('edflex.edflex.loader.load_unicode', return_value='unicode')
    @mock.patch('edflex.edflex.loader.render_django_template', return_value='html')
    @mock.patch('edflex.edflex.Fragment', return_value=mock.Mock(initialize_js=mock.Mock(),
                                                                 add_javascript_url=mock.Mock(),
                                                                 add_javascript=mock.Mock(),
                                                                 add_css=mock.Mock()))
    @mock.patch('edflex.edflex.EdflexXBlock.update_studio_context')
    def test_studio_view(self, mock_update_studio_context, mock_self, mock_render_django_template, mock_load_unicode):
        # arrange:
        test_instance = self.create_one()
        test_context = {'key': 'value'}

        # act:
        test_instance.studio_view(context=test_context)

        # assert:
        mock_update_studio_context.assert_called_with(test_context)
        mock_render_django_template.assert_called_with('static/html/studio_edit.html', test_context)
        mock_load_unicode.assert_called_with('static/js/src/studio_edit.js')
        mock_self().add_javascript.assert_called_with(mock_load_unicode())
        mock_self().initialize_js.assert_called_once()
        self.assertEqual(mock_self().add_css.call_count, 2)

    @mock.patch('edflex.edflex.Resource.objects.filter', return_value=mock.Mock(
        order_by=mock.Mock(return_value=mock.Mock(
            values_list=mock.Mock(return_value=mock.Mock(distinct=mock.Mock()))))
    ))
    @mock.patch('edflex.edflex.Category.objects.filter', return_value=mock.Mock(
        order_by=mock.Mock(return_value=mock.Mock(distinct=mock.Mock(return_value=mock.Mock(values=mock.Mock()))))))
    @mock.patch('edflex.edflex.get_edflex_configuration_for_org', return_value='configuration')
    @mock.patch('edflex.edflex.EdflexOauthClient.get_catalogs')
    @mock.patch('edflex.edflex.EdflexOauthClient')
    def test_update_studio_context(
            self,
            mock_edflex_oauth_client,
            mock_get_catalogs,
            mock_get_edflex_configuration_for_org,
            mock_category_filter,
            mock_resource_filter
    ):
        # arrange:
        test_instance = self.create_one()
        test_context = {'key': 'value'}

        # act:
        result = test_instance.update_studio_context(test_context)

        # assert:
        mock_get_edflex_configuration_for_org.assert_called_once_with(test_instance.location.org)
        mock_edflex_oauth_client.assert_called_with('configuration')
        mock_get_catalogs.assert_called_once()
        mock_category_filter.assert_called_with(resources__catalog_id__in=[])
        mock_category_filter().order_by.assert_called_with('name')
        mock_category_filter().order_by().distinct.assert_called_once()
        mock_category_filter().order_by().distinct().values.assert_called_once()
        mock_resource_filter.assert_called_with(catalog_id__in=[], language__isnull=False)
        mock_resource_filter().order_by.assert_called_with('language')
        mock_resource_filter().order_by().values_list.assert_called_with('language', flat=True)
        mock_resource_filter().order_by().values_list().distinct.assert_called_once()
        self.assertEqual(
            result,
            {
                'languages': mock_resource_filter().order_by().values_list().distinct(),
                'categories': mock_category_filter().order_by().distinct().values(),
                'weight': 1.0,
                'key': 'value'
            }
        )

    @mock.patch('edflex.models.Resource.objects.filter')
    @mock.patch('edflex.edflex.EdflexOauthClient')
    @mock.patch('edflex.edflex.get_edflex_configuration_for_org')
    def test_get_list_resources_when_not_set_required_parameters(
            self,
            mock_get_edflex_configuration_for_org,
            mock_edflex_oauth_client,
            mock_resource_filter
    ):
        # arrange:
        test_instance = self.create_one()
        data = {'format': None, 'category': None, 'language': 'test_language'}

        # act:
        response = test_instance.get_list_resources(mock.Mock(method="POST", body=json.dumps(data)))

        # assert:
        mock_get_edflex_configuration_for_org.assert_not_called()
        mock_edflex_oauth_client.assert_not_called()
        mock_resource_filter.assert_not_called()
        self.assertEqual(response.json, {'resources': []})

    @mock.patch('edflex.models.Category.objects.get', return_value=mock.Mock(id='id', catalog_id='catalog_id'))
    @mock.patch('edflex.models.Resource.objects.filter', return_value=mock.Mock(
        filter=mock.Mock(return_value=mock.Mock(
            filter=mock.Mock(return_value=mock.Mock(
                distinct=mock.Mock(return_value=mock.Mock(
                    values=mock.Mock(return_value=[{'resource_id': 'resource_id', 'title': 'title'}]))))))
        )))
    @mock.patch('edflex.edflex.EdflexOauthClient', return_value=mock.Mock(get_catalogs=mock.Mock(return_value=[])))
    @mock.patch('edflex.edflex.get_edflex_configuration_for_org', return_value={
        'client_id': '100',
        'client_secret': 'test_client_secret',
        'base_api_url': "https://test.base.url"
    })
    def test_get_list_resources(
            self,
            mock_get_edflex_configuration_for_org,
            mock_edflex_oauth_client,
            mock_resource_filter,
            mock_category_get
    ):
        # arrange:
        test_instance = self.create_one()
        data = {'format': 'format', 'category_id': 'category_id', 'language': 'language'}

        # act:
        response = test_instance.get_list_resources(mock.Mock(method="POST", body=json.dumps(data)))

        # assert:
        mock_get_edflex_configuration_for_org.assert_called_once_with(test_instance.location.org)
        mock_edflex_oauth_client.assert_called_once_with(
            {
                'client_id': '100',
                'client_secret': 'test_client_secret',
                'base_api_url': "https://test.base.url"
            }
        )
        mock_edflex_oauth_client().get_catalogs.assert_called_once_with()
        mock_resource_filter.assert_called_with(
            r_type='format',
        )
        mock_category_get.assert_called_with(id='category_id')
        mock_resource_filter().filter.assert_called_with(categories__id='id', catalog_id='catalog_id')
        mock_resource_filter().filter().filter.assert_called_with(language='language')
        mock_resource_filter().filter().filter().distinct.assert_called_once()
        mock_resource_filter().filter().filter().distinct().values.assert_called_with('resource_id', 'title')
        self.assertEqual(
            response.json,
            {'resources': [{'resource_id': 'resource_id', 'title': 'title'}]}
        )

    @mock.patch('edflex.edflex.EdflexOauthClient', return_value=mock.Mock(
        get_resource=mock.Mock(return_value={'id': 'resource_id', 'title': 'title'})
    ))
    @mock.patch('edflex.edflex.get_edflex_configuration_for_org', return_value={
        'client_id': '100',
        'client_secret': 'test_client_secret',
        'base_api_url': "https://test.base.url"
    })
    def test_get_resource(self, mock_get_edflex_configuration_for_org, mock_edflex_oauth_client):
        # arrange:
        test_instance = self.create_one()
        data = {'resource': 'resource_id'}

        # act:
        response = test_instance.get_resource(mock.Mock(method="POST", body=json.dumps(data)))

        # assert:
        mock_get_edflex_configuration_for_org.assert_called_once_with(test_instance.location.org)
        mock_edflex_oauth_client.assert_called_once_with(
            {
                'client_id': '100',
                'client_secret': 'test_client_secret',
                'base_api_url': "https://test.base.url"
            }
        )
        mock_edflex_oauth_client().get_resource.assert_called_with('resource_id')
        self.assertEqual(
            response.json,
            {'id': 'resource_id', 'title': 'title'}
        )

    @mock.patch('edflex.edflex.EdflexXBlock.publish_grade')
    def test_set_grade(self, mock_publish_grade):
        # arrange:
        test_instance = self.create_one()
        data = {'score': 5}

        # act:
        response = test_instance.set_grade(mock.Mock(method="POST", body=json.dumps(data)))

        # assert:
        self.assertEqual(test_instance.score, 5)
        mock_publish_grade.assert_called()
        self.assertEqual(response.json, {'status': 'ok'})

    @mock.patch('edflex.edflex.EdflexXBlock.publish_grade')
    def test_set_grade_score_is_not_bigger(self, mock_publish_grade):
        # arrange:
        test_instance = self.create_one(score=1)
        data = {'score': 0}

        # act:
        response = test_instance.set_grade(mock.Mock(method="POST", body=json.dumps(data)))

        # assert:
        self.assertEqual(test_instance.score, 1)
        mock_publish_grade.assert_not_called()
        self.assertEqual(response.json, {'status': 'ok'})

    @mock.patch('edflex.edflex.Fragment', return_value='frag')
    @mock.patch('edflex.edflex.loader.render_django_template', return_value='html')
    def test_author_view(self, mock_render_django_template, mock_fragment):
        # arrange:
        test_instance = self.create_one()

        # act:
        result = test_instance.author_view()

        # assert:
        mock_render_django_template.assert_called_with("static/html/author_view.html", None)
        mock_fragment.assert_called_with(mock_render_django_template())
        self.assertEqual(result, 'frag')

    def test_max_score(self):
        # arrange:
        test_instance = self.create_one(weight=5)

        # act:
        result = test_instance.max_score()

        # assert:
        self.assertEqual(result, 5)

    def test_publish_grade(self):
        # arrange:
        test_instance = self.create_one(score=1, weight=3)
        mock_publish = test_instance.runtime.publish = mock.Mock()

        # act:
        test_instance.publish_grade()

        # assert:
        mock_publish.assert_called_with(
            test_instance,
            'grade',
            {
                'value': 3.0,
                'max_value': 3.0,
            }
        )
