#!/bin/bash

. /etc/profile.d/klee-web-environment.sh
cd /titb/src/klee_web
python manage.py update_admin_user --username=admin --password={{ admin_password }}
