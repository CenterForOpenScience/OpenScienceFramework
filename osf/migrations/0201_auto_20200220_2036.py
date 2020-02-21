# Generated by Django 2.0.13 on 2020-02-20 20:36

import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion
import osf.utils.datetime_aware_jsonfield


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0200_auto_20200214_1518'),
    ]

    operations = [
        migrations.AlterField(
            model_name='abstractnode',
            name='provider',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='registrations', to='osf.RegistrationProvider'),
        ),
        migrations.AlterField(
            model_name='abstractnode',
            name='registered_meta',
            field=osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONField(blank=True, default=dict, encoder=osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONEncoder),
        ),
        migrations.AlterField(
            model_name='abstractprovider',
            name='additional_providers',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=200), blank=True, default=list, size=None),
        ),
        migrations.AlterField(
            model_name='abstractprovider',
            name='preprint_word',
            field=models.CharField(choices=[('preprint', 'Preprint'), ('paper', 'Paper'), ('thesis', 'Thesis'), ('work', 'Work'), ('none', 'None')], default='preprint', max_length=10),
        ),
        migrations.AlterField(
            model_name='abstractprovider',
            name='share_publish_type',
            field=models.CharField(choices=[('Preprint', 'Preprint'), ('Thesis', 'Thesis')], default='Preprint', help_text='This SHARE type will be used when pushing publications to SHARE', max_length=32),
        ),
        migrations.AlterField(
            model_name='abstractprovider',
            name='share_title',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='abstractprovider',
            name='subjects_acceptable',
            field=osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONField(blank=True, default=list, encoder=osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONEncoder),
        ),
        migrations.AlterField(
            model_name='collection',
            name='collected_types',
            field=models.ManyToManyField(limit_choices_to={'model__in': ['abstractnode', 'basefilenode', 'collection', 'preprint']}, related_name='_collection_collected_types_+', to='contenttypes.ContentType'),
        ),
    ]