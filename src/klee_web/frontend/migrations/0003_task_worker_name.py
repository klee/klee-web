# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0002_auto_20150106_0704'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='worker_name',
            field=models.CharField(default=b'', max_length=40),
            preserve_default=True,
        ),
    ]
