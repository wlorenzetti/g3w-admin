# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-04-23 09:56
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('iternet', '0030_auto_20160423_0923'),
    ]

    operations = [
        migrations.AlterField(
            model_name='numerocivico',
            name='cod_top',
            field=models.CharField(max_length=15),
        ),
        migrations.AlterField(
            model_name='numerocivico',
            name='num_civ',
            field=models.FloatField(),
        ),
    ]