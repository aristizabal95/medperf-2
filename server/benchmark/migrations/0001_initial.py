# Generated by Django 3.2.10 on 2022-03-07 09:34

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("mlcube", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Benchmark",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=20, unique=True)),
                ("description", models.CharField(blank=True, max_length=100)),
                ("docs_url", models.CharField(blank=True, max_length=100)),
                ("demo_dataset_tarball_url", models.CharField(max_length=256)),
                ("demo_dataset_tarball_hash", models.CharField(max_length=100)),
                ("demo_dataset_generated_uid", models.CharField(max_length=128)),
                ("metadata", models.JSONField(blank=True, default=dict, null=True)),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("DEVELOPMENT", "DEVELOPMENT"),
                            ("OPERATION", "OPERATION"),
                        ],
                        default="DEVELOPMENT",
                        max_length=100,
                    ),
                ),
                ("is_valid", models.BooleanField(default=True)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "approval_status",
                    models.CharField(
                        choices=[
                            ("PENDING", "PENDING"),
                            ("APPROVED", "APPROVED"),
                            ("REJECTED", "REJECTED"),
                        ],
                        default="PENDING",
                        max_length=100,
                    ),
                ),
                (
                    "user_metadata",
                    models.JSONField(blank=True, default=dict, null=True),
                ),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("modified_at", models.DateTimeField(auto_now=True)),
                (
                    "data_evaluator_mlcube",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="data_evaluator_mlcube",
                        to="mlcube.mlcube",
                    ),
                ),
                (
                    "data_preparation_mlcube",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="data_preprocessor_mlcube",
                        to="mlcube.mlcube",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "reference_model_mlcube",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reference_model_mlcube",
                        to="mlcube.mlcube",
                    ),
                ),
            ],
            options={"ordering": ["modified_at"],},
        ),
    ]
