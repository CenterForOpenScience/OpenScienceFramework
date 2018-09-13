# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.db import migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0128_merge_20180829_0012'),
    ]

    operations = [
        migrations.RunSQL([
            """
            CREATE TABLE "{}" (
                "cache_key" varchar(255) NOT NULL PRIMARY KEY,
                "value" text NOT NULL,
                "expires" timestamp with time zone NOT NULL
            );
            """.format(settings.CACHES['default']['LOCATION'])
        ], [
            """DROP TABLE "{}"; """.format(settings.CACHES['default']['LOCATION'])
        ])
    ]
