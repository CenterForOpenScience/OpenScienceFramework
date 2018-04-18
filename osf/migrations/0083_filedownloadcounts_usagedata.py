# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-02-21 21:29
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import osf.utils.datetime_aware_jsonfield


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0082_merge_20180213_1502'),
    ]

    operations = [
        migrations.CreateModel(
            name='UsageData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('update_date', osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONField(default=dict, encoder=osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONEncoder)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='FileDownloadCounts',
            fields=[
                ('usagedata_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='osf.UsageData')),
                ('number_downloads_total', models.PositiveIntegerField(default=0)),
                ('number_downloads_unique', models.PositiveIntegerField(default=0)),
            ],
            options={
                'abstract': False,
            },
            bases=('osf.usagedata',),
        ),
    ]
