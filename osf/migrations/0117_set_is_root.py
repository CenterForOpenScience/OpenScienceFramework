# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-07-11 18:05
from __future__ import unicode_literals

from django.db import migrations


def set_is_root(state, *args, **kwargs):
    OsfStorageFolder = state.get_model('osf', 'osfstoragefolder')
    OsfStorageFolder.objects.filter(nodesettings__isnull=False, is_root__isnull=True).update(is_root=True)


def unset_is_root(state, *args, **kwargs):
    state.get_model('osf', 'osfstoragefolder').objects.filter(is_root=True).update(is_root=None)


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0116_merge_20180706_0901'),
    ]

    operations = [
        migrations.RunPython(set_is_root, unset_is_root),
    ]
