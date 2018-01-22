# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-01-12 21:17
from __future__ import unicode_literals

from django.db import migrations
from django.db.models import OuterRef, Subquery
import osf.utils.fields

from osf.models import PreprintService, NodeLog


def update_deleted_field(*args, **kwargs):
    nodelog_subqueryset  = NodeLog.objects.filter(node_id=OuterRef('node___id'), action='project_deleted').values('date')
    PreprintService.objects.filter(node__is_deleted=True).update(
        deleted=Subquery(nodelog_subqueryset)
    )


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0076_action_rename'),
    ]

    operations = [
        migrations.RenameField(
            model_name='abstractnode',
            old_name='deleted_date',
            new_name='deleted',
        ),
        migrations.RenameField(
            model_name='basefilenode',
            old_name='deleted_on',
            new_name='deleted',
        ),
        migrations.AddField(
            model_name='comment',
            name='deleted',
            field=osf.utils.fields.NonNaiveDateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='preprintservice',
            name='deleted',
            field=osf.utils.fields.NonNaiveDateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='privatelink',
            name='deleted',
            field=osf.utils.fields.NonNaiveDateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reviewaction',
            name='deleted',
            field=osf.utils.fields.NonNaiveDateTimeField(blank=True, null=True),
        ),
        migrations.RunSQL([
            """
            UPDATE osf_abstractnode
            SET deleted = (
                SELECT date FROM osf_nodelog
                WHERE node_id = "osf_abstractnode"."id" AND action = 'project_deleted'
                LIMIT 1)
            WHERE osf_abstractnode.is_deleted = True;
            """,
            """
            UPDATE osf_abstractnode
            SET deleted='epoch' WHERE deleted IS NULL AND is_deleted=True;
            """,
            """
            UPDATE osf_comment
            SET deleted=(
                SELECT date from osf_nodelog
                WHERE node_id = "osf_comment"."node_id"  AND action='comment_removed'
                ORDER BY date DESC
                LIMIT 1)
            WHERE osf_comment.is_deleted = True;
            """,
            """
            UPDATE osf_comment
            SET deleted='epoch' WHERE deleted IS NULL AND is_deleted=True;
            """,
            """
            UPDATE osf_privatelink
            SET deleted='epoch' WHERE deleted IS NULL AND is_deleted=True;
            """,
            """
            UPDATE osf_reviewaction
            SET deleted='epoch' WHERE deleted IS NULL AND is_deleted=True;
            """,
            """
            UPDATE osf_preprintservice
            SET deleted = (
              SELECT date FROM osf_nodelog
              WHERE node_id = osf_preprintservice.node_id AND action = 'project_deleted'
              LIMIT 1
            ) WHERE (
              SELECT is_deleted from osf_abstractnode
              WHERE node_id = osf_abstractnode.id
            ) = True;
            """
            ], [
        ])
    ]
