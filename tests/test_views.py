#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Views tests for the OSF.'''
from __future__ import absolute_import
import json
import unittest
import datetime as dt
import mock

import mock
from nose.tools import *  # PEP8 asserts
from webtest_plus import TestApp
from framework import Q
from framework.auth.model import User

import website.app
from website.models import Node, Pointer, NodeLog
from website.project.model import ensure_schemas
from framework.auth.decorators import Auth
from website.project.views.contributor import _add_contributor_json
from webtest.app import AppError
from website import settings
from website.util import rubeus
from website.project.views.node import _view_project


from tests.base import DbTestCase
from tests.factories import (
    UserFactory, ApiKeyFactory, ProjectFactory, WatchConfigFactory,
    NodeFactory, NodeLogFactory, AuthUserFactory, UnregUserFactory,
    RegistrationFactory
)


app = website.app.init_app(
    routes=True, set_backends=False, settings_module='website.settings',
)


class TestProjectViews(DbTestCase):

    def setUp(self):
        ensure_schemas()
        self.app = TestApp(app)
        self.user1 = UserFactory.build()
        # Add an API key for quicker authentication
        api_key = ApiKeyFactory()
        self.user1.api_keys.append(api_key)
        self.user1.save()
        self.consolidate_auth1 = Auth(user=self.user1, api_key=api_key)
        self.auth = ('test', api_key._primary_key)
        self.user2 = UserFactory()
        # A project has 2 contributors
        self.project = ProjectFactory(
            title="Ham",
            description='Honey-baked',
            creator=self.user1
        )
        self.project.add_contributor(self.user1)
        self.project.add_contributor(self.user2)
        self.project.api_keys.append(api_key)
        self.project.save()

    def test_edit_description(self):
        url = "/api/v1/project/{0}/edit/".format(self.project._id)
        self.app.post_json(url,
                            {"name": "description", "value": "Deep-fried"},
                            auth=self.auth)
        self.project.reload()
        assert_equal(self.project.description, "Deep-fried")

    def test_project_api_url(self):
        url = self.project.api_url
        res = self.app.get(url, auth=self.auth)
        data = res.json
        assert_equal(data['node']['category'], 'project')
        assert_equal(data['node']['title'], self.project.title)
        assert_equal(data['node']['is_public'], self.project.is_public)
        assert_equal(data['node']['is_registration'], False)
        assert_equal(data['node']['id'], self.project._primary_key)
        assert_equal(data['node']['watched_count'], 0)
        assert_true(data['user']['is_contributor'])
        assert_equal(data['node']['logs'][-1]['action'], 'project_created')
        assert_equal(data['node']['children_ids'],
                        [str(n._primary_key) for n in self.project.nodes])
        assert_equal(data['node']['description'], self.project.description)
        assert_equal(data['node']['url'], self.project.url)
        assert_equal(data['node']['tags'], [t._primary_key for t in self.project.tags])
        assert_in('forked_date', data['node'])
        assert_in('watched_count', data['node'])
        assert_in('registered_from_url', data['node'])
        # TODO: Test "parent" and "user" output

    def test_add_contributor_post(self):
        # Two users are added as a contributor via a POST request
        project = ProjectFactory(creator=self.user1, is_public=True)
        user2 = UserFactory()
        user3 = UserFactory()
        url = "/api/v1/project/{0}/addcontributors/".format(project._id)
        res = self.app.post(url, json.dumps({"user_ids": [user2._id, user3._id]}),
                            content_type="application/json",
                            auth=self.auth).maybe_follow()
        project.reload()
        assert_in(user2._id, project.contributors)
        # A log event was added
        assert_equal(project.logs[-1].action, "contributor_added")
        assert_equal(len(project.contributors), 3)
        assert_equal(len(project.contributor_list), 3)

    @unittest.skip('Adding non-registered contributors is on hold until '
                   'invitations and account merging are done.')
    def test_add_non_registered_contributor(self):
        url = "/api/v1/project/{0}/addcontributor/".format(self.project._id)
        # A non-registered user is added
        res = self.app.post(url, json.dumps({"email": "joe@example.com", "fullname": "Joe Dirt"}),
                            content_type="application/json",
                            auth=self.auth).maybe_follow()
        self.project.reload()
        # The contributor list should have length 3 (2 registered, 1 unregistered)
        assert_equal(len(self.project.contributor_list), 3)
        # A log event was added
        assert_equal(self.project.logs[-1].action, "contributor_added")

    def test_project_remove_contributor(self):
        url = "/api/v1/project/{0}/removecontributors/".format(self.project._id)
        # User 1 removes user2
        res = self.app.post(url, json.dumps({"id": self.user2._id}),
                            content_type="application/json",
                            auth=self.auth).maybe_follow()
        self.project.reload()
        assert_not_in(self.user2._id, self.project.contributors)
        # A log event was added
        assert_equal(self.project.logs[-1].action, "contributor_removed")

    @unittest.skip('Removing non-registered contributors is on hold until '
                   'invitations and account merging are done.')
    def test_project_remove_non_registered_contributor(self):
        # A non-registered user is added to the project
        self.project.add_nonregistered_contributor(
            name="Vanilla Ice",
            email="iceice@baby.ice",
            auth=self.consolidate_auth1
        )
        self.project.save()
        url = "/api/v1/project/{0}/removecontributors/".format(self.project._id)
        # the contributor is removed via the API
        assert False, 'finish me'


    def test_edit_node_title(self):
        url = "/api/v1/project/{0}/edit/".format(self.project._id)
        # The title is changed though posting form data
        res = self.app.post_json(url, {"name": "title", "value": "Bacon"},
                            auth=self.auth).maybe_follow()
        self.project.reload()
        # The title was changed
        assert_equal(self.project.title, "Bacon")
        # A log event was saved
        assert_equal(self.project.logs[-1].action, "edit_title")

    def test_make_public(self):
        self.project.is_public = False
        self.project.save()
        url = "/api/v1/project/{0}/permissions/public/".format(self.project._id)
        res = self.app.post_json(url, {}, auth=self.auth)
        self.project.reload()
        assert_true(self.project.is_public)
        assert_equal(res.json['status'], 'success')

    def test_make_private(self):
        self.project.is_public = True
        self.project.save()
        url = "/api/v1/project/{0}/permissions/private/".format(self.project._id)
        res = self.app.post_json(url, {}, auth=self.auth)
        self.project.reload()
        assert_false(self.project.is_public)
        assert_equal(res.json['status'], 'success')

    def test_add_tag(self):
        url = "/api/v1/project/{0}/addtag/{tag}/".format(self.project._primary_key,
                                                        tag="footag")
        res = self.app.post_json(url, {}, auth=self.auth)
        self.project.reload()
        assert_in("footag", self.project.tags)

    def test_remove_tag(self):
        self.project.add_tag("footag", auth=self.consolidate_auth1, save=True)
        assert_in("footag", self.project.tags)
        url = "/api/v1/project/{0}/removetag/{tag}/".format(self.project._primary_key,
                                                        tag="footag")
        res = self.app.post_json(url, {}, auth=self.auth)
        self.project.reload()
        assert_not_in("footag", self.project.tags)

    def test_register_template_page(self):
        url = "/api/v1/project/{0}/register/Replication_Recipe_(Brandt_et_al.,_2013):_Post-Completion/".format(self.project._primary_key)
        res = self.app.post_json(url, {}, auth=self.auth)
        self.project.reload()
        # A registration was added to the project's registration list
        assert_equal(len(self.project.registration_list), 1)
        # A log event was saved
        assert_equal(self.project.logs[-1].action, "project_registered")
        # Most recent node is a registration
        reg = Node.load(self.project.registration_list[-1])
        assert_true(reg.is_registration)

    def test_get_logs(self):
        # Add some logs
        for _ in range(5):
            self.project.logs.append(
                NodeLogFactory(
                    user=self.user1,
                    action='file_added',
                    params={'project': self.project._id}
                )
            )
        self.project.save()
        url = '/api/v1/project/{0}/log/'.format(self.project._primary_key)
        res = self.app.get(url, auth=self.auth)
        self.project.reload()
        data = res.json
        assert_equal(len(data['logs']), len(self.project.logs))
        most_recent = data['logs'][0]
        assert_equal(most_recent['action'], 'file_added')

    def test_get_logs_with_count_param(self):
        # Add some logs
        for _ in range(5):
            self.project.logs.append(
                NodeLogFactory(
                    user=self.user1,
                    action='file_added',
                    params={'project': self.project._id}
                )
            )
        self.project.save()
        url = '/api/v1/project/{0}/log/'.format(self.project._primary_key)
        res = self.app.get(url, {'count': 3}, auth=self.auth)
        assert_equal(len(res.json['logs']), 3)

    def test_get_logs_defaults_to_ten(self):
        # Add some logs
        for _ in range(12):
            self.project.logs.append(
                NodeLogFactory(
                    user=self.user1,
                    action='file_added',
                    params={'project': self.project._id}
                )
            )
        self.project.save()
        url = '/api/v1/project/{0}/log/'.format(self.project._primary_key)
        res = self.app.get(url, auth=self.auth)
        assert_equal(len(res.json['logs']), 10)

    def test_logs_private(self):
        """Add logs to a public project, then to its private component. Get
        the ten most recent logs; assert that ten logs are returned and that
        all belong to the project and not its component.

        """
        # Add some logs
        for _ in range(15):
            self.project.add_log(
                auth=self.consolidate_auth1,
                action='file_added',
                params={'project': self.project._id}
            )
        self.project.is_public = True
        self.project.save()
        child = NodeFactory(project=self.project)
        for _ in range(5):
            child.add_log(
                auth=self.consolidate_auth1,
                action='file_added',
                params={'project': child._id}
            )
        url = '/api/v1/project/{0}/log/'.format(self.project._primary_key)
        res = self.app.get(url).maybe_follow()
        assert_equal(len(res.json['logs']), 10)
        assert_equal(
            [self.project._id] * 10,
            [
                log['params']['project']
                for log in res.json['logs']
            ]
        )

    def test_logs_from_api_url(self):
        # Add some logs
        for _ in range(12):
            self.project.logs.append(
                NodeLogFactory(
                    user=self.user1,
                    action="file_added",
                    params={"project": self.project._id}
                )
            )
        self.project.save()
        url = "/api/v1/project/{0}/".format(self.project._primary_key)
        res = self.app.get(url, auth=self.auth)
        assert_equal(len(res.json['node']['logs']), 10)

    def test_remove_project(self):
        url = self.project.api_url + 'remove/'
        res = self.app.delete_json(url, {}, auth=self.auth).maybe_follow()
        self.project.reload()
        assert_equal(self.project.is_deleted, True)
        assert_in('url', res.json)
        assert_equal(res.json['url'], '/dashboard/')

    def test_remove_project_with_component(self):
        node = NodeFactory(project=self.project, creator=self.user1)
        url = self.project.api_url + 'remove/'
        self.app.delete_json(url, {}, auth=self.auth).maybe_follow()
        node.reload()
        assert_equal(node.is_deleted, True)

    def test_remove_component(self):
        node = NodeFactory(project=self.project, creator=self.user1)
        url = node.api_url + 'remove/'
        res = self.app.delete_json(url, {}, auth=self.auth).maybe_follow()
        node.reload()
        assert_equal(node.is_deleted, True)
        assert_in('url', res.json)
        assert_equal(res.json['url'], self.project.url)

@unittest.skipIf(not settings.ALLOW_CLAIMING, 'skipping until claiming is fully implemented')
class TestUserInviteViews(DbTestCase):

    def setUp(self):
        ensure_schemas()
        self.app = TestApp(app)
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.invite_url = '/api/v1/project/{0}/invite_contributor/'.format(self.project._primary_key)

    @mock.patch('website.project.views.contributor.send_email.delay')
    def test_invite_contributor_api_endpoint_sends_an_email(self, send_email_delay):
        self.app.post_json(self.invite_url,
            {'fullname': 'Brian May', 'email': 'brian@queen.com'}, auth=self.user.auth)
        assert_true(send_email_delay.called)

    @mock.patch('website.project.views.contributor.send_email')
    def test_invite_contributor_api_endpoint_adds_a_non_registered_contributor(self, send_email):
        res = self.app.post_json(self.invite_url,
            {'fullname': 'Brian May', 'email': 'brian@queen.com'}, auth=self.user.auth)

        latest_user = User.find_one(Q('username', 'eq', 'brian@queen.com'))
        assert_equal(latest_user.fullname, 'Brian May')
        assert_equal(latest_user.username, 'brian@queen.com')
        assert_false(latest_user.is_registered)
        assert_equal(res.json['contributor'], _add_contributor_json(latest_user))

    def test_invite_contributor_adds_unclaimed_data(self):
        res = self.app.post_json(self.invite_url,
            {'fullname': 'Briann May', 'email': 'brian2@queen.com'}, auth=self.user.auth)
        latest_user = User.find()[len(User.find()) - 1]
        data = latest_user.unclaimed_records[self.project._primary_key]
        assert_equal(data['name'], 'Briann May')
        assert_equal(data['referrer_id'], self.user._primary_key)
        assert_true(data['verification'])

    @mock.patch('website.project.views.contributor.send_email')
    def test_invite_contributor_with_no_email(self, send_email):
        assert 0, 'finish me'

    def test_invite_contributor_requires_fullname(self):
        res = self.app.post_json(self.invite_url,
            {'email': 'brian@queen.com', 'fullname': ''}, auth=self.user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 400)

    @mock.patch('website.project.views.contributor.send_email')
    def test_cannot_invite_unreg_contributor_if_they_already_exist(self, send_email):
        user = UserFactory()
        res = self.app.post_json(self.invite_url,
            {'fullname': 'Fred Mercury', 'email': user.username}, auth=self.user.auth)
        assert_in('User already exists', res.json['message'])
        assert_in('contributor', res.json)

@unittest.skipIf(not settings.ALLOW_CLAIMING, 'skipping until claiming is fully implemented')
class TestClaimViews(DbTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.referrer = UserFactory()
        self.user = UnregUserFactory()
        self.project = ProjectFactory(creator=self.referrer)

    def add_unclaimed_record(self):
        given_name = 'Fredd Merkury'
        self.user.add_unclaimed_record(node=self.project,
            given_name=given_name, referrer=self.referrer)
        self.user.save()
        data = self.user.unclaimed_records[self.project._primary_key]
        return data

    def test_valid_claim_url(self):
        self.add_unclaimed_record()
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.get(url).maybe_follow()
        assert_equal(res.status_code, 200)

    def test_invalid_claim_url_responds_with_404(self):
        res = self.app.get('/claim/badsignature/', expect_errors=True).maybe_follow()
        assert_equal(res.status_code, 404)

    def test_posting_to_claim_url_with_valid_data(self):
        url = self.user.get_claim_url(self.project._primary_key)
        # res = self.app.post(url, )
        assert 0, 'finish me'


class TestWatchViews(DbTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = UserFactory.build(username='tesla@electric.com')
        api_key = ApiKeyFactory()
        self.user.api_keys.append(api_key)
        self.user.save()
        self.consolidate_auth = Auth(user=self.user, api_key=api_key)
        self.auth = ('test', self.user.api_keys[0]._id)  # used for requests auth
        # A public project
        self.project = ProjectFactory(is_public=True)
        self.project.save()
        # Manually reset log date to 100 days ago so it won't show up in feed
        self.project.logs[0].date = dt.datetime.utcnow() - dt.timedelta(days=100)
        self.project.logs[0].save()
        # A log added now
        self.last_log = self.project.add_log(
            NodeLog.TAG_ADDED, params={'project': self.project._primary_key},
            auth=self.consolidate_auth, log_date=dt.datetime.utcnow(),
            save=True,
        )
        # Clear watched list
        self.user.watched = []
        self.user.save()

    def test_watching_a_project_appends_to_users_watched_list(self):
        n_watched_then = len(self.user.watched)
        url = '/api/v1/project/{0}/watch/'.format(self.project._id)
        res = self.app.post_json(url,
                                 params={"digest": True},
                                 auth=self.auth)
        assert_equal(res.json['watchCount'], 1)
        self.user.reload()
        n_watched_now = len(self.user.watched)
        assert_equal(res.status_code, 200)
        assert_equal(n_watched_now, n_watched_then + 1)
        assert_true(self.user.watched[-1].digest)

    def test_watching_project_twice_returns_400(self):
        url = "/api/v1/project/{0}/watch/".format(self.project._id)
        res = self.app.post_json(url,
                            params={},
                            auth=self.auth)
        assert_equal(res.status_code, 200)
        # User tries to watch a node she's already watching
        res2 = self.app.post_json(url,
                            params={},
                            auth=self.auth,
                            expect_errors=True)
        assert_equal(res2.status_code, 400)

    def test_unwatching_a_project_removes_from_watched_list(self):
        # The user has already watched a project
        watch_config = WatchConfigFactory(node=self.project)
        self.user.watch(watch_config)
        self.user.save()
        n_watched_then = len(self.user.watched)
        url = '/api/v1/project/{0}/unwatch/'.format(self.project._id)
        res = self.app.post_json(url, {}, auth=self.auth)
        self.user.reload()
        n_watched_now = len(self.user.watched)
        assert_equal(res.status_code, 200)
        assert_equal(n_watched_now, n_watched_then - 1)
        assert_false(self.user.is_watching(self.project))

    def test_toggle_watch(self):
        # The user is not watching project
        assert_false(self.user.is_watching(self.project))
        url = "/api/v1/project/{0}/togglewatch/".format(self.project._id)
        res = self.app.post_json(url, {}, auth=self.auth)
        # The response json has a watchcount and watched property
        assert_equal(res.json['watchCount'], 1)
        assert_true(res.json['watched'])
        assert_equal(res.status_code, 200)
        self.user.reload()
        # The user is now watching the project
        assert_true(res.json['watched'])
        assert_true(self.user.is_watching(self.project))

    def test_toggle_watch_node(self):
        # The project has a public sub-node
        node = NodeFactory(creator=self.user, project=self.project, is_public=True)
        url = "/api/v1/project/{}/node/{}/togglewatch/".format(self.project._id,
                                                                node._id)
        res = self.app.post_json(url, {}, auth=self.auth)
        assert_equal(res.status_code, 200)
        self.user.reload()
        # The user is now watching the sub-node
        assert_true(res.json['watched'])
        assert_true(self.user.is_watching(node))

    def test_get_watched_logs(self):
        project = ProjectFactory()
        # Add some logs
        for _ in range(12):
            project.logs.append(NodeLogFactory(user=self.user, action="file_added"))
        project.save()
        watch_cfg = WatchConfigFactory(node=project)
        self.user.watch(watch_cfg)
        self.user.save()
        url = "/api/v1/watched/logs/"
        res = self.app.get(url, auth=self.auth)
        assert_equal(len(res.json['logs']), len(project.logs))
        assert_equal(res.json['logs'][0]['action'], 'file_added')


class TestPointerViews(DbTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = AuthUserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user)

    def test_add_pointers(self):

        url = self.project.api_url + 'pointer/'
        node_ids = [
            NodeFactory()._id
            for _ in range(5)
        ]
        self.app.post_json(
            url,
            {'nodeIds': node_ids},
            auth=self.user.auth,
        ).maybe_follow()

        self.project.reload()
        assert_equal(
            len(self.project.nodes),
            5
        )

    def test_add_pointers_not_provided(self):
        url = self.project.api_url + 'pointer/'
        with assert_raises(AppError):
            self.app.post_json(url, {}, auth=self.user.auth)

    def test_remove_pointer(self):
        url = self.project.api_url + 'pointer/'
        node = NodeFactory()
        pointer = self.project.add_pointer(node, auth=self.consolidate_auth)
        self.app.delete_json(
            url,
            {'pointerId': pointer._id},
            auth=self.user.auth,
        )
        self.project.reload()
        assert_equal(
            len(self.project.nodes),
            0
        )

    def test_remove_pointer_not_provided(self):
        url = self.project.api_url + 'pointer/'
        with assert_raises(AppError):
            self.app.delete_json(url, {}, auth=self.user.auth)

    def test_remove_pointer_not_found(self):
        url = self.project.api_url + 'pointer/'
        with assert_raises(AppError):
            self.app.delete_json(
                url,
                {'pointerId': None},
                auth=self.user.auth
            )

    def test_remove_pointer_not_in_nodes(self):
        url = self.project.api_url + 'pointer/'
        node = NodeFactory()
        pointer = Pointer(node=node)
        with assert_raises(AppError):
            self.app.delete_json(
                url,
                {'pointerId': pointer._id},
                auth=self.user.auth,
            )

    def test_fork_pointer(self):
        url = self.project.api_url + 'pointer/fork/'
        node = NodeFactory(creator=self.user)
        pointer = self.project.add_pointer(node, auth=self.consolidate_auth)
        self.app.post_json(
            url,
            {'pointerId': pointer._id},
            auth=self.user.auth
        )

    def test_fork_pointer_not_provided(self):
        url = self.project.api_url + 'pointer/fork/'
        with assert_raises(AppError):
            self.app.post_json(url, {}, auth=self.user.auth)

    def test_fork_pointer_not_found(self):
        url = self.project.api_url + 'pointer/fork/'
        with assert_raises(AppError):
            self.app.post_json(
                url,
                {'pointerId': None},
                auth=self.user.auth
            )

    def test_fork_pointer_not_in_nodes(self):
        url = self.project.api_url + 'pointer/fork/'
        node = NodeFactory()
        pointer = Pointer(node=node)
        with assert_raises(AppError):
            self.app.post_json(
                url,
                {'pointerId': pointer._id},
                auth=self.user.auth
            )

    def test_before_register_with_pointer(self):
        "Assert that link warning appears in before register callback."
        node = NodeFactory()
        self.project.add_pointer(node, auth=self.consolidate_auth)
        url = self.project.api_url + 'fork/before/'
        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        prompts = [
            prompt
            for prompt in res.json['prompts']
            if 'Links will be copied into your fork' in prompt
        ]
        assert_equal(len(prompts), 1)

    def test_before_fork_with_pointer(self):
        "Assert that link warning appears in before fork callback."
        node = NodeFactory()
        self.project.add_pointer(node, auth=self.consolidate_auth)
        url = self.project.api_url + 'beforeregister/'
        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        prompts = [
            prompt
            for prompt in res.json['prompts']
            if 'Links will be copied into your registration' in prompt
        ]
        assert_equal(len(prompts), 1)

    def test_before_register_no_pointer(self):
        "Assert that link warning does not appear in before register callback."
        url = self.project.api_url + 'fork/before/'
        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        prompts = [
            prompt
            for prompt in res.json['prompts']
            if 'Links will be copied into your fork' in prompt
        ]
        assert_equal(len(prompts), 0)

    def test_before_fork_no_pointer(self):
        "Assert that link warning does not appear in before fork callback."
        url = self.project.api_url + 'beforeregister/'
        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        prompts = [
            prompt
            for prompt in res.json['prompts']
            if 'Links will be copied into your registration' in prompt
        ]
        assert_equal(len(prompts), 0)


class TestPublicViews(DbTestCase):

    def setUp(self):
        self.app = TestApp(app)

    def test_explore(self):
        res = self.app.get("/explore/").maybe_follow()
        assert_equal(res.status_code, 200)


class TestAuthViews(DbTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = UserFactory.build()
        # Add an API key for quicker authentication
        api_key = ApiKeyFactory()
        self.user.api_keys.append(api_key)
        self.user.save()
        self.auth = ('test', api_key._primary_key)

    def test_merge_user(self):
        dupe = UserFactory(username="copy@cat.com",
                            emails=['copy@cat.com'])
        dupe.set_password("copycat")
        dupe.save()
        url = "/api/v1/user/merge/"
        res = self.app.post_json(url, {"merged_username": "copy@cat.com",
                                        "merged_password": "copycat"}, auth=self.auth)
        self.user.reload()
        dupe.reload()
        assert_true(dupe.is_merged)

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_register_sends_confirm_email(self, send_mail):
        url = '/register/'
        self.app.post(url, {
            'register-fullname': 'Freddie Mercury',
            'register-username': 'fred@queen.com',
            'register-password': 'killerqueen',
            'register-username2': 'fred@queen.com',
            'register-password2': 'killerqueen',
        })
        assert_true(send_mail.called)
        assert_true(send_mail.called_with(
            to_addr='fred@queen.com'
        ))

    def test_resend_confirmation_get(self):
        res = self.app.get('/resend/')
        assert_equal(res.status_code, 200)

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_resend_confirmation_post_sends_confirm_email(self, send_mail):
        # Make sure user has a confirmation token for their primary email
        self.user.add_email_verification(self.user.username)
        self.user.save()
        res = self.app.post('/resend/', {'email': self.user.username})
        assert_true(send_mail.called)
        assert_true(send_mail.called_with(
            to_addr=self.user.username
        ))

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_resend_confirmation_post_if_user_not_in_database(self, send_mail):
        res = self.app.post('/resend/', {'email': 'norecord@norecord.no'})
        assert_false(send_mail.called)

    def test_confirmation_link_registers_user(self):
        user = User.create_unconfirmed('brian@queen.com', 'bicycle123', 'Brian May')
        assert_false(user.is_registered)  # sanity check
        user.save()
        confirmation_url = user.get_confirmation_url('brian@queen.com', external=False)
        res = self.app.get(confirmation_url)
        assert_equal(res.status_code, 302, 'redirects to settings page')
        res = res.follow()
        user.reload()
        assert_true(user.is_registered)

    def test_expired_link_returns_400(self):
        user = User.create_unconfirmed('brian1@queen.com', 'bicycle123', 'Brian May')
        user.save()
        token = user.get_confirmation_token('brian1@queen.com')
        url = user.get_confirmation_url('brian1@queen.com', external=False)
        user.confirm_email(token)
        user.save()
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_change_names(self):
        self.app.post(
            '/api/v1/settings/names/',
            json.dumps({
                'fullname': 'Lyndon Baines Johnson',
                'given_name': 'Lyndon',
                'middle_names': 'Baines',
                'family_name': 'Johnson',
                'suffix': '',
            }),
            content_type='application/json',
            auth=self.auth
        ).maybe_follow()
        self.user.reload()
        assert_equal(self.user.given_name, 'Lyndon')
        assert_equal(self.user.middle_names, 'Baines')
        assert_equal(self.user.family_name, 'Johnson')


# TODO: Use mock add-on
class TestAddonUserViews(DbTestCase):

    def setUp(self):
        self.user = AuthUserFactory()
        self.app = TestApp(app)

    def test_choose_addons_add(self):
        """Add add-ons; assert that add-ons are attached to project.

        """
        url = '/api/v1/settings/addons/'
        self.app.post_json(
            url,
            {'github': True},
            auth=self.user.auth,
        ).maybe_follow()
        self.user.reload()
        assert_true(self.user.get_addon('github'))

    def test_choose_addons_remove(self):
        """Add, then delete, add-ons; assert that add-ons are not attached to
        project.

        """
        url = '/api/v1/settings/addons/'
        self.app.post_json(
            url,
            {'github': True},
            auth=self.user.auth,
        ).maybe_follow()
        self.app.post_json(
            url,
            {'github': False},
            auth=self.user.auth
        ).maybe_follow()
        self.user.reload()
        assert_false(self.user.get_addon('github'))


# TODO: Move to OSF Storage
class TestFileViews(DbTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = AuthUserFactory()
        self.project = ProjectFactory.build(creator=self.user, is_public=True)
        self.project.add_contributor(self.user)
        self.project.save()

    def test_files_get(self):
        url = '/api/v1/{0}/files/'.format(self.project._primary_key)
        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        assert_equal(res.status_code, 200)
        expected = _view_project(self.project, auth=Auth(user=self.user))
        assert_equal(res.json['node'], expected['node'])
        assert_in('tree_js', res.json)
        assert_in('tree_css', res.json)

    def test_grid_data(self):
        url = '/api/v1/{0}/files/grid/'.format(self.project._primary_key)
        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        assert_equal(res.status_code, 200)
        expected = rubeus.to_hgrid(self.project, auth=Auth(self.user))
        data = res.json['data']
        assert_equal(len(data), len(expected))

if __name__ == '__main__':
    unittest.main()
