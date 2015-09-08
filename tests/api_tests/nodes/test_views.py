# -*- coding: utf-8 -*-
import mock
from urlparse import urlparse
from nose.tools import *  # flake8: noqa

from website.models import Node
from framework.auth.core import Auth
from website.util.sanitize import strip_html
from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase, fake
from tests.factories import (
    DashboardFactory,
    FolderFactory,
    NodeFactory,
    ProjectFactory,
    RegistrationFactory,
    UserFactory,
    AuthUserFactory
)

class TestWelcomeToApi(ApiTestCase):
    def setUp(self):
        super(TestWelcomeToApi, self).setUp()
        self.user = AuthUserFactory()
        self.url = '/{}'.format(API_BASE)

    def test_returns_200_for_logged_out_user(self):
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['meta']['current_user'], None)

    def test_returns_current_user_info_when_logged_in(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['meta']['current_user']['data']['attributes']['given_name'], self.user.given_name)


class TestNodeList(ApiTestCase):
    def setUp(self):
        super(TestNodeList, self).setUp()
        self.user = AuthUserFactory()

        self.non_contrib = AuthUserFactory()

        self.deleted = ProjectFactory(is_deleted=True)
        self.private = ProjectFactory(is_public=False, creator=self.user)
        self.public = ProjectFactory(is_public=True, creator=self.user)

        self.url = '/{}nodes/'.format(API_BASE)

    def test_only_returns_non_deleted_public_projects(self):
        res = self.app.get(self.url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.public._id, ids)
        assert_not_in(self.deleted._id, ids)
        assert_not_in(self.private._id, ids)

    def test_return_public_node_list_logged_out_user(self):
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.public._id, ids)
        assert_not_in(self.private._id, ids)

    def test_return_public_node_list_logged_in_user(self):
        res = self.app.get(self.url, auth=self.non_contrib)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.public._id, ids)
        assert_not_in(self.private._id, ids)

    def test_return_private_node_list_logged_out_user(self):
        res = self.app.get(self.url)
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.public._id, ids)
        assert_not_in(self.private._id, ids)

    def test_return_private_node_list_logged_in_contributor(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.public._id, ids)
        assert_in(self.private._id, ids)

    def test_return_private_node_list_logged_in_non_contributor(self):
        res = self.app.get(self.url, auth=self.non_contrib.auth)
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.public._id, ids)
        assert_not_in(self.private._id, ids)



class TestNodeFiltering(ApiTestCase):

    def setUp(self):
        super(TestNodeFiltering, self).setUp()
        self.user_one = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.project_one = ProjectFactory(title="Project One", is_public=True)
        self.project_two = ProjectFactory(title="Project Two", description="One Three", is_public=True)
        self.project_three = ProjectFactory(title="Three", is_public=True)
        self.private_project_user_one = ProjectFactory(title="Private Project User One",
                                                       is_public=False,
                                                       creator=self.user_one)
        self.private_project_user_two = ProjectFactory(title="Private Project User Two",
                                                       is_public=False,
                                                       creator=self.user_two)
        self.folder = FolderFactory()
        self.dashboard = DashboardFactory()

        self.url = "/{}nodes/".format(API_BASE)

    def tearDown(self):
        super(TestNodeFiltering, self).tearDown()
        Node.remove()

    def test_get_all_projects_with_no_filter_logged_in(self):
        res = self.app.get(self.url, auth=self.user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_in(self.project_three._id, ids)
        assert_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_all_projects_with_no_filter_not_logged_in(self):
        res = self.app.get(self.url)
        node_json = res.json['data']
        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_one_project_with_exact_filter_logged_in(self):
        url = "/{}nodes/?filter[title]=Project%20One".format(API_BASE)

        res = self.app.get(url, auth=self.user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_not_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_one_project_with_exact_filter_not_logged_in(self):
        url = "/{}nodes/?filter[title]=Project%20One".format(API_BASE)

        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_not_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_some_projects_with_substring_logged_in(self):
        url = "/{}nodes/?filter[title]=Two".format(API_BASE)

        res = self.app.get(url, auth=self.user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_not_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_some_projects_with_substring_not_logged_in(self):
        url = "/{}nodes/?filter[title]=Two".format(API_BASE)

        res = self.app.get(url, auth=self.user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_not_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_only_public_or_my_projects_with_filter_logged_in(self):
        url = "/{}nodes/?filter[title]=Project".format(API_BASE)

        res = self.app.get(url, auth=self.user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_only_public_projects_with_filter_not_logged_in(self):
        url = "/{}nodes/?filter[title]=Project".format(API_BASE)

        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_alternate_filtering_field_logged_in(self):
        url = "/{}nodes/?filter[description]=Three".format(API_BASE)

        res = self.app.get(url, auth=self.user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_not_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_alternate_filtering_field_not_logged_in(self):
        url = "/{}nodes/?filter[description]=Three".format(API_BASE)

        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_not_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_incorrect_filtering_field_not_logged_in(self):
        url = '/{}nodes/?filter[notafield]=bogus'.format(API_BASE)

        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 400)
        errors = res.json['errors']
        assert_equal(len(errors), 1)
        assert_equal(errors[0]['detail'], 'Querystring contains an invalid filter.')


class TestNodeCreate(ApiTestCase):

    def setUp(self):
        super(TestNodeCreate, self).setUp()
        self.user_one = AuthUserFactory()
        self.url = '/{}nodes/'.format(API_BASE)

        self.title = 'Cool Project'
        self.description = 'A Properly Cool Project'
        self.category = 'data'

        self.user_two = AuthUserFactory()

        self.public_project = {'title': self.title,
                               'description': self.description,
                               'category': self.category,
                               'public': True}
        self.private_project = {'title': self.title,
                                'description': self.description,
                                'category': self.category,
                                'public': False}

    def test_creates_public_project_logged_out(self):
        res = self.app.post_json_api(self.url, self.public_project, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

    def test_creates_public_project_logged_in(self):
        res = self.app.post_json_api(self.url, self.public_project, auth=self.user_one.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['title'], self.public_project['title'])
        assert_equal(res.json['data']['attributes']['description'], self.public_project['description'])
        assert_equal(res.json['data']['attributes']['category'], self.public_project['category'])
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_creates_private_project_logged_out(self):
        res = self.app.post_json_api(self.url, self.private_project, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

    def test_creates_private_project_logged_in_contributor(self):
        res = self.app.post_json_api(self.url, self.private_project, auth=self.user_one.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.private_project['title'])
        assert_equal(res.json['data']['attributes']['description'], self.private_project['description'])
        assert_equal(res.json['data']['attributes']['category'], self.private_project['category'])

    def test_creates_project_creates_project_and_sanitizes_html(self):
        title = '<em>Cool</em> <strong>Project</strong>'
        description = 'An <script>alert("even cooler")</script> project'

        res = self.app.post_json_api(self.url, {
            'title': title,
            'description': description,
            'category': self.category,
            'public': True,
        }, auth=self.user_one.auth)
        project_id = res.json['data']['id']
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        url = '/{}nodes/{}/'.format(API_BASE, project_id)

        res = self.app.get(url, auth=self.user_one.auth)
        assert_equal(res.json['data']['attributes']['title'], strip_html(title))
        assert_equal(res.json['data']['attributes']['description'], strip_html(description))
        assert_equal(res.json['data']['attributes']['category'], self.category)


class TestNodeDetail(ApiTestCase):
    def setUp(self):
        super(TestNodeDetail, self).setUp()
        self.user = AuthUserFactory()

        self.user_two = AuthUserFactory()

        self.public_project = ProjectFactory(title="Project One", is_public=True, creator=self.user)
        self.private_project = ProjectFactory(title="Project Two", is_public=False, creator=self.user)
        self.public_url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        self.private_url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)

        self.public_component = NodeFactory(parent=self.public_project, creator=self.user, is_public=True)
        self.public_component_url = '/{}nodes/{}/'.format(API_BASE, self.public_component._id)

    def test_return_public_project_details_logged_out(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.public_project.title)
        assert_equal(res.json['data']['attributes']['description'], self.public_project.description)
        assert_equal(res.json['data']['attributes']['category'], self.public_project.category)

    def test_return_public_project_details_logged_in(self):
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.public_project.title)
        assert_equal(res.json['data']['attributes']['description'], self.public_project.description)
        assert_equal(res.json['data']['attributes']['category'], self.public_project.category)

    def test_return_private_project_details_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]


    def test_return_private_project_details_logged_in_contributor(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.private_project.title)
        assert_equal(res.json['data']['attributes']['description'], self.private_project.description)
        assert_equal(res.json['data']['attributes']['category'], self.private_project.category)

    def test_return_private_project_details_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

    def test_top_level_project_has_no_parent(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['relationships']['parent']['links']['self'], None)
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_child_project_has_parent(self):
        public_component = NodeFactory(parent=self.public_project, creator=self.user, is_public=True)
        public_component_url = '/{}nodes/{}/'.format(API_BASE, public_component._id)
        res = self.app.get(public_component_url)
        assert_equal(res.status_code, 200)
        url = res.json['data']['relationships']['parent']['links']['self']
        assert_equal(urlparse(url).path, self.public_url)

    def test_node_has_children_link(self):
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['children']['links']['related']['href']
        expected_url = self.public_url + 'children/'
        assert_equal(urlparse(url).path, expected_url)

    def test_node_has_contributors_link(self):
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['contributors']['links']['related']['href']
        expected_url = self.public_url + 'contributors/'
        assert_equal(urlparse(url).path, expected_url)

    def test_node_has_pointers_link(self):
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['node_links']['links']['related']['href']
        expected_url = self.public_url + 'node_links/'
        assert_equal(urlparse(url).path, expected_url)

    def test_node_has_registrations_link(self):
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['registrations']['links']['related']['href']
        expected_url = self.public_url + 'registrations/'
        assert_equal(urlparse(url).path, expected_url)

    def test_node_has_files_link(self):
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['files']['links']['related']
        expected_url = self.public_url + 'files/'
        assert_equal(urlparse(url).path, expected_url)

    def test_node_properties(self):
        res = self.app.get(self.public_url)
        assert_equal(res.json['data']['attributes']['public'], True)
        assert_equal(res.json['data']['attributes']['registration'], False)
        assert_equal(res.json['data']['attributes']['collection'], False)
        assert_equal(res.json['data']['attributes']['dashboard'], False)
        assert_equal(res.json['data']['attributes']['tags'], [])


class TestNodeUpdate(ApiTestCase):

    def setUp(self):
        super(TestNodeUpdate, self).setUp()
        self.user = AuthUserFactory()

        self.title = 'Cool Project'
        self.new_title = 'Super Cool Project'
        self.description = 'A Properly Cool Project'
        self.new_description = 'An even cooler project'
        self.category = 'data'
        self.new_category = 'project'

        self.user_two = AuthUserFactory()

        self.public_project = ProjectFactory(title=self.title,
                                             description=self.description,
                                             category=self.category,
                                             is_public=True,
                                             creator=self.user)
        self.public_url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)

        self.private_project = ProjectFactory(title=self.title,
                                              description=self.description,
                                              category=self.category,
                                              is_public=False,
                                              creator=self.user)
        self.private_url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)

    def test_update_public_project_logged_out(self):
        res = self.app.put_json_api(self.public_url, {
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': True,
        }, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]


    def test_update_public_project_logged_in(self):
        # Public project, logged in, contrib
        res = self.app.put_json_api(self.public_url, {
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': True,
        }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.new_title)
        assert_equal(res.json['data']['attributes']['description'], self.new_description)
        assert_equal(res.json['data']['attributes']['category'], self.new_category)

        # Public project, logged in, unauthorized
        res = self.app.put_json_api(self.public_url, {
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': True,
        }, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

    def test_update_private_project_logged_out(self):
        res = self.app.put_json_api(self.private_url, {
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': False,
        }, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

    def test_update_private_project_logged_in_contributor(self):
        res = self.app.put_json_api(self.private_url, {
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': False,
        }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.new_title)
        assert_equal(res.json['data']['attributes']['description'], self.new_description)
        assert_equal(res.json['data']['attributes']['category'], self.new_category)

    def test_update_private_project_logged_in_non_contributor(self):
        res = self.app.put_json_api(self.private_url, {
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': False,
        }, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

    def test_update_project_sanitizes_html_properly(self):
        """Post request should update resource, and any HTML in fields should be stripped"""
        new_title = '<strong>Super</strong> Cool Project'
        new_description = 'An <script>alert("even cooler")</script> project'
        project = self.project = ProjectFactory(
            title=self.title, description=self.description, category=self.category, is_public=True, creator=self.user)

        url = '/{}nodes/{}/'.format(API_BASE, project._id)
        res = self.app.put_json_api(url, {
            'title': new_title,
            'description': new_description,
            'category': self.new_category,
            'public': True,
        }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], strip_html(new_title))
        assert_equal(res.json['data']['attributes']['description'], strip_html(new_description))

    def test_partial_update_project_updates_project_correctly_and_sanitizes_html(self):
        new_title = 'An <script>alert("even cooler")</script> project'
        project = self.project = ProjectFactory(
            title=self.title, description=self.description, category=self.category, is_public=True, creator=self.user)

        url = '/{}nodes/{}/'.format(API_BASE, project._id)
        res = self.app.patch_json_api(url, {
            'title': new_title,
        }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')

        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], strip_html(new_title))
        assert_equal(res.json['data']['attributes']['description'], self.description)
        assert_equal(res.json['data']['attributes']['category'], self.category)

    def test_writing_to_public_field(self):
        title = "Cool project"
        description = 'A Properly Cool Project'
        category = 'data'
        project = self.project = ProjectFactory(
            title=title, description=description, category=category, is_public=True, creator=self.user)
        # Test non-contrib writing to public field
        url = '/{}nodes/{}/'.format(API_BASE, project._id)
        res = self.app.patch_json_api(url, {
            'is_public': False,
        }, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

        # Test creator writing to public field (supposed to be read-only)
        res = self.app.patch_json_api(url, {
            'is_public': False,
        }, auth=self.user.auth, expect_errors=True)
        assert_true(res.json['data']['attributes']['public'])
        # TODO: Figure out why the validator isn't raising when attempting to write to a read-only field
        # assert_equal(res.status_code, 403)

    def test_partial_update_public_project_logged_out(self):
        res = self.app.patch_json_api(self.public_url, {'title': self.new_title}, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

    def test_partial_update_public_project_logged_in(self):
        res = self.app.patch_json_api(self.public_url, {
            'title': self.new_title,
        }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.new_title)
        assert_equal(res.json['data']['attributes']['description'], self.description)
        assert_equal(res.json['data']['attributes']['category'], self.category)

        # Public resource, logged in, unauthorized
        res = self.app.patch_json_api(self.public_url, {
            'title': self.new_title,
        }, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

    def test_partial_update_private_project_logged_out(self):
        res = self.app.patch_json_api(self.private_url, {'title': self.new_title}, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

    def test_partial_update_private_project_logged_in_contributor(self):
        res = self.app.patch_json_api(self.private_url, {'title': self.new_title}, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.new_title)
        assert_equal(res.json['data']['attributes']['description'], self.description)
        assert_equal(res.json['data']['attributes']['category'], self.category)

    def test_partial_update_private_project_logged_in_non_contributor(self):
        res = self.app.patch_json_api(self.private_url,
                                  {'title': self.new_title},
                                  auth=self.user_two.auth,
                                  expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]


class TestNodeDelete(ApiTestCase):

    def setUp(self):
        super(TestNodeDelete, self).setUp()
        self.user = AuthUserFactory()

        self.project = ProjectFactory(creator=self.user, is_public=False)
        self.private_url = '/{}nodes/{}/'.format(API_BASE, self.project._id)

        self.user_two = AuthUserFactory()

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)

        self.fake_url = '/{}nodes/{}/'.format(API_BASE, '12345')

    def test_deletes_public_node_logged_out(self):
        res = self.app.delete(self.public_url, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]


    def test_deletes_public_node_fails_if_bad_auth(self):
        res = self.app.delete_json_api(self.public_url, auth=self.user_two.auth, expect_errors=True)
        self.public_project.reload()
        assert_equal(res.status_code, 403)
        assert_equal(self.public_project.is_deleted, False)
        assert 'detail' in res.json['errors'][0]


    def test_deletes_public_node_succeeds_as_owner(self):
        res = self.app.delete_json_api(self.public_url, auth=self.user.auth, expect_errors=True)
        self.public_project.reload()
        assert_equal(res.status_code, 204)
        assert_equal(self.public_project.is_deleted, True)

    def test_deletes_private_node_logged_out(self):
        res = self.app.delete(self.private_url, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]


    def test_deletes_private_node_logged_in_contributor(self):
        res = self.app.delete(self.private_url, auth=self.user.auth, expect_errors=True)
        self.project.reload()
        assert_equal(res.status_code, 204)
        assert_equal(self.project.is_deleted, True)

    def test_deletes_private_node_logged_in_non_contributor(self):
        res = self.app.delete(self.private_url, auth=self.user_two.auth, expect_errors=True)
        self.project.reload()
        assert_equal(res.status_code, 403)
        assert_equal(self.project.is_deleted, False)
        assert 'detail' in res.json['errors'][0]


    def test_deletes_private_node_logged_in_read_only_contributor(self):
        self.project.add_contributor(self.user_two, permissions=['read'])
        self.project.save()
        res = self.app.delete(self.private_url, auth=self.user_two.auth, expect_errors=True)
        self.project.reload()
        assert_equal(res.status_code, 403)
        assert_equal(self.project.is_deleted, False)
        assert 'detail' in res.json['errors'][0]


    def test_deletes_invalid_node(self):
        res = self.app.delete(self.fake_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert 'detail' in res.json['errors'][0]


class TestNodeContributorList(ApiTestCase):

    def setUp(self):
        super(TestNodeContributorList, self).setUp()
        self.user = AuthUserFactory()

        self.user_two = AuthUserFactory()

        self.private_project = ProjectFactory(is_public=False, creator=self.user)
        self.private_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.private_project._id)
        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.public_project._id)

    def test_return_public_contributor_list_logged_out(self):
        self.public_project.add_contributor(self.user_two)
        self.public_project.save()

        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(len(res.json['data']), 2)
        assert_equal(res.json['data'][0]['id'], self.user._id)
        assert_equal(res.json['data'][1]['id'], self.user_two._id)

    def test_return_public_contributor_list_logged_in(self):
        res = self.app.get(self.public_url, auth=self.user_two.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['id'], self.user._id)

    def test_return_private_contributor_list_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]


    def test_return_private_contributor_list_logged_in_contributor(self):
        self.private_project.add_contributor(self.user_two)
        self.private_project.save()

        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(len(res.json['data']), 2)
        assert_equal(res.json['data'][0]['id'], self.user._id)
        assert_equal(res.json['data'][1]['id'], self.user_two._id)

    def test_return_private_contributor_list_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

class TestNodeContributorFiltering(ApiTestCase):

    def setUp(self):
        super(TestNodeContributorFiltering, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)

    def test_filtering_node_with_only_bibliographic_contributors(self):

        base_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.project._id)
        # no filter
        res = self.app.get(base_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)

        # filter for bibliographic contributors
        url = base_url + '?filter[bibliographic]=True'
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(len(res.json['data']), 1)
        assert_true(res.json['data'][0]['attributes'].get('bibliographic', None))

        # filter for non-bibliographic contributors
        url = base_url + '?filter[bibliographic]=False'
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 0)

    def test_filtering_node_with_non_bibliographic_contributor(self):
        non_bibliographic_contrib = UserFactory()
        self.project.add_contributor(non_bibliographic_contrib, visible=False)
        self.project.save()

        base_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.project._id)

        # no filter
        res = self.app.get(base_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 2)

        # filter for bibliographic contributors
        url = base_url + '?filter[bibliographic]=True'
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)
        assert_true(res.json['data'][0]['attributes'].get('bibliographic', None))

        # filter for non-bibliographic contributors
        url = base_url + '?filter[bibliographic]=False'
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)
        assert_false(res.json['data'][0]['attributes'].get('bibliographic', None))

    def test_filtering_on_invalid_field(self):
        url = '/{}nodes/{}/contributors/?filter[invalid]=foo'.format(API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        errors = res.json['errors']
        assert_equal(len(errors), 1)
        assert_equal(errors[0]['detail'], 'Querystring contains an invalid filter.')

class TestNodeRegistrationList(ApiTestCase):
    def setUp(self):
        super(TestNodeRegistrationList, self).setUp()
        self.user = AuthUserFactory()

        self.project = ProjectFactory(is_public=False, creator=self.user)
        self.registration_project = RegistrationFactory(creator=self.user, project=self.project)
        self.project.save()
        self.private_url = '/{}nodes/{}/registrations/'.format(API_BASE, self.project._id)

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_registration_project = RegistrationFactory(creator=self.user, project=self.public_project)
        self.public_project.save()
        self.public_url = '/{}nodes/{}/registrations/'.format(API_BASE, self.public_project._id)

        self.user_two = AuthUserFactory()

    def test_return_public_registrations_logged_out(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data'][0]['attributes']['title'], self.public_project.title)

    def test_return_public_registrations_logged_in(self):
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['attributes']['category'], self.public_project.category)
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_return_private_registrations_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

    def test_return_private_registrations_logged_in_contributor(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['attributes']['category'], self.project.category)
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_return_private_registrations_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]


class TestNodeChildrenList(ApiTestCase):
    def setUp(self):
        super(TestNodeChildrenList, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory()
        self.project.add_contributor(self.user, permissions=['read', 'write'])
        self.project.save()
        self.component = NodeFactory(parent=self.project, creator=self.user)
        self.pointer = ProjectFactory()
        self.project.add_pointer(self.pointer, auth=Auth(self.user), save=True)
        self.private_project_url = '/{}nodes/{}/children/'.format(API_BASE, self.project._id)

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_project.save()
        self.public_component = NodeFactory(parent=self.public_project, creator=self.user, is_public=True)
        self.public_project_url = '/{}nodes/{}/children/'.format(API_BASE, self.public_project._id)

        self.user_two = AuthUserFactory()

    def test_node_children_list_does_not_include_pointers(self):
        res = self.app.get(self.private_project_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)

    def test_return_public_node_children_list_logged_out(self):
        res = self.app.get(self.public_project_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['id'], self.public_component._id)

    def test_return_public_node_children_list_logged_in(self):
        res = self.app.get(self.public_project_url, auth=self.user_two.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['id'], self.public_component._id)

    def test_return_private_node_children_list_logged_out(self):
        res = self.app.get(self.private_project_url, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]


    def test_return_private_node_children_list_logged_in_contributor(self):
        res = self.app.get(self.private_project_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['id'], self.component._id)

    def test_return_private_node_children_list_logged_in_non_contributor(self):
        res = self.app.get(self.private_project_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

    def test_node_children_list_does_not_include_unauthorized_projects(self):
        private_component = NodeFactory(parent=self.project)
        res = self.app.get(self.private_project_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)

    def test_node_children_list_does_not_include_deleted(self):
        child_project = NodeFactory(parent=self.public_project, creator=self.user)
        child_project.save()

        res = self.app.get(self.public_project_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        ids = [node['id'] for node in res.json['data']]
        assert_in(child_project._id, ids)
        assert_equal(2, len(ids))

        child_project.is_deleted = True
        child_project.save()

        res = self.app.get(self.public_project_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        ids = [node['id'] for node in res.json['data']]
        assert_not_in(child_project._id, ids)
        assert_equal(1, len(ids))



class TestNodeChildCreate(ApiTestCase):

    def setUp(self):
        super(TestNodeChildCreate, self).setUp()

        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()

        self.project = ProjectFactory(creator=self.user, is_publc=True)

        self.url = '/{}nodes/{}/children/'.format(API_BASE, self.project._id)
        self.child = {
            'title': 'child',
            'description': 'this is a child project',
            'category': 'project',
        }

    def test_creates_child_logged_out_user(self):
        res = self.app.post_json_api(self.url, self.child, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

        self.project.reload()
        assert_equal(len(self.project.nodes), 0)

    def test_creates_child_logged_in_owner(self):
        res = self.app.post_json_api(self.url, self.child, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['title'], self.child['title'])
        assert_equal(res.json['data']['attributes']['description'], self.child['description'])
        assert_equal(res.json['data']['attributes']['category'], self.child['category'])

        self.project.reload()
        assert_equal(res.json['data']['id'], self.project.nodes[0]._id)

    def test_creates_child_logged_in_write_contributor(self):
        self.project.add_contributor(self.user_two, permissions=['read', 'write'], auth=Auth(self.user), save=True)

        res = self.app.post_json_api(self.url, self.child, auth=self.user_two.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['title'], self.child['title'])
        assert_equal(res.json['data']['attributes']['description'], self.child['description'])
        assert_equal(res.json['data']['attributes']['category'], self.child['category'])

        self.project.reload()
        assert_equal(res.json['data']['id'], self.project.nodes[0]._id)

    def test_creates_child_logged_in_read_contributor(self):
        self.project.add_contributor(self.user_two, permissions=['read'], auth=Auth(self.user), save=True)
        self.project.reload()

        res = self.app.post_json_api(self.url, self.child, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        self.project.reload()
        assert_equal(len(self.project.nodes), 0)

    def test_creates_child_logged_in_non_contributor(self):
        res = self.app.post_json_api(self.url, self.child, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        self.project.reload()
        assert_equal(len(self.project.nodes), 0)

    def test_creates_child_creates_child_and_sanitizes_html_logged_in_owner(self):
        title = '<em>Cool</em> <strong>Project</strong>'
        description = 'An <script>alert("even cooler")</script> child'

        res = self.app.post_json_api(self.url, {
            'title': title,
            'description': description,
            'category': 'project',
            'public': True,
        }, auth=self.user.auth)
        child_id = res.json['data']['id']
        assert_equal(res.status_code, 201)
        url = '/{}nodes/{}/'.format(API_BASE, child_id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], strip_html(title))
        assert_equal(res.json['data']['attributes']['description'], strip_html(description))
        assert_equal(res.json['data']['attributes']['category'], 'project')

        self.project.reload()
        assert_equal(res.json['data']['id'], self.project.nodes[0]._id)


class TestNodePointersList(ApiTestCase):

    def setUp(self):
        super(TestNodePointersList, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(is_public=False, creator=self.user)
        self.pointer_project = ProjectFactory(is_public=False, creator=self.user)
        self.project.add_pointer(self.pointer_project, auth=Auth(self.user))
        self.private_url = '/{}nodes/{}/node_links/'.format(API_BASE, self.project._id)

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_pointer_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_project.add_pointer(self.public_pointer_project, auth=Auth(self.user))
        self.public_url = '/{}nodes/{}/node_links/'.format(API_BASE, self.public_project._id)

        self.user_two = AuthUserFactory()

    def test_return_public_node_pointers_logged_out(self):
        res = self.app.get(self.public_url)
        res_json = res.json['data']
        assert_equal(len(res_json), 1)
        assert_equal(res.status_code, 200)
        assert_in(res_json[0]['attributes']['target_node_id'], self.public_pointer_project._id)
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_return_public_node_pointers_logged_in(self):
        res = self.app.get(self.public_url, auth=self.user_two.auth)
        res_json = res.json['data']
        assert_equal(len(res_json), 1)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_in(res_json[0]['attributes']['target_node_id'], self.public_pointer_project._id)

    def test_return_private_node_pointers_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]


    def test_return_private_node_pointers_logged_in_contributor(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        res_json = res.json['data']
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(len(res_json), 1)
        assert_in(res_json[0]['attributes']['target_node_id'], self.pointer_project._id)

    def test_return_private_node_pointers_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]


class TestNodeTags(ApiTestCase):
    def setUp(self):
        super(TestNodeTags, self).setUp()
        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.read_only_contributor = AuthUserFactory()
        self.one_new_tag_json = {'tags': ['new-tag']}

        self.public_project = ProjectFactory(title="Project One", is_public=True, creator=self.user)
        self.public_project.add_contributor(self.user, permissions=['read'])
        self.private_project = ProjectFactory(title="Project Two", is_public=False, creator=self.user)
        self.private_project.add_contributor(self.user, permissions=['read'])
        self.public_url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        self.private_url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)

    def test_public_project_starts_with_no_tags(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']['attributes']['tags']), 0)

    def test_contributor_can_add_tag_to_public_project(self):
        res = self.app.patch_json(self.public_url, self.one_new_tag_json, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        # Ensure data is correct from the PATCH response
        assert_equal(len(res.json['data']['attributes']['tags']), 1)
        assert_equal(res.json['data']['attributes']['tags'][0], 'new-tag')
        # Ensure data is correct in the database
        self.public_project.reload()
        assert_equal(len(self.public_project.tags), 1)
        assert_equal(self.public_project.tags[0]._id, 'new-tag')
        # Ensure data is correct when GETting the resource again
        reload_res = self.app.get(self.public_url)
        assert_equal(len(reload_res.json['data']['attributes']['tags']), 1)
        assert_equal(reload_res.json['data']['attributes']['tags'][0], 'new-tag')

    def test_contributor_can_add_tag_to_private_project(self):
        res = self.app.patch_json(self.private_url, self.one_new_tag_json, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        # Ensure data is correct from the PATCH response
        assert_equal(len(res.json['data']['attributes']['tags']), 1)
        assert_equal(res.json['data']['attributes']['tags'][0], 'new-tag')
        # Ensure data is correct in the database
        self.private_project.reload()
        assert_equal(len(self.private_project.tags), 1)
        assert_equal(self.private_project.tags[0]._id, 'new-tag')
        # Ensure data is correct when GETting the resource again
        reload_res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(len(reload_res.json['data']['attributes']['tags']), 1)
        assert_equal(reload_res.json['data']['attributes']['tags'][0], 'new-tag')

    def test_non_authenticated_user_cannot_add_tag_to_public_project(self):
        res = self.app.patch_json(self.public_url, self.one_new_tag_json, expect_errors=True, auth=None)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_non_authenticated_user_cannot_add_tag_to_private_project(self):
        res = self.app.patch_json(self.private_url, self.one_new_tag_json, expect_errors=True, auth=None)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_non_contributor_cannot_add_tag_to_public_project(self):
        res = self.app.patch_json(self.public_url, self.one_new_tag_json, expect_errors=True, auth=self.user_two.auth)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_non_contributor_cannot_add_tag_to_private_project(self):
        res = self.app.patch_json(self.private_url, self.one_new_tag_json, expect_errors=True, auth=self.user_two.auth)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_read_only_contributor_cannot_add_tag_to_public_project(self):
        res = self.app.patch_json(self.public_url, self.one_new_tag_json, expect_errors=True, auth=self.read_only_contributor.auth)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_read_only_contributor_cannot_add_tag_to_private_project(self):
        res = self.app.patch_json(self.private_url, self.one_new_tag_json, expect_errors=True, auth=self.read_only_contributor.auth)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_tags_add_and_remove_properly(self):
        res = self.app.patch_json(self.private_url, self.one_new_tag_json, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        # Ensure adding tag data is correct from the PATCH response
        assert_equal(len(res.json['data']['attributes']['tags']), 1)
        assert_equal(res.json['data']['attributes']['tags'][0], 'new-tag')
        # Ensure removing and adding tag data is correct from the PATCH response
        res = self.app.patch_json(self.private_url, {'tags': ['newer-tag']}, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']['attributes']['tags']), 1)
        assert_equal(res.json['data']['attributes']['tags'][0], 'newer-tag')
        # Ensure removing tag data is correct from the PATCH response
        res = self.app.patch_json(self.private_url, {'tags': []}, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']['attributes']['tags']), 0)

class TestCreateNodePointer(ApiTestCase):
    def setUp(self):
        super(TestCreateNodePointer, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(is_public=False, creator=self.user)
        self.pointer_project = ProjectFactory(is_public=False, creator=self.user)
        self.private_url = '/{}nodes/{}/node_links/'.format(API_BASE, self.project._id)
        self.private_payload = {'target_node_id': self.pointer_project._id}
        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_pointer_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_url = '/{}nodes/{}/node_links/'.format(API_BASE, self.public_project._id)
        self.public_payload = {'target_node_id': self.public_pointer_project._id}
        self.fake_url = '/{}nodes/{}/node_links/'.format(API_BASE, 'fdxlq')
        self.fake_payload = {'target_node_id': 'fdxlq'}
        self.point_to_itself_payload = {'target_node_id': self.public_project._id}

        self.user_two = AuthUserFactory()
        self.user_two_project = ProjectFactory(is_public=True, creator=self.user_two)
        self.user_two_url = '/{}nodes/{}/node_links/'.format(API_BASE, self.user_two_project._id)
        self.user_two_payload = {'target_node_id': self.user_two_project._id}

    def test_creates_public_node_pointer_logged_out(self):
        res = self.app.post(self.public_url, self.public_payload, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]


    def test_creates_public_node_pointer_logged_in(self):
        res = self.app.post(self.public_url, self.public_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

        res = self.app.post(self.public_url, self.public_payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['target_node_id'], self.public_pointer_project._id)

    def test_creates_private_node_pointer_logged_out(self):
        res = self.app.post(self.private_url, self.private_payload, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]


    def test_creates_private_node_pointer_logged_in_contributor(self):
        res = self.app.post(self.private_url, self.private_payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['target_node_id'], self.pointer_project._id)
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_creates_private_node_pointer_logged_in_non_contributor(self):
        res = self.app.post(self.private_url, self.private_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

    def test_create_node_pointer_non_contributing_node_to_contributing_node(self):
        res = self.app.post(self.private_url, self.user_two_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

    def test_create_node_pointer_contributing_node_to_non_contributing_node(self):
        res = self.app.post(self.private_url, self.user_two_payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['target_node_id'], self.user_two_project._id)

    def test_create_pointer_non_contributing_node_to_fake_node(self):
        res = self.app.post(self.private_url, self.fake_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

    def test_create_pointer_contributing_node_to_fake_node(self):
        res = self.app.post(self.private_url, self.fake_payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert 'detail' in res.json['errors'][0]

    def test_create_fake_node_pointing_to_contributing_node(self):
        res = self.app.post(self.fake_url, self.private_payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert 'detail' in res.json['errors'][0]

        res = self.app.post(self.fake_url, self.private_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert 'detail' in res.json['errors'][0]

    def test_create_node_pointer_to_itself(self):
        res = self.app.post(self.public_url, self.point_to_itself_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

        res = self.app.post(self.public_url, self.point_to_itself_payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['target_node_id'], self.public_project._id)

    def test_create_node_pointer_already_connected(self):
        res = self.app.post(self.public_url, self.public_payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['target_node_id'], self.public_pointer_project._id)

        res = self.app.post(self.public_url, self.public_payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert 'detail' in res.json['errors'][0]


class TestNodeFilesList(ApiTestCase):

    def setUp(self):
        super(TestNodeFilesList, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.private_url = '/{}nodes/{}/files/'.format(API_BASE, self.project._id)

        self.user_two = AuthUserFactory()

        self.public_project = ProjectFactory(creator=self.user, is_public=True)
        self.public_url = '/{}nodes/{}/files/'.format(API_BASE, self.public_project._id)

    def test_returns_public_files_logged_out(self):
        res = self.app.get(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['attributes']['provider'], 'osfstorage')
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_returns_public_files_logged_in(self):
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data'][0]['attributes']['provider'], 'osfstorage')

    def test_returns_private_files_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]


    def test_returns_private_files_logged_in_contributor(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['attributes']['provider'], 'osfstorage')

    def test_returns_private_files_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]


    def test_returns_addon_folders(self):
        user_auth = Auth(self.user)
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['attributes']['provider'], 'osfstorage')

        self.project.add_addon('github', auth=user_auth)
        self.project.save()
        res = self.app.get(self.private_url, auth=self.user.auth)
        data = res.json['data']
        providers = [item['attributes']['provider'] for item in data]
        assert_equal(len(data), 2)
        assert_in('github', providers)
        assert_in('osfstorage', providers)

    @mock.patch('api.nodes.views.requests.get')
    def test_returns_node_files_list(self, mock_waterbutler_request):
        mock_res = mock.MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = {
            u'data': [{
                u'contentType': None,
                u'extra': {u'downloads': 0, u'version': 1},
                u'kind': u'file',
                u'modified': None,
                u'name': u'NewFile',
                u'path': u'/',
                u'provider': u'osfstorage',
                u'size': None
            }]
        }
        mock_waterbutler_request.return_value = mock_res

        url = '/{}nodes/{}/files/?path=%2F&provider=osfstorage'.format(API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data'][0]['attributes']['name'], 'NewFile')
        assert_equal(res.json['data'][0]['attributes']['provider'], 'osfstorage')

    @mock.patch('api.nodes.views.requests.get')
    def test_handles_unauthenticated_waterbutler_request(self, mock_waterbutler_request):
        url = '/{}nodes/{}/files/?path=%2F&provider=osfstorage'.format(API_BASE, self.project._id)
        mock_res = mock.MagicMock()
        mock_res.status_code = 401
        mock_waterbutler_request.return_value = mock_res
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]


    @mock.patch('api.nodes.views.requests.get')
    def test_handles_bad_waterbutler_request(self, mock_waterbutler_request):
        url = '/{}nodes/{}/files/?path=%2F&provider=osfstorage'.format(API_BASE, self.project._id)
        mock_res = mock.MagicMock()
        mock_res.status_code = 418
        mock_res.json.return_value = {}
        mock_waterbutler_request.return_value = mock_res
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert 'detail' in res.json['errors'][0]

    def test_files_list_does_not_contain_empty_relationships_object(self):
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert 'relationships' not in res.json['data'][0]


class TestNodePointerDetail(ApiTestCase):

    def setUp(self):
        super(TestNodePointerDetail, self).setUp()
        self.user = AuthUserFactory()
        self.private_project = ProjectFactory(creator=self.user, is_public=False)
        self.pointer_project = ProjectFactory(creator=self.user, is_public=False)
        self.pointer = self.private_project.add_pointer(self.pointer_project, auth=Auth(self.user), save=True)
        self.private_url = '/{}nodes/{}/node_links/{}/'.format(API_BASE, self.private_project._id, self.pointer._id)

        self.user_two = AuthUserFactory()

        self.public_project = ProjectFactory(is_public=True)
        self.public_pointer_project = ProjectFactory(is_public=True)
        self.public_pointer = self.public_project.add_pointer(self.public_pointer_project,
                                                              auth=Auth(self.user),
                                                              save=True)
        self.public_url = '/{}nodes/{}/node_links/{}/'.format(API_BASE, self.public_project._id, self.public_pointer._id)

    def test_returns_public_node_pointer_detail_logged_out(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        res_json = res.json['data']
        assert_equal(res_json['attributes']['target_node_id'], self.public_pointer_project._id)

    def test_returns_public_node_pointer_detail_logged_in(self):
        res = self.app.get(self.public_url, auth=self.user.auth)
        res_json = res.json['data']
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res_json['attributes']['target_node_id'], self.public_pointer_project._id)

    def test_returns_private_node_pointer_detail_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]


    def test_returns_private_node_pointer_detail_logged_in_contributor(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        res_json = res.json['data']
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res_json['attributes']['target_node_id'], self.pointer_project._id)

    def returns_private_node_pointer_detail_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]


class TestDeleteNodePointer(ApiTestCase):

    def setUp(self):
        super(TestDeleteNodePointer, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user, is_public=False)
        self.pointer_project = ProjectFactory(creator=self.user, is_public=True)
        self.pointer = self.project.add_pointer(self.pointer_project, auth=Auth(self.user), save=True)
        self.private_url = '/{}nodes/{}/node_links/{}'.format(API_BASE, self.project._id, self.pointer._id)

        self.user_two = AuthUserFactory()

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_pointer_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_pointer = self.public_project.add_pointer(self.public_pointer_project,
                                                              auth=Auth(self.user),
                                                              save=True)
        self.public_url = '/{}nodes/{}/node_links/{}'.format(API_BASE, self.public_project._id, self.public_pointer._id)

    def test_deletes_public_node_pointer_logged_out(self):
        res = self.app.delete(self.public_url, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]


    def test_deletes_public_node_pointer_fails_if_bad_auth(self):
        node_count_before = len(self.public_project.nodes_pointer)
        res = self.app.delete(self.public_url, auth=self.user_two.auth, expect_errors=True)
        self.public_project.reload()
        # This is could arguably be a 405, but we don't need to go crazy with status codes
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

        assert_equal(node_count_before, len(self.public_project.nodes_pointer))

    def test_deletes_public_node_pointer_succeeds_as_owner(self):
        node_count_before = len(self.public_project.nodes_pointer)
        res = self.app.delete(self.public_url, auth=self.user.auth)
        self.public_project.reload()
        assert_equal(res.status_code, 204)
        assert_equal(node_count_before - 1, len(self.public_project.nodes_pointer))

    def test_deletes_private_node_pointer_logged_out(self):
        res = self.app.delete(self.private_url, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]


    def test_deletes_private_node_pointer_logged_in_contributor(self):
        res = self.app.delete(self.private_url, auth=self.user.auth)
        self.project.reload()  # Update the model to reflect changes made by post request
        assert_equal(res.status_code, 204)
        assert_equal(len(self.project.nodes_pointer), 0)

    def test_deletes_private_node_pointer_logged_in_non_contributor(self):
        res = self.app.delete(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]


    def test_return_deleted_public_node_pointer(self):
        res = self.app.delete(self.public_url, auth=self.user.auth)
        self.public_project.reload() # Update the model to reflect changes made by post request
        assert_equal(res.status_code, 204)

        #check that deleted pointer can not be returned
        res = self.app.get(self.public_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_return_deleted_private_node_pointer(self):
        res = self.app.delete(self.private_url, auth=self.user.auth)
        self.project.reload()  # Update the model to reflect changes made by post request
        assert_equal(res.status_code, 204)

        #check that deleted pointer can not be returned
        res = self.app.get(self.private_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)


class TestReturnDeletedNode(ApiTestCase):
    def setUp(self):

        super(TestReturnDeletedNode, self).setUp()
        self.user = AuthUserFactory()
        self.non_contrib = AuthUserFactory()

        self.public_deleted = ProjectFactory(is_deleted=True, creator=self.user,
                                             title='This public project has been deleted', category='project',
                                             is_public=True)
        self.private_deleted = ProjectFactory(is_deleted=True, creator=self.user,
                                              title='This private project has been deleted', category='project',
                                              is_public=False)
        self.private = ProjectFactory(is_public=False, creator=self.user, title='A boring project', category='project')
        self.public = ProjectFactory(is_public=True, creator=self.user, title='A fun project', category='project')

        self.new_title = 'This deleted node has been edited'

        self.public_url = '/{}nodes/{}/'.format(API_BASE, self.public_deleted._id)
        self.private_url = '/{}nodes/{}/'.format(API_BASE, self.private_deleted._id)

    def test_return_deleted_public_node(self):
        res = self.app.get(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 410)

    def test_return_deleted_private_node(self):
        res = self.app.get(self.private_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 410)

    def test_edit_deleted_public_node(self):
        res = self.app.put(self.public_url, params={'title': self.new_title,
                                                    'node_id': self.public_deleted._id,
                                                    'category': self.public_deleted.category},
                           auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 410)

    def test_edit_deleted_private_node(self):
        res = self.app.put(self.private_url, params={'title': self.new_title,
                                                     'node_id': self.private_deleted._id,
                                                     'category': self.private_deleted.category},
                           auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 410)

    def test_delete_deleted_public_node(self):
        res = self.app.delete(self.public_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 410)

    def test_delete_deleted_private_node(self):
        res = self.app.delete(self.private_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 410)


class TestExceptionFormatting(ApiTestCase):
    def setUp(self):

        super(TestExceptionFormatting, self).setUp()
        self.user = AuthUserFactory()
        self.non_contrib = AuthUserFactory()

        self.title = 'Cool Project'
        self.description = 'A Properly Cool Project'
        self.category = 'data'

        self.project_no_title = {'description': self.description,
                                 'category': self.category,
                                 }

        self.private_project = ProjectFactory(is_public=False, creator=self.user)
        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.private_url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)

    def test_creates_project_with_no_title_formatting(self):
        url = '/{}nodes/'.format(API_BASE)
        res = self.app.post_json_api(url, self.project_no_title, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert('title' in res.json['errors'][0]['meta']['field'])
        assert('This field is required.' in res.json['errors'][0]['detail'])

    def test_node_does_not_exist_formatting(self):
        url = '/{}nodes/{}/'.format(API_BASE, '12345')
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert_equal(errors[0], {'detail': 'Not found.'})

    def test_forbidden_formatting(self):
        res = self.app.get(self.private_url, auth=self.non_contrib.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert_equal(errors[0], {'detail': 'You do not have permission to perform this action.'})

    def test_not_authorized_formatting(self):
        res = self.app.get(self.private_url, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert_equal(errors[0], {'detail': "Authentication credentials were not provided."})

    def test_update_project_with_no_title_or_category_formatting(self):
        res = self.app.put_json_api(self.private_url, {'description': 'New description'}, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert_equal(len(errors), 2)
        assert('category' in res.json['errors'][0]['meta']['field'])
        assert('This field is required.' in res.json['errors'][0]['detail'])
        assert('title' in res.json['errors'][1]['meta']['field'])
        assert('This field is required.' in res.json['errors'][0]['detail'])

    def test_create_node_link_no_target_formatting(self):
        url = self.private_url + 'node_links/'
        res = self.app.post_json_api(url, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert('target_node_id' in res.json['errors'][0]['meta']['field'])
        assert('This field is required.' in res.json['errors'][0]['detail'])


    def test_node_link_already_exists(self):
        url = self.private_url + 'node_links/'
        res = self.app.post_json_api(url, {'target_node_id': self.public_project._id}, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 201)
        res = self.app.post_json_api(url, {'target_node_id': self.public_project._id}, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert(self.public_project._id in res.json['errors'][0]['detail'])
