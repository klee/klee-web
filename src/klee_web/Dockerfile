FROM python:3.8-buster

# Install Node.js, Ruby and other frontend tools
RUN curl -sL https://deb.nodesource.com/setup_12.x | bash -
RUN apt-get install -y ruby-full nodejs
RUN npm install grunt grunt-contrib-sass grunt-contrib-watch grunt-contrib-copy grunt-contrib-concat grunt-contrib-uglify
RUN npm install -g bower grunt-cli
RUN gem install sass

WORKDIR /klee_web
COPY . /klee_web

# Download geoip
RUN mkdir geoip
RUN wget -q -P ./geoip/ https://geolite.maxmind.com/download/geoip/database/GeoLite2-City.mmdb.gz
RUN wget -q -P ./geoip/ https://geolite.maxmind.com/download/geoip/database/GeoLite2-Country.mmdb.gz
RUN gunzip -f ./geoip/GeoLite2-City.mmdb.gz
RUN gunzip -f ./geoip/GeoLite2-Country.mmdb.gz

# Install NPM, Bower and Python dependences
RUN npm install
RUN pip install -r ./requirements.txt
RUN bower install --config.interactive=false --allow-root

# Build web assets with Grunt
RUN grunt

CMD python manage.py collectstatic --noinput && \
  python manage.py migrate --noinput && \
  python manage.py update_admin_user --username=admin --password=${ADMIN_PASSWORD} && \
  uwsgi --master --uid www-data --gid www-data -s /tmp/uwsgi.sock -w wsgi:application --chmod-socket=666
