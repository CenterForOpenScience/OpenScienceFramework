import unittest
from nose.tools import *

import os
import urllib
import urlparse

from framework.exceptions import HTTPError

from website.addons.gitlab.tests import GitlabTestCase
from website.addons.gitlab import utils


def normalize_query_string(url):
    parsed = urlparse.urlparse(url)
    query_data = dict(urlparse.parse_qsl(parsed.query))
    query_str = urllib.urlencode(query_data)
    return parsed._replace(query=query_str).geturl()


def assert_urls_equal(url1, url2):
    assert_equal(
        normalize_query_string(url1),
        normalize_query_string(url2)
    )


class TestTranslatePermissions(unittest.TestCase):

    def test_translate_admin(self):
        assert_equal(
            utils.translate_permissions(['read', 'write', 'admin']),
            'master'
        )

    def test_translate_write(self):
        assert_equal(
            utils.translate_permissions(['read', 'write']),
            'developer'
        )

    def test_translate_read(self):
        assert_equal(
            utils.translate_permissions(['read']),
            'reporter'
        )


class TestKwargsToPath(unittest.TestCase):

    def test_kwargs_to_path(self):
        assert_equal(
            utils.kwargs_to_path({'path': 'foo/bar/baz'}),
            urllib.unquote_plus('foo/bar/baz')
        )

    def test_kwargs_to_path_required(self):
        with assert_raises(HTTPError):
            utils.kwargs_to_path({}, required=True)


class TestRefsToParams(unittest.TestCase):

    def test_no_kwargs(self):
        assert_equal(
            utils.refs_to_params(),
            ''
        )

    def test_branch(self):
        assert_equal(
            utils.refs_to_params(branch='master'),
            '?' + urllib.urlencode({'branch': 'master'})
        )

    def test_sha(self):
        assert_equal(
            utils.refs_to_params(sha='12345'),
            '?' + urllib.urlencode({'sha': '12345'})
        )

    def test_branch_sha(self):
        assert_equal(
            utils.refs_to_params(branch='master', sha='12345'),
            '?' + urllib.urlencode({'branch': 'master', 'sha': '12345'})
        )


class TestSlugify(unittest.TestCase):

    def test_replace_special(self):
        assert_equal(
            utils.gitlab_slugify('foo&bar_baz'),
            'foo-bar-baz'
        )

    def test_replace_git(self):
        assert_equal(
            utils.gitlab_slugify('foo.git'),
            'foo'
        )


class TestBuildUrls(GitlabTestCase):

    def setUp(self):
        super(TestBuildUrls, self).setUp()
        self.app.app.test_request_context().push()

    def test_tree(self):

        item = {
            'name': 'foo',
            'type': 'tree',
        }
        path = 'myfolder'
        branch = 'master'
        sha = '12345'

        output = utils.build_urls(
            self.project, item, path, branch, sha
        )

        quote_path = urllib.quote_plus(path)

        assert_equal(
            set(output.keys()),
            {'upload', 'fetch'}
        )
        assert_urls_equal(
            output['upload'],
            self.node_lookup(
                'api', 'gitlab_upload_file',
                path=quote_path, branch=branch
            )
        )
        assert_urls_equal(
            output['fetch'],
            self.node_lookup(
                'api', 'gitlab_list_files',
                path=quote_path, branch=branch, sha=sha
            )
        )

    def test_blob(self):

        item = {
            'name': 'bar',
            'type': 'blob',
        }
        path = 'myfolder'
        branch = 'master'
        sha = '12345'

        output = utils.build_urls(
            self.project, item, path, branch, sha
        )

        quote_path = urllib.quote_plus(path)

        assert_equal(
            set(output.keys()),
            {'view', 'download', 'delete'}
        )
        assert_urls_equal(
            output['view'],
            self.node_lookup(
                'web', 'gitlab_view_file',
                path=quote_path, branch=branch, sha=sha
            )
        )
        assert_urls_equal(
            output['download'],
            self.node_lookup(
                'web', 'gitlab_download_file',
                path=quote_path, branch=branch, sha=sha
            )
        )
        assert_urls_equal(
            output['delete'],
            self.node_lookup(
                'api', 'gitlab_delete_file',
                path=quote_path, branch=branch
            )
        )

    def test_bad_type(self):
        with assert_raises(ValueError):
            utils.build_urls(
                self.project, item={'type': 'bad'}, path=''
            )


class TestGridSerializers(GitlabTestCase):

    def setUp(self):
        super(TestGridSerializers, self).setUp()
        self.app.app.test_request_context().push()

    def test_item_to_hgrid(self):

        item = {
            'name': 'myfile',
            'type': 'blob',
        }
        path = 'myfolder'
        permissions = {
            'view': True,
            'edit': True,
        }

        output = utils.item_to_hgrid(
            self.project, item, path, permissions
        )

        assert_equal(output['name'], 'myfile')
        assert_equal(output['kind'], utils.type_to_kind['blob'])
        assert_equal(output['permissions'], permissions)
        assert_equal(
            output['urls'],
            utils.build_urls(
                self.project, item, os.path.join(path, item['name'])
            )
        )
