# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-08-28 21:02
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0131_auto_20180828_0444'),
    ]

    operations = [
        migrations.CreateModel(
            name='OSFGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('name', models.TextField()),
                ('creator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='osfgroups_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'permissions': (('member_group', 'Has group membership'), ('manage_group', 'Can manage group membership'),),
            },
        ),
    ]
