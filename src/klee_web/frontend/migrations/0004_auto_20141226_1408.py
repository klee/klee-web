# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0003_auto_20141226_1325'),
    ]

    operations = [
        migrations.AddField(
            model_name='example',
            name='last_modified',
            field=models.DateTimeField(default=datetime.datetime(2014, 12, 26, 14, 8, 51, 552868), auto_now=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='example',
            name='max_stdin_args',
            field=models.IntegerField(default=0),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='example',
            name='min_stdin_args',
            field=models.IntegerField(default=0),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='example',
            name='num_files',
            field=models.IntegerField(default=0),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='example',
            name='size_files',
            field=models.IntegerField(default=0),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='example',
            name='size_stdin_args',
            field=models.IntegerField(default=0),
            preserve_default=True,
        ),
    ]
