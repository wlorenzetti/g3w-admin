# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-11-25 09:53
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('qdjango', '0039_merge_20190522_0733'),
    ]

    operations = [
        migrations.AddField(
            model_name='layer',
            name='external',
            field=models.BooleanField(default=False, verbose_name='Get WMS/WMS externally'),
        ),
    ]