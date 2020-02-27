# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2019-06-14 14:29
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import django_extensions.db.fields
import osf.models.base
import osf.utils.datetime_aware_jsonfield
import osf.utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0174_add_ab_testing_home_page_version_b_flag'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('_id', models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True)),
                ('action', models.CharField(choices=[(b'file_tag_removed', b'FILE_TAG_REMOVED'), (b'file_tag_added', b'FILE_TAG_ADDED'), (b'addon_file_moved', b'ADDON_FILE_MOVED'), (b'addon_file_copied', b'ADDON_FILE_COPIED'), (b'addon_file_renamed', b'ADDON_FILE_RENAMED'), (b'file_metadata_updated', b'FILE_METADATA_UPDATED'), (b'osf_storage_file_added', b'OSF_STORAGE_FILE_ADDED'), (b'osf_storage_file_updated', b'OSF_STORAGE_FILE_UPDATED'), (b'osf_storage_file_removed', b'OSF_STORAGE_FILE_REMOVED'), (b'osf_storage_file_restored', b'OSF_STORAGE_FILE_RESTORED')], db_index=True, max_length=255)),
                ('params', osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONField(default=dict, encoder=osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONEncoder)),
                ('should_hide', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['-created'],
                'get_latest_by': 'created',
            },
        ),
        migrations.CreateModel(
            name='QuickFolder',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
            },
            bases=('osf.osfstoragefolder',),
        ),
        migrations.AddField(
            model_name='osfuser',
            name='last_logged',
            field=osf.utils.fields.NonNaiveDateTimeField(blank=True, db_index=True, default=django.utils.timezone.now, null=True),
        ),
        migrations.AlterField(
            model_name='basefilenode',
            name='type',
            field=models.CharField(choices=[('osf.trashedfilenode', 'trashed file node'), ('osf.trashedfile', 'trashed file'), ('osf.trashedfolder', 'trashed folder'), ('osf.osfstoragefilenode', 'osf storage file node'), ('osf.osfstoragefile', 'osf storage file'), ('osf.osfstoragefolder', 'osf storage folder'), ('osf.quickfolder', 'quick folder'), ('osf.bitbucketfilenode', 'bitbucket file node'), ('osf.bitbucketfolder', 'bitbucket folder'), ('osf.bitbucketfile', 'bitbucket file'), ('osf.boxfilenode', 'box file node'), ('osf.boxfolder', 'box folder'), ('osf.boxfile', 'box file'), ('osf.dataversefilenode', 'dataverse file node'), ('osf.dataversefolder', 'dataverse folder'), ('osf.dataversefile', 'dataverse file'), ('osf.dropboxfilenode', 'dropbox file node'), ('osf.dropboxfolder', 'dropbox folder'), ('osf.dropboxfile', 'dropbox file'), ('osf.figsharefilenode', 'figshare file node'), ('osf.figsharefolder', 'figshare folder'), ('osf.figsharefile', 'figshare file'), ('osf.githubfilenode', 'github file node'), ('osf.githubfolder', 'github folder'), ('osf.githubfile', 'github file'), ('osf.gitlabfilenode', 'git lab file node'), ('osf.gitlabfolder', 'git lab folder'), ('osf.gitlabfile', 'git lab file'), ('osf.googledrivefilenode', 'google drive file node'), ('osf.googledrivefolder', 'google drive folder'), ('osf.googledrivefile', 'google drive file'), ('osf.onedrivefilenode', 'one drive file node'), ('osf.onedrivefolder', 'one drive folder'), ('osf.onedrivefile', 'one drive file'), ('osf.owncloudfilenode', 'owncloud file node'), ('osf.owncloudfolder', 'owncloud folder'), ('osf.owncloudfile', 'owncloud file'), ('osf.s3filenode', 's3 file node'), ('osf.s3folder', 's3 folder'), ('osf.s3file', 's3 file')], db_index=True, max_length=255),
        ),
        migrations.AddField(
            model_name='userlog',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='user_logs', to=settings.AUTH_USER_MODEL),
        ),
    ]
