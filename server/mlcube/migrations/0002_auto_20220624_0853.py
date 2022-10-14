# Generated by Django 3.2.10 on 2022-06-24 08:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mlcube", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="mlcube",
            old_name="tarball_hash",
            new_name="additional_files_tarball_hash",
        ),
        migrations.RenameField(
            model_name="mlcube",
            old_name="tarball_url",
            new_name="additional_files_tarball_url",
        ),
        migrations.AddField(
            model_name="mlcube",
            name="image_tarball_hash",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="mlcube",
            name="image_tarball_url",
            field=models.CharField(blank=True, max_length=256),
        ),
        migrations.AlterUniqueTogether(
            name="mlcube",
            unique_together={
                (
                    "image_tarball_url",
                    "image_tarball_hash",
                    "additional_files_tarball_url",
                    "additional_files_tarball_hash",
                    "git_mlcube_url",
                    "git_parameters_url",
                )
            },
        ),
    ]
