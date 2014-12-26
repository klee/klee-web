# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0002_example'),
    ]

    operations = [
        migrations.AddField(
            model_name='example',
            name='max_stdin_args',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='example',
            name='min_stdin_args',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='example',
            name='num_files',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='example',
            name='size_files',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='example',
            name='size_stdin_args',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]
