# -*- coding: utf-8 -*-
# Generated by Django 1.11.28 on 2021-04-06 14:14
from __future__ import unicode_literals

from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0234_auto_20210610_1812'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='abstractprovider',
            name='in_sloan_study',
        ),
    ]