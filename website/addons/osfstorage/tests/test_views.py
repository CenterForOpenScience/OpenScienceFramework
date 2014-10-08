# -*- coding: utf-8 -*-

from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import ProjectFactory

from website.addons.osfstorage.tests import factories

import hashlib
import urlparse

from cloudstorm import sign

from website.addons.osfstorage import model
from website.addons.osfstorage import utils
from website.addons.osfstorage import settings as osf_storage_settings


def create_record_with_version(path, node_settings, **kwargs):
    version = factories.FileVersionFactory(**kwargs)
    record = model.FileRecord.get_or_create(path, node_settings)
    record.versions.append(version)
    record.save()
    return record


class TestHGridViews(OsfTestCase):

    def setUp(self):
        super(TestHGridViews, self).setUp()
        self.project = ProjectFactory()
        self.node_settings = self.project.get_addon('osfstorage')

    def test_hgrid_contents(self):
        path = 'kind/of/magic.mp3'
        model.FileRecord.get_or_create(
            path=path,
            node_settings=self.node_settings,
        )
        version = factories.FileVersionFactory()
        record = model.FileRecord.find_by_path(path, self.node_settings)
        record.versions.append(version)
        record.save()
        res = self.app.get(
            self.project.api_url_for(
                'osf_storage_hgrid_contents',
                path='kind/of',
            ),
            auth=self.project.creator.auth,
        )
        assert_equal(len(res.json), 1)
        assert_equal(
            res.json[0],
            utils.serialize_metadata_hgrid(
                record,
                self.project,
                {
                    'edit': True,
                    'view': True,
                }
            )
        )

    def test_hgrid_contents_tree_not_found_root_path(self):
        res = self.app.get(
            self.project.api_url_for(
                'osf_storage_hgrid_contents',
            ),
            auth=self.project.creator.auth,
        )
        assert_equal(res.json, [])

    def test_hgrid_contents_tree_not_found_nested_path(self):
        res = self.app.get(
            self.project.api_url_for(
                'osf_storage_hgrid_contents',
                path='not/found',
            ),
            auth=self.project.creator.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 404)


class TestSignedUrlViews(OsfTestCase):

    def setUp(self):
        super(TestSignedUrlViews, self).setUp()
        self.project = ProjectFactory()
        self.node_settings = self.project.get_addon('osfstorage')


class TestHookViews(OsfTestCase):

    def setUp(self):
        super(TestHookViews, self).setUp()
        self.project = ProjectFactory()
        self.node_settings = self.project.get_addon('osfstorage')

    def send_hook(self, view_name, payload, signature, path=None, **kwargs):
        return self.app.put_json(
            self.project.api_url_for(view_name, path=path),
            payload,
            headers={
                osf_storage_settings.SIGNATURE_HEADER_KEY: signature,
            },
            **kwargs
        )

    def send_start_hook(self, payload, signature, path=None, **kwargs):
        return self.send_hook(
            'osf_storage_upload_start_hook',
            payload, signature, path,
            **kwargs
        )

    def send_finish_hook(self, payload, signature, path=None, **kwargs):
        return self.send_hook(
            'osf_storage_upload_finish_hook',
            payload, signature, path,
            **kwargs
        )

    def test_start_hook(self):
        payload = {'uploadSignature': '07235a8'}
        message, signature = utils.webhook_signer.sign_payload(payload)
        path = 'crunchy/pizza.png'
        res = self.send_start_hook(
            payload=payload, signature=signature, path=path,
        )
        assert_equal(res.status_code, 200)
        assert_equal(res.json['status'], 'success')
        self.node_settings.reload()
        assert_true(self.node_settings.file_tree)
        record = model.FileRecord.find_by_path(path, self.node_settings)
        assert_true(record)
        assert_equal(len(record.versions), 1)
        assert_equal(record.versions[0].status, model.status['PENDING'])

    def test_start_hook_invalid_signature(self):
        payload = {'uploadSignature': '07235a8'}
        path = 'soggy/pizza.png'
        res = self.send_start_hook(
            payload=payload, signature='invalid', path=path,
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)
        assert_equal(res.json['code'], 400)

    def test_start_hook_path_locked(self):
        payload = {'uploadSignature': '07235a8'}
        path = 'cold/pizza.png'
        message, signature = utils.webhook_signer.sign_payload(payload)
        record = model.FileRecord.get_or_create(path, self.node_settings)
        record.create_pending_version('4217713')
        res = self.send_start_hook(
            payload=payload, signature=signature, path=path,
            expect_errors=True,
        )
        assert_equal(res.status_code, 409)
        assert_equal(res.json['code'], 409)
        record.reload()
        assert_equal(len(record.versions), 1)

    def test_start_hook_signature_consumed(self):
        payload = {'uploadSignature': '07235a8'}
        message, signature = utils.webhook_signer.sign_payload(payload)
        path = 'rotten/pizza.png'
        record = model.FileRecord.get_or_create(path, self.node_settings)
        record.create_pending_version('07235a8')
        record.resolve_pending_version(
            '07235a8',
            factories.generic_location,
            {'size': 1024},
        )
        res = self.send_start_hook(
            payload=payload, signature=signature, path=path,
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)
        assert_equal(res.json['code'], 400)
        record.reload()
        assert_equal(len(record.versions), 1)

    def test_finish_hook_status_success(self):
        size = 1024
        payload = {
            'status': 'success',
            'uploadSignature': '07235a8',
            'location': factories.generic_location,
            'metadata': {'size': size},
        }
        message, signature = utils.webhook_signer.sign_payload(payload)
        path = 'rotten/pizza.png'
        record = model.FileRecord.get_or_create(path, self.node_settings)
        record.create_pending_version('07235a8')
        version = record.versions[0]
        res = self.send_finish_hook(
            payload=payload, signature=signature, path=path,
        )
        assert_equal(res.status_code, 200)
        version.reload()
        assert_equal(version.status, model.status['COMPLETE'])
        assert_equal(version.size, size)

    def test_finish_hook_status_error(self):
        size = 1024
        payload = {
            'status': 'error',
            'uploadSignature': '07235a8',
        }
        message, signature = utils.webhook_signer.sign_payload(payload)
        path = 'rotten/pizza.png'
        record = model.FileRecord.get_or_create(path, self.node_settings)
        record.create_pending_version('07235a8')
        version = record.versions[0]
        res = self.send_finish_hook(
            payload=payload, signature=signature, path=path,
        )
        assert_equal(res.status_code, 200)
        version.reload()
        assert_equal(version.status, model.status['FAILED'])

    def test_finish_hook_status_unknown(self):
        pass

    def test_finish_hook_invalid_signature(self):
        pass

    def test_finish_hook_record_not_found(self):
        pass

    def test_finish_hook_status_success_no_upload_pending(self):
        pass

    def test_finish_hook_status_error_no_upload_pending(self):
        pass

    def test_finish_hook_status_success_already_complete(self):
        pass

    def test_finish_hook_status_error_already_complete(self):
        pass


class TestViewFile(OsfTestCase):

    def setUp(self):
        super(TestViewFile, self).setUp()
        self.project = ProjectFactory()
        self.node_settings = self.project.get_addon('osfstorage')
        self.path = 'kind/of/magic.mp3'
        self.record = model.FileRecord.get_or_create(self.path, self.node_settings)
        self.version = factories.FileVersionFactory()
        self.record.versions.append(self.version)
        self.record.save()

    def view_file(self, path):
        return self.app.get(
            self.project.web_url_for('osf_storage_view_file', path=path),
            auth=self.project.creator.auth,
        )

    def test_view_file_creates_guid_if_none_exists(self):
        n_objs = model.StorageFile.find().count()
        res = self.view_file(self.path)
        assert_equal(n_objs + 1, model.StorageFile.find().count())
        assert_equal(res.status_code, 302)
        file_obj = model.StorageFile.find_one(node=self.project, path=self.path)
        redirect_parsed = urlparse.urlparse(res.location)
        assert_equal(redirect_parsed.path.strip('/'), file_obj._id)

    def test_view_file_does_not_create_guid_if_exists(self):
        _ = self.view_file(self.path)
        n_objs = model.StorageFile.find().count()
        res = self.view_file(self.path)
        assert_equal(n_objs, model.StorageFile.find().count())

    def test_view_file_redirects_to_guid_url(self):
        res = self.view_file(self.path).follow(auth=self.project.creator.auth)
        assert_equal(res.status_code, 200)
        assert_true(res.html.find('h1', text='magic.mp3'))


class TestDeleteFile(OsfTestCase):

    def setUp(self):
        super(TestDeleteFile, self).setUp()
        self.project = ProjectFactory()
        self.node_settings = self.project.get_addon('osfstorage')

    def test_delete_file(self):
        path = 'going/slightly/mad.mp3'
        record = create_record_with_version(
            path,
            self.node_settings,
            status=model.status['COMPLETE'],
        )
        assert_false(record.is_deleted)
        res = self.app.delete(
            self.project.api_url_for(
                'osf_storage_delete_file',
                path=path,
            ),
            auth=self.project.creator.auth,
        )
        assert_equal(res.json['status'], 'success')
        record.reload()
        assert_true(record.is_deleted)

    def test_delete_file_already_deleted(self):
        path = 'going/slightly/mad.mp3'
        record = create_record_with_version(
            path,
            self.node_settings,
            status=model.status['COMPLETE'],
        )
        record.delete()
        record.save()
        assert_true(record.is_deleted)
        res = self.app.delete(
            self.project.api_url_for(
                'osf_storage_delete_file',
                path=path,
            ),
            auth=self.project.creator.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 404)
        assert_equal(res.json['code'], 404)
        record.reload()
        assert_true(record.is_deleted)

    def test_delete_file_not_found(self):
        res = self.app.delete(
            self.project.api_url_for(
                'osf_storage_delete_file',
                path='im/not/there.avi',
            ),
            auth=self.project.creator.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 404)
        assert_equal(res.json['code'], 404)

