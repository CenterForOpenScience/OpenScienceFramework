import mock

from webtest_plus import TestApp
from dataverse import Connection, Dataverse, Dataset, DataverseFile

from website.addons.base.testing import AddonTestCase


class DataverseAddonTestCase(AddonTestCase):
    ADDON_SHORT_NAME = 'dataverse'

    def create_app(self):
        return TestApp(app)

    def set_user_settings(self, settings):
        settings.api_token = 'snowman-frosty'

    def set_node_settings(self, settings):
        settings.dataverse_alias = 'ALIAS2'
        settings.dataverse = 'Example 2'
        settings.dataset_doi = 'doi:12.3456/DVN/00001'
        settings.dataset_id = '18'
        settings.dataset = 'Example (DVN/00001)'


def create_mock_connection(token='snowman-frosty'):
    """
    Create a mock dataverse connection.

    Pass any credentials other than the default parameters and the connection
    will return none.
    """
    if not token == 'snowman-frosty':
        return None

    mock_connection = mock.create_autospec(Connection)

    mock_connection.token = token

    mock_connection.get_dataverses.return_value = [
        create_mock_dataverse('Example 1'),
        create_mock_dataverse('Example 2'),
        create_mock_dataverse('Example 3'),
    ]

    def _get_dataverse(alias):
        return next((
            dataverse for dataverse in mock_connection.get_dataverses()
            if alias is not None and dataverse.title[-1] == alias[-1]), None
        )

    mock_connection.get_dataverse = mock.MagicMock(
        side_effect=_get_dataverse
    )
    mock_connection.get_dataverse.return_value = create_mock_dataverse()

    return mock_connection


def create_mock_dataverse(title='Example Dataverse 0'):

    mock_dataverse = mock.create_autospec(Dataverse)

    type(mock_dataverse).title = mock.PropertyMock(return_value=title)
    type(mock_dataverse).is_published = mock.PropertyMock(return_value=True)
    type(mock_dataverse).alias = mock.PropertyMock(
        return_value='ALIAS{}'.format(title[-1])
    )

    mock_dataverse.get_datasets.return_value = [
        create_mock_dataset('DVN/00001'),
        create_mock_dataset('DVN/00002'),
        create_mock_dataset('DVN/00003'),
    ]

    def _get_dataset_by_doi(doi):
        return next((
            dataset for dataset in mock_dataverse.get_datasets()
            if dataset.doi == doi), None
        )

    mock_dataverse.get_dataset_by_doi = mock.MagicMock(
        side_effect=_get_dataset_by_doi
    )

    return mock_dataverse


def create_mock_dataset(id='DVN/12345'):
    mock_dataset = mock.create_autospec(Dataset)

    mock_dataset.citation = 'Example Citation for {0}'.format(id)
    mock_dataset.title = 'Example ({0})'.format(id)
    mock_dataset.doi = 'doi:12.3456/{0}'.format(id)
    mock_dataset.id = '18'
    mock_dataset.get_state.return_value = 'DRAFT'

    def _create_file(name, published=False):
        return create_mock_published_file() if published else create_mock_draft_file()

    def _create_files(published=False):
        return [_create_file('name.txt', published)]

    mock_dataset.get_files = mock.MagicMock(side_effect=_create_files)
    mock_dataset.get_file = mock.MagicMock(side_effect=_create_file)
    mock_dataset.get_file_by_id = mock.MagicMock(side_effect=_create_file)

    # Fail if not given a valid ID
    if 'DVN' in id:
        return mock_dataset

def create_mock_draft_file(id='54321'):
    mock_file = mock.create_autospec(DataverseFile)

    mock_file.name = 'file.txt'
    mock_file.id = id
    mock_file.is_published = False

    return mock_file

def create_mock_published_file(id='54321'):
    mock_file = mock.create_autospec(DataverseFile)

    mock_file.name = 'published.txt'
    mock_file.id = id
    mock_file.is_published = True

    return mock_file

mock_responses = {
    'contents': {
        u'kind': u'item',
        u'name': u'file.txt',
        u'ext': u'.txt',
        u'file_id': u'54321',
        u'urls': {u'download': u'/project/xxxxx/dataverse/file/54321/download/',
                 u'delete': u'/api/v1/project/xxxxx/dataverse/file/54321/',
                 u'view': u'/project/xxxxx/dataverse/file/54321/'},
        u'permissions': {u'edit': False, u'view': True},
        u'addon': u'dataverse',
        u'hasPublishedFiles': True,
        u'state': 'published',
    }
}
