# Generated by Django 3.2.20 on 2024-07-22 16:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dataset', '0004_auto_20231211_1827'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dataset',
            name='description',
            field=models.CharField(blank=True, max_length=256),
        ),
    ]
