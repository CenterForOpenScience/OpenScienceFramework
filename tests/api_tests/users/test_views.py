# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from website.models import Node
from tests.base import ApiTestCase, fake
from api.base.settings.defaults import API_BASE
from tests.factories import UserFactory, ProjectFactory, FolderFactory, DashboardFactory


class TestUsers(ApiTestCase):

    def setUp(self):
        super(TestUsers, self).setUp()
        self.user_one = UserFactory.build()
        self.user_one.save()
        self.user_two = UserFactory.build()
        self.user_two.save()

    def tearDown(self):
        super(TestUsers, self).tearDown()

    def test_returns_200(self):
        res = self.app.get('/{}users/'.format(API_BASE))
        assert_equal(res.status_code, 200)

    def test_find_user_in_users(self):
        url = "/{}users/".format(API_BASE)

        res = self.app.get(url)
        user_son = res.json['data']

        ids = [each['id'] for each in user_son]
        assert_in(self.user_two._id, ids)

    def test_all_users_in_users(self):
        url = "/{}users/".format(API_BASE)

        res = self.app.get(url)
        user_son = res.json['data']

        ids = [each['id'] for each in user_son]
        assert_in(self.user_one._id, ids)
        assert_in(self.user_two._id, ids)

    def test_find_multiple_in_users(self):
        url = "/{}users/?filter[fullname]=fred".format(API_BASE)

        res = self.app.get(url)
        user_json = res.json['data']
        ids = [each['id'] for each in user_json]
        assert_in(self.user_one._id, ids)
        assert_in(self.user_two._id, ids)

    def test_find_single_user_in_users(self):
        url = "/{}users/?filter[fullname]=my".format(API_BASE)
        self.user_one.fullname = 'My Mom'
        self.user_one.save()
        res = self.app.get(url)
        user_json = res.json['data']
        ids = [each['id'] for each in user_json]
        assert_in(self.user_one._id, ids)
        assert_not_in(self.user_two._id, ids)

    def test_find_no_user_in_users(self):
        url = "/{}users/?filter[fullname]=NotMyMom".format(API_BASE)
        res = self.app.get(url)
        user_json = res.json['data']
        ids = [each['id'] for each in user_json]
        assert_not_in(self.user_one._id, ids)
        assert_not_in(self.user_two._id, ids)


class TestUserDetail(ApiTestCase):

    def setUp(self):
        super(TestUserDetail, self).setUp()
        self.user_one = UserFactory.build()
        self.user_one.set_password('justapoorboy')
        self.user_one.social['twitter'] = fake.first_name()
        self.user_one.save()
        self.auth_one = (self.user_one.username, 'justapoorboy')
        self.user_two = UserFactory.build()
        self.user_two.set_password('justapoorboy')
        self.user_two.save()
        self.auth_two = (self.user_two.username, 'justapoorboy')

    def tearDown(self):
        super(TestUserDetail, self).tearDown()

    def test_gets_200(self):
        url = "/{}users/{}/".format(API_BASE, self.user_one._id)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    def test_get_correct_pk_user(self):
        url = "/{}users/{}/".format(API_BASE, self.user_one._id)
        res = self.app.get(url)
        user_json = res.json['data']
        assert_equal(user_json['fullname'], self.user_one.fullname)
        assert_equal(
            user_json['social_accounts']['twitter'],
            self.user_one.social['twitter']
        )

    def test_get_incorrect_pk_user_logged_in(self):
        url = "/{}users/{}/".format(API_BASE, self.user_two._id)
        res = self.app.get(url)
        user_json = res.json['data']
        assert_not_equal(user_json['fullname'], self.user_one.fullname)

    def test_get_incorrect_pk_user_not_logged_in(self):
        url = "/{}users/{}/".format(API_BASE, self.user_two._id)
        res = self.app.get(url, auth=self.auth_one)
        user_json = res.json['data']
        assert_not_equal(user_json['fullname'], self.user_one.fullname)
        assert_equal(user_json['fullname'], self.user_two.fullname)


class TestUserNodes(ApiTestCase):

    def setUp(self):
        super(TestUserNodes, self).setUp()
        self.user_one = UserFactory.build()
        self.user_one.set_password('justapoorboy')
        self.user_one.social['twitter'] = fake.first_name()
        self.user_one.save()
        self.auth_one = (self.user_one.username, 'justapoorboy')
        self.user_two = UserFactory.build()
        self.user_two.set_password('justapoorboy')
        self.user_two.save()
        self.auth_two = (self.user_two.username, 'justapoorboy')
        self.public_project_user_one = ProjectFactory(title="Public Project User One",
                                                      is_public=True,
                                                      creator=self.user_one)
        self.private_project_user_one = ProjectFactory(title="Private Project User One",
                                                       is_public=False,
                                                       creator=self.user_one)
        self.public_project_user_two = ProjectFactory(title="Public Project User Two",
                                                      is_public=True,
                                                      creator=self.user_two)
        self.private_project_user_two = ProjectFactory(title="Private Project User Two",
                                                       is_public=False,
                                                       creator=self.user_two)
        self.deleted_project_user_one = FolderFactory(title="Deleted Project User One",
                                                      is_public=False,
                                                      creator=self.user_one,
                                                      is_deleted=True)
        self.folder = FolderFactory()
        self.deleted_folder = FolderFactory(title="Deleted Folder User One",
                                            is_public=False,
                                            creator=self.user_one,
                                            is_deleted=True)
        self.dashboard = DashboardFactory()

    def tearDown(self):
        super(TestUserNodes, self).tearDown()

    def test_authorized_in_gets_200(self):
        url = "/{}users/{}/nodes/".format(API_BASE, self.user_one._id)
        res = self.app.get(url, auth=self.auth_one)
        assert_equal(res.status_code, 200)

    def test_anonymous_gets_200(self):
        url = "/{}users/{}/nodes/".format(API_BASE, self.user_one._id)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    def test_get_projects_logged_in(self):
        url = "/{}users/{}/nodes/".format(API_BASE, self.user_one._id)
        res = self.app.get(url, auth=self.auth_one)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.public_project_user_one._id, ids)
        assert_in(self.private_project_user_one._id, ids)
        assert_not_in(self.public_project_user_two._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.deleted_folder._id, ids)
        assert_not_in(self.deleted_project_user_one._id, ids)

    def test_get_projects_not_logged_in(self):
        url = "/{}users/{}/nodes/".format(API_BASE, self.user_one._id)
        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.public_project_user_one._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.public_project_user_two._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.deleted_project_user_one._id, ids)

    def test_get_projects_logged_in_as_different_user(self):
        url = "/{}users/{}/nodes/".format(API_BASE, self.user_two._id)
        res = self.app.get(url, auth=self.auth_one)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.public_project_user_two._id, ids)
        assert_not_in(self.public_project_user_one._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.deleted_project_user_one._id, ids)


class TestUserRoutesNodeRoutes(ApiTestCase):

    def setUp(self):
        super(TestUserRoutesNodeRoutes, self).setUp()
        self.user_one = UserFactory.build()
        self.user_one.set_password('justapoorboy')
        self.user_one.social['twitter'] = 'howtopizza'
        self.user_one.save()
        self.auth_one = (self.user_one.username, 'justapoorboy')

        self.user_two = UserFactory.build()
        self.user_two.set_password('justapoorboy')
        self.user_two.save()
        self.auth_two = (self.user_two.username, 'justapoorboy')

        self.public_project_user_one = ProjectFactory(title="Public Project User One", is_public=True, creator=self.user_one)
        self.private_project_user_one = ProjectFactory(title="Private Project User One", is_public=False, creator=self.user_one)
        self.public_project_user_two = ProjectFactory(title="Public Project User Two", is_public=True, creator=self.user_two)
        self.private_project_user_two = ProjectFactory(title="Private Project User Two", is_public=False, creator=self.user_two)
        self.deleted_project_user_one = FolderFactory(title="Deleted Project User One", is_public=False, creator=self.user_one, is_deleted=True)

        self.folder = FolderFactory()
        self.deleted_folder = FolderFactory(title="Deleted Folder User One", is_public=False, creator=self.user_one, is_deleted=True)
        self.dashboard = DashboardFactory()

    def tearDown(self):
        super(TestUserRoutesNodeRoutes, self).tearDown()
        Node.remove()

    def test_get_200_path_users_me_userone_logged_in(self):
        url = "/{}users/me/".format(API_BASE)
        res = self.app.get(url, auth=self.auth_one)
        assert_equal(res.status_code, 200)

    def test_get_200_path_users_me_usertwo_logged_in(self):
        url = "/{}users/me/".format(API_BASE)
        res = self.app.get(url, auth=self.auth_two)
        assert_equal(res.status_code, 200)

    def test_get_403_path_users_me_no_user(self):
        # TODO: change expected exception from 403 to 401 for unauthorized users

        url = "/{}users/me/".format(API_BASE)
        res = self.app.get(url, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_get_404_path_users_user_id_me_user_logged_in(self):
        url = "/{}users/{}/me/".format(API_BASE, self.user_one._id)
        res = self.app.get(url, auth=self.auth_one, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_get_404_path_users_user_id_me_no_user(self):
        url = "/{}users/{}/me/".format(API_BASE, self.user_one._id)
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_get_404_path_users_user_id_me_unauthorized_user(self):
        url = "/{}users/{}/me/".format(API_BASE, self.user_one._id)
        res = self.app.get(url, auth= self.auth_two, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_get_200_path_users_user_id_user_logged_in(self):
        url = "/{}users/{}/".format(API_BASE, self.user_one._id)
        res = self.app.get(url, auth=self.auth_one)
        assert_equal(res.status_code, 200)

    def test_get_200_path_users_user_id_no_user(self):
        url = "/{}users/{}/".format(API_BASE, self.user_two._id)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    def test_get_200_path_users_user_id_unauthorized_user(self):
        url = "/{}users/{}/".format(API_BASE, self.user_two._id)
        res = self.app.get(url, auth=self.auth_one)
        assert_equal(res.status_code, 200)

        ids = {each['id'] for each in res.json['data']}
        assert_in(self.public_project_user_one._id, ids)
        assert_in(self.private_project_user_one._id, ids)
        assert_not_in(self.public_project_user_two._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.deleted_folder._id, ids)
        assert_not_in(self.deleted_project_user_one._id, ids)

    def test_get_200_path_users_me_nodes_user_logged_in(self):
        url = "/{}users/me/nodes/".format(API_BASE, self.user_one._id)
        res = self.app.get(url, auth=self.auth_one)
        assert_equal(res.status_code, 200)

        ids = {each['id'] for each in res.json['data']}
        assert_in(self.public_project_user_one._id, ids)
        assert_in(self.private_project_user_one._id, ids)
        assert_not_in(self.public_project_user_two._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.deleted_folder._id, ids)
        assert_not_in(self.deleted_project_user_one._id, ids)

    def test_get_403_path_users_me_nodes_no_user(self):
        # TODO: change expected exception from 403 to 401 for unauthorized users

        url = "/{}users/me/nodes/".format(API_BASE)
        res = self.app.get(url, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_get_200_path_users_user_id_nodes_user_logged_in(self):
        url = "/{}users/{}/nodes/".format(API_BASE, self.user_one._id)
        res = self.app.get(url, auth= self.auth_one)
        assert_equal(res.status_code, 200)

        ids = {each['id'] for each in res.json['data']}
        assert_in(self.public_project_user_one._id, ids)
        assert_in(self.private_project_user_one._id, ids)
        assert_not_in(self.public_project_user_two._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.deleted_folder._id, ids)
        assert_not_in(self.deleted_project_user_one._id, ids)

    def test_get_200_path_users_user_id_nodes_no_user(self):
        url = "/{}users/{}/nodes/".format(API_BASE, self.user_one._id)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

        # an anonymous/unauthorized user can only see the public projects user_one contributes to.
        ids = {each['id'] for each in res.json['data']}
        assert_in(self.public_project_user_one._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.public_project_user_two._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.deleted_folder._id, ids)
        assert_not_in(self.deleted_project_user_one._id, ids)

    def test_get_200_path_users_user_id_unauthorized_user(self):
        url = "/{}users/{}/nodes/".format(API_BASE, self.user_one._id)
        res = self.app.get(url, auth=self.auth_two)
        assert_equal(res.status_code, 200)

        # an anonymous/unauthorized user can only see the public projects user_one contributes to.
        ids = {each['id'] for each in res.json['data']}
        assert_in(self.public_project_user_one._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.public_project_user_two._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.deleted_folder._id, ids)
        assert_not_in(self.deleted_project_user_one._id, ids)

    def test_get_404_path_users_user_id_nodes_me_user_logged_in(self):
        url = "/{}users/{}/nodes/me/".format(API_BASE, self.user_one._id)
        res = self.app.get(url, auth=self.auth_one, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_get_404_path_users_user_id_nodes_me_unauthorized_user(self):
        url = "/{}users/{}/nodes/me/".format(API_BASE, self.user_one._id)
        res = self.app.get(url, auth=self.auth_two, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_get_404_path_users_user_id_nodes_me_no_user(self):
        url = "/{}users/{}/nodes/me/".format(API_BASE, self.user_one._id)
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_get_404_path_nodes_me_user_logged_in(self):
        url = "/{}nodes/me/".format(API_BASE)
        res = self.app.get(url, auth=self.auth_one, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_get_404_path_nodes_me_no_user(self):
        url = "/{}nodes/me/".format(API_BASE)
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_get_404_path_nodes_user_id_user_logged_in(self):
        url = "/{}nodes/{}/".format(API_BASE, self.user_one._id)
        res = self.app.get(url, auth=self.auth_one, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_get_404_path_nodes_user_id_unauthorized_user(self):
        url = "/{}nodes/{}/".format(API_BASE, self.user_one._id)
        res = self.app.get(url, auth=self.auth_two, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_get_404_path_nodes_user_id_no_user(self):
        url = "/{}nodes/{}/".format(API_BASE, self.user_one._id)
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 404)
