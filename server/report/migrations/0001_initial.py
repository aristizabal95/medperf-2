# Generated by Django 3.2.20 on 2023-09-22 11:13

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('benchmark', '0001_initial'),
        ('mlcube', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Report',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dataset_name', models.CharField(max_length=20)),
                ('description', models.CharField(blank=True, max_length=20)),
                ('location', models.CharField(blank=True, max_length=100)),
                ('input_data_hash', models.CharField(max_length=128)),
                ('is_valid', models.BooleanField(default=True)),
                ('contents', models.JSONField(blank=True, default=dict, null=True)),
                ('metadata', models.JSONField(blank=True, default=dict, null=True)),
                ('user_metadata', models.JSONField(blank=True, default=dict, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('benchmark', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='benchmark.benchmark')),
                ('data_preparation_mlcube', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='mlcube.mlcube')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['modified_at'],
            },
        ),
    ]