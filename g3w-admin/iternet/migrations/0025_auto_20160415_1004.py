# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-04-15 10:04
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('iternet', '0024_comuni'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comuni',
            name='cod_catastale',
            field=models.CharField(max_length=4, null=True),
        ),
    ]