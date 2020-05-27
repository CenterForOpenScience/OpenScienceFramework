# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2020-05-27 13:30
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('addons_zotero', '0006_rename_deleted_field'),
    ]

    operations = [
        migrations.AlterField(
            model_name='nodesettings',
            name='user_settings',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='addons_zotero.UserSettings'),
        ),
    ]
