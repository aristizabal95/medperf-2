# Generated by Django 3.2.20 on 2023-10-19 22:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mlcube', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='mlcube',
            name='git_stages_url',
            field=models.CharField(blank=True, max_length=256),
        ),
        migrations.AddField(
            model_name='mlcube',
            name='stages_hash',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
