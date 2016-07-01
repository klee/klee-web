# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0003_project_default_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='current_output',
            field=models.TextField(null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='project',
            name='default_file',
            field=models.ForeignKey(related_name='default_project', blank=True, to='frontend.File', null=True),
            preserve_default=True,
        ),
    ]
