# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import json

from django.db import models, migrations

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
FIXTURE_DIR = os.path.join(BASE_DIR, '..', 'fixtures')


def load_example_fixtures(apps, schema_editor):
    Project = apps.get_model("frontend", "Project")
    File = apps.get_model("frontend", "File")

    # Create example project
    project = Project(name="Examples", example=True)
    project.save()

    # Load example figures
    example_file = os.path.join(FIXTURE_DIR, 'examples.json')
    with open(example_file) as example_data:
        examples = json.loads(example_data.read())
        for fixture in examples.get('examples', []):
            example = File(**fixture)
            example.project = project
            example.save()


class Migration(migrations.Migration):
    dependencies = [
        ('frontend', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(load_example_fixtures)
    ]
