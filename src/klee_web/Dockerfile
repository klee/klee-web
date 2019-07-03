FROM python:3.6

# NOTES: no klee or klide user created.
# ---- WEB INSTALLATIONS ----
WORKDIR /titb/src
RUN mkdir klee_web && mkdir geoip

# Download geoip 
RUN wget -P ./geoip/ https://geolite.maxmind.com/download/geoip/database/GeoLite2-City.mmdb.gz
RUN wget -P ./geoip/ https://geolite.maxmind.com/download/geoip/database/GeoLite2-Country.mmdb.gz
RUN gunzip -f ./geoip/GeoLite2-City.mmdb.gz
RUN gunzip -f ./geoip/GeoLite2-Country.mmdb.gz

RUN mkdir -p /src/web/logs

# ---- FRONTEND INSTALLATIONS ----
RUN apt-get update
RUN apt install sudo
RUN curl -sL https://deb.nodesource.com/setup_6.x | sudo -E bash -
RUN apt install nodejs
RUN npm install -g grunt-cli
WORKDIR /titb
RUN npm install grunt
RUN npm install grunt-contrib-sass
RUN npm install grunt-contrib-watch
RUN npm install grunt-contrib-copy
RUN npm install grunt-contrib-concat
RUN npm install grunt-contrib-uglify
RUN npm install -g bower
COPY ./klee_web/.bowerrc ./klee_web/Gruntfile.js ./klee_web/bower.json ./klee_web/package.json \
     ./klee_web/package-lock.json ./klee_web/requirements.txt /titb/
COPY ./klee_web /titb/src/klee_web
RUN npm install 
RUN apt install -y ruby-full
RUN gem install sass

# ---- DEPLOY INSTALLATIONS ----
RUN pip install -r /titb/requirements.txt

# NOTE: these differ between ci and no ci
RUN bower install --config.interactive=false --allow-root
RUN grunt
COPY ./klee_web/admin_psw.sh /src/web/admin_psw.sh
COPY ./klee_web/klee-web-environment.sh /etc/profile.d/klee-web-environment.sh
COPY ./worker /titb/src/worker

CMD . /etc/profile.d/klee-web-environment.sh && cd /titb/src/klee_web && \
    python manage.py migrate --noinput && \
    python manage.py collectstatic --noinput && \
    . /src/web/admin_psw.sh && \
    uwsgi -s /tmp/uwsgi.sock -w wsgi:application --chmod-socket=666
