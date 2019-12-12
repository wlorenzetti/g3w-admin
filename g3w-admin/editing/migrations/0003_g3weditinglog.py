# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2018-08-23 15:30
from __future__ import unicode_literals

from django.conf import settings
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('editing', '0002_g3weditinglayer'),
    ]

    operations = [
        migrations.CreateModel(
            name='G3WEditingLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False)),
                ('app_name', models.CharField(max_length=255)),
                ('layer_id', models.IntegerField()),
                ('msg', django.contrib.postgres.fields.jsonb.JSONField()),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
