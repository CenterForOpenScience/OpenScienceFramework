# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-06-28 17:53
from __future__ import unicode_literals

import logging
from django.db import migrations

from osf.models import PreprintProvider

logger = logging.getLogger(__file__)

PREPRINT_DOI_NAMESPACE = {
    'africarxiv': '10.31730',
}

def add_doi_prefix(*args, **kwargs):
    for key, value in PREPRINT_DOI_NAMESPACE.items():
        provider = PreprintProvider.objects.filter(_id=key)
        if not provider.exists():
            logger.info('Could not find provider with _id {}, skipping for now...'.format(key))
            continue
        provider = provider.get()
        provider.doi_prefix = value
        provider.save()


def remove_doi_prefix(*args, **kwargs):
    for key, _ in PREPRINT_DOI_NAMESPACE.items():
        provider = PreprintProvider.objects.filter(_id=key)
        if not provider.exists():
            logger.info('Could not find provider with _id {}, skipping for now...'.format(key))
            continue
        provider = provider.get()
        provider.doi_prefix = ''
        provider.save()

class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0114_merge_20180628_1234'),
    ]

    operations = [
        migrations.RunPython(add_doi_prefix, remove_doi_prefix),
    ]
