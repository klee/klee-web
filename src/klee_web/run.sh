#!/bin/bash

set -e

python manage.py migrate --noinput
python manage.py update_admin_user --username=admin --password="$ADMIN_PASSWORD"
uwsgi --master --uid www-data --gid www-data -s /tmp/uwsgi.sock -w wsgi:application --chmod-socket=666
