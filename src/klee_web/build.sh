#!/bin/bash

set -e

CUR_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Download geoip
mkdir -p "${CUR_DIR}/geoip"
wget -q -P "${CUR_DIR}/geoip" https://geolite.maxmind.com/download/geoip/database/GeoLite2-City.mmdb.gz
wget -q -P "${CUR_DIR}/geoip" https://geolite.maxmind.com/download/geoip/database/GeoLite2-Country.mmdb.gz
gunzip -f "${CUR_DIR}/geoip/GeoLite2-City.mmdb.gz"
gunzip -f "${CUR_DIR}/geoip/GeoLite2-Country.mmdb.gz"

npm install
bower install --config.interactive=false --allow-root
grunt
python manage.py collectstatic --noinput
