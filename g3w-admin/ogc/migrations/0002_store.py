# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-05-13 13:09
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ogc', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Store',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Name')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('type', models.CharField(choices=[(b'wms', 'WMS'), (b'wmst', b'wmst'), ('WMST', 'WMST'), (b'wfs', 'WFS')], max_length=20, verbose_name='OGC Type')),
                ('url', models.URLField(verbose_name='URL')),
                ('username', models.URLField(blank=True, max_length=255, null=True, verbose_name='Username')),
                ('password', models.CharField(blank=True, max_length=255, null=True, verbose_name='Passaword')),
            ],
            options={
                'permissions': (('view_ogc_store', 'Can view OGC store'),),
            },
        ),
    ]