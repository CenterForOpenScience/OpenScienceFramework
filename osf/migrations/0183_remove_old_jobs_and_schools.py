# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2019-03-08 14:00
from __future__ import unicode_literals

from django.db import migrations
from django.conf import settings


if settings.AUTO_RUN_DATA_MIGRATION:
    operations = []
else:
    operations = [
        migrations.RemoveField(
            model_name='osfuser',
            name='jobs',
        ),
        migrations.RemoveField(
            model_name='osfuser',
            name='schools',
        ),
    ]


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0182_add_education_employment_models'),
    ]

    operations = operations
