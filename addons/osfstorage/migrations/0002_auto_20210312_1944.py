# Generated by Django 2.2 on 2021-03-12 19:44

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('addons_osfstorage', '0001_initial'),
        ('osf', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='usersettings',
            name='owner',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='addons_osfstorage_user_settings', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='region',
            unique_together={('_id', 'name')},
        ),
        migrations.AddField(
            model_name='nodesettings',
            name='owner',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='addons_osfstorage_node_settings', to='osf.AbstractNode'),
        ),
        migrations.AddField(
            model_name='nodesettings',
            name='region',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='addons_osfstorage.Region'),
        ),
        migrations.AddField(
            model_name='nodesettings',
            name='root_node',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='osf.OsfStorageFolder'),
        ),
        migrations.AddField(
            model_name='nodesettings',
            name='user_settings',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='addons_osfstorage.UserSettings'),
        ),
    ]
