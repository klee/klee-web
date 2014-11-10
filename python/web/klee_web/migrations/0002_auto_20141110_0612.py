# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('klee_web', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='email_address',
            field=models.EmailField(max_length=75, null=True),
            preserve_default=True,
        ),
    ]
