# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2019-01-14 17:02
from __future__ import unicode_literals

from django.db import migrations
import osf.utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0153_merge_20181221_1842'),
    ]

    operations = [
        migrations.AddField(
            model_name='osfuser',
            name='submit_reset_token_last_attempt',
            field=osf.utils.fields.NonNaiveDateTimeField(blank=True, null=True),
        ),
    ]
