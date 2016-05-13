# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-05-12 13:02
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales_analytics', '0001_squashed_0002_auto_20160512_1015'),
    ]

    operations = [
        migrations.CreateModel(
            name='DBMetrics',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(auto_now_add=True)),
                ('name', models.TextField()),
                ('data', models.TextField()),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='dbmetrics',
            unique_together=set([('date', 'name')]),
        ),
    ]
