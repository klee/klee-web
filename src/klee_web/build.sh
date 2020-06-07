#!/bin/bash

set -e

CUR_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

echo "Running flake8"
flake8 --extend-ignore=E722 --max-complexity 12 --exclude=migrations "${CUR_DIR}"

VERSION="20200602"
CITY="GeoLite2-City"
COUNTRY="GeoLite2-Country"

echo "Unzipping GeoIP"
cd "geoip"
tar xzf "${CUR_DIR}/geoip/${CITY}_${VERSION}.tar.gz"
tar xzf "${CUR_DIR}/geoip/${COUNTRY}_${VERSION}.tar.gz"
mv "${CUR_DIR}/geoip/${CITY}_${VERSION}/${CITY}.mmdb" "${CUR_DIR}/geoip/${COUNTRY}_${VERSION}/${COUNTRY}.mmdb" "${CUR_DIR}/geoip"
cd ..

npm install
bower install --config.interactive=false --allow-root
grunt
python manage.py collectstatic --noinput
