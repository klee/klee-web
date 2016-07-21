# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import json

from django.db import models, migrations

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
FIXTURE_DIR = os.path.join(BASE_DIR, '..', 'fixtures')


def load_fixtures(apps, schema_editor):
    fixtures_file = os.path.join(FIXTURE_DIR, 'fixtures.json')
    with open(fixtures_file) as fixtures_data:
        fixtures = json.loads(fixtures_data.read())    
        # Create example project
        add_fixtures(apps, fixtures, "Examples")
        # Create tutorial project
        add_fixtures(apps, fixtures, "Tutorials")


def add_fixtures(apps, fixtures, title):
    Project = apps.get_model("frontend", "Project")
    File = apps.get_model("frontend", "File")
            
    project = Project(name=title, example=True)
    project.save()
    for fixture in fixtures.get(title, []):
        figure = File(**fixture)
        code_path = os.path.join(FIXTURE_DIR, title, figure.name)
        with open(code_path, 'r') as code:
            figure.code = code.read()
        figure.project = project
        figure.save()


class Migration(migrations.Migration):
    dependencies = [
        ('frontend', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(load_fixtures)
    ]