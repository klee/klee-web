# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0002_auto_20150106_0704'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='default_file',
            field=models.ForeignKey(related_name='default_project', to='frontend.File', null=True),
            preserve_default=True,
        ),
    ]
