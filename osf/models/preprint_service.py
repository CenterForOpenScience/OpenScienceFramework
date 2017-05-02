# -*- coding: utf-8 -*-
import urlparse

from dirtyfields import DirtyFieldsMixin
from django.db import models
from django.utils import timezone

from framework.celery_tasks.handlers import enqueue_task
from framework.exceptions import PermissionsError
from osf.utils.fields import NonNaiveDateTimeField
from website.files.models import StoredFileNode
from website.preprints.tasks import on_preprint_updated
from website.project.model import NodeLog
from website.project.licenses import set_license
from website.project.taxonomies import validate_subject_hierarchy
from website.util import api_v2_url
from website.util.permissions import ADMIN
from website import settings

from osf.models.base import BaseModel, GuidMixin
from osf.models.subject import Subject

class PreprintService(DirtyFieldsMixin, GuidMixin, BaseModel):
    date_created = NonNaiveDateTimeField(auto_now_add=True)
    date_modified = NonNaiveDateTimeField(auto_now=True)
    provider = models.ForeignKey('osf.PreprintProvider',
                                 on_delete=models.SET_NULL,
                                 related_name='preprint_services',
                                 null=True, blank=True, db_index=True)
    node = models.ForeignKey('osf.AbstractNode', on_delete=models.SET_NULL,
                             related_name='preprints',
                             null=True, blank=True, db_index=True)
    is_published = models.BooleanField(default=False, db_index=True)
    date_published = NonNaiveDateTimeField(null=True, blank=True)
    license = models.ForeignKey('osf.NodeLicenseRecord',
                                on_delete=models.SET_NULL, null=True, blank=True)

    subjects = models.ManyToManyField(blank=True, to='osf.Subject')

    class Meta:
        unique_together = ('node', 'provider')
        permissions = (
            ('view_preprintservice', 'Can view preprint service details in the admin app.'),
        )

    def __unicode__(self):
        return '{} preprint (guid={}) of {}'.format('published' if self.is_published else 'unpublished', self._id, self.node.__unicode__())

    @property
    def primary_file(self):
        if not self.node:
            return
        return self.node.preprint_file

    @property
    def article_doi(self):
        if not self.node:
            return
        return self.node.preprint_article_doi

    @property
    def is_preprint_orphan(self):
        if not self.node:
            return
        return self.node.is_preprint_orphan

    @property
    def subject_hierarchy(self):
        return [
            s.object_hierarchy for s in self.subjects.exclude(children__in=self.subjects.all())
        ]

    @property
    def deep_url(self):
        # Required for GUID routing
        return '/preprints/{}/'.format(self._primary_key)

    @property
    def url(self):
        if self.provider.domain_redirect_enabled or self.provider._id == 'osf':
            return '/{}/'.format(self._id)

        return '/preprints/{}/{}/'.format(self.provider._id, self._id)

    @property
    def absolute_url(self):
        return urlparse.urljoin(
            self.provider.domain if self.provider.domain_redirect_enabled else settings.DOMAIN,
            self.url
        )

    @property
    def absolute_api_v2_url(self):
        path = '/preprints/{}/'.format(self._id)
        return api_v2_url(path)

    def has_permission(self, *args, **kwargs):
        return self.node.has_permission(*args, **kwargs)

    def get_subjects(self):
        ret = []
        for subj_list in self.subject_hierarchy:
            subj_hierarchy = []
            for subj in subj_list:
                if subj:
                    subj_hierarchy += ({'id': subj._id, 'text': subj.text}, )
            if subj_hierarchy:
                ret.append(subj_hierarchy)
        return ret

    def set_subjects(self, preprint_subjects, auth, save=False):
        if not self.node.has_permission(auth.user, ADMIN):
            raise PermissionsError('Only admins can change a preprint\'s subjects.')

        self.subjects.clear()
        for subj_list in preprint_subjects:
            subj_hierarchy = []
            for s in subj_list:
                subj_hierarchy.append(s)
            if subj_hierarchy:
                validate_subject_hierarchy(subj_hierarchy)
                for s_id in subj_hierarchy:
                    self.subjects.add(Subject.load(s_id))

        if save:
            self.save()

    def set_primary_file(self, preprint_file, auth, save=False):
        if not self.node.has_permission(auth.user, ADMIN):
            raise PermissionsError('Only admins can change a preprint\'s primary file.')

        if not isinstance(preprint_file, StoredFileNode):
            preprint_file = preprint_file.stored_object

        if preprint_file.node != self.node or preprint_file.provider != 'osfstorage':
            raise ValueError('This file is not a valid primary file for this preprint.')

        existing_file = self.node.preprint_file
        self.node.preprint_file = preprint_file

        # only log if updating the preprint file, not adding for the first time
        if existing_file:
            self.node.add_log(
                action=NodeLog.PREPRINT_FILE_UPDATED,
                params={
                    'preprint': self._id
                },
                auth=auth,
                save=False
            )

        if save:
            self.save()
            self.node.save()

    def set_published(self, published, auth, save=False):
        if not self.node.has_permission(auth.user, ADMIN):
            raise PermissionsError('Only admins can publish a preprint.')

        if self.is_published and not published:
            raise ValueError('Cannot unpublish preprint.')

        self.is_published = published

        if published:
            if not (self.node.preprint_file and self.node.preprint_file.node == self.node):
                raise ValueError('Preprint node is not a valid preprint; cannot publish.')
            if not self.provider:
                raise ValueError('Preprint provider not specified; cannot publish.')
            if not self.subjects:
                raise ValueError('Preprint must have at least one subject to be published.')
            self.date_published = timezone.now()
            self.node._has_abandoned_preprint = False

            self.node.add_log(
                action=NodeLog.PREPRINT_INITIATED,
                params={
                    'preprint': self._id
                },
                auth=auth,
                save=False,
            )

            if not self.node.is_public:
                self.node.set_privacy(
                    self.node.PUBLIC,
                    auth=None,
                    log=True
                )

        if save:
            self.node.save()
            self.save()

    def set_preprint_license(self, license_detail, auth, save=False):
        license_record, license_changed = set_license(self, license_detail, auth, node_type='preprint')

        if license_changed:
            self.node.add_log(
                action=NodeLog.PREPRINT_LICENSE_UPDATED,
                params={
                    'preprint': self._id,
                    'new_license': license_record.node_license.name
                },
                auth=auth,
                save=False
            )

        if save:
            self.save()

    def save(self, *args, **kwargs):
        first_save = not bool(self.pk)
        saved_fields = self.get_dirty_fields() or []
        ret = super(PreprintService, self).save(*args, **kwargs)

        if (not first_save and 'is_published' in saved_fields) or self.is_published:
            enqueue_task(on_preprint_updated.s(self._id))
        return ret
