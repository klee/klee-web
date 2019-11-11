FROM python:3.8-rc-buster

# NOTES: no klee or klide user created.
# ---- WEB INSTALLATIONS ----
WORKDIR /titb
RUN mkdir geoip

# Download geoip 
RUN wget -P ./geoip/ https://geolite.maxmind.com/download/geoip/database/GeoLite2-City.mmdb.gz
RUN wget -P ./geoip/ https://geolite.maxmind.com/download/geoip/database/GeoLite2-Country.mmdb.gz
RUN gunzip -f ./geoip/GeoLite2-City.mmdb.gz
RUN gunzip -f ./geoip/GeoLite2-Country.mmdb.gz

RUN mkdir -p /src/web/logs

# ---- FRONTEND INSTALLATIONS ----
RUN apt-get update
RUN apt install sudo
RUN curl -sL https://deb.nodesource.com/setup_12.x | sudo -E bash -
RUN apt-get install -y nodejs
RUN npm install -g grunt-cli
# WORKDIR /titb
RUN npm install grunt
RUN npm install grunt-contrib-sass
RUN npm install grunt-contrib-watch
RUN npm install grunt-contrib-copy
RUN npm install grunt-contrib-concat
RUN npm install grunt-contrib-uglify
RUN npm install -g bower
COPY ./.bowerrc ./Gruntfile.js ./bower.json ./package.json \
     ./package-lock.json ./requirements.txt /titb/

RUN npm install 
RUN apt install -y ruby-full
RUN gem install sass

# ---- DEPLOY INSTALLATIONS ----
RUN pip install -r /titb/requirements.txt

CMD bower install --config.interactive=false --allow-root && \
    grunt && \
    rm -rf ./src/klee_web/geoip/ && \
    cp -r -f ./geoip/ ./src/klee_web/ && \
    . /etc/profile.d/klee-web-environment.sh && cd /titb/src/klee_web && \
    python manage.py migrate --noinput && \
    python manage.py collectstatic --noinput && \
    . /src/web/admin_psw.sh && \
    uwsgi -s /tmp/uwsgi.sock -w wsgi:application --chmod-socket=666
