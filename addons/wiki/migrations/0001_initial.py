# Generated by Django 2.2 on 2021-03-12 19:44

import addons.wiki.models
from django.db import migrations, models
import django_extensions.db.fields
import osf.models.base
import osf.utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='NodeSettings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('_id', models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('deleted', osf.utils.fields.NonNaiveDateTimeField(blank=True, null=True)),
                ('is_publicly_editable', models.BooleanField(db_index=True, default=False)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, osf.models.base.QuerySetExplainMixin),
        ),
        migrations.CreateModel(
            name='WikiPage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('content_type_pk', models.PositiveIntegerField(blank=True, null=True)),
                ('page_name', models.CharField(max_length=200, validators=[addons.wiki.models.validate_page_name])),
                ('deleted', osf.utils.fields.NonNaiveDateTimeField(blank=True, db_index=True, null=True)),
            ],
            bases=(models.Model, osf.models.base.QuerySetExplainMixin),
        ),
        migrations.CreateModel(
            name='WikiVersion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('_id', models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True)),
                ('content', models.TextField(blank=True, default='')),
                ('identifier', models.IntegerField(default=1)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, osf.models.base.QuerySetExplainMixin),
        ),
    ]
