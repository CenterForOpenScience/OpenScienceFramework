# -*- coding: utf-8 -*-
# Generated by Django 1.11.28 on 2021-03-17 20:13
from __future__ import unicode_literals

from django.db import migrations
import osf.utils.datetime_aware_jsonfield


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0227_abstractnode_branched_from_node.py'),
    ]

    operations = [
        migrations.AddField(
            model_name='abstractnode',
            name='additional_metadata',
            field=osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONField(blank=True, default=list, encoder=osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONEncoder, null=True),
        ),
        migrations.AddField(
            model_name='abstractprovider',
            name='additional_metadata_fields',
            field=osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONField(blank=True, default=list, encoder=osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONEncoder, null=True),
        ),
    ]
