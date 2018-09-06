# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-09-05 18:31
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0132_remove_node_preprint_fields'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='preprint',
            options={'permissions': (('view_preprint', 'Can view preprint details in the admin app'), ('read_preprint', 'Can read the preprint'), ('write_preprint', 'Can write the preprint'), ('admin_preprint', 'Can manage the preprint'))},
        ),
    ]