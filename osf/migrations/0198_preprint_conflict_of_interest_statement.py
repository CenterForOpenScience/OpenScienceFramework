# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2020-01-29 16:27
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0197_add_ab_testing_home_page_hero_text_version_b_flag'),
    ]

    operations = [
        migrations.AddField(
            model_name='preprint',
            name='conflict_of_interest_statement',
            field=models.CharField(blank=True, max_length=5000, null=True),
        ),
    ]
