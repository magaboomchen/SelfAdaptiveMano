# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2021-09-28 23:45
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webserver', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='monitorMemory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hostid', models.IntegerField(verbose_name='监控主机ID')),
                ('avai', models.CharField(max_length=20, verbose_name='空闲内存')),
                ('total', models.CharField(max_length=20, verbose_name='总内存')),
                ('ratio', models.CharField(max_length=20, verbose_name='使用率')),
                ('time', models.DateTimeField(auto_now_add=True, verbose_name='时间')),
            ],
        ),
    ]
