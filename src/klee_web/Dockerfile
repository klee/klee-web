FROM python:3.6

# ---- WEB INSTALLATIONS ----
WORKDIR /titb/src
RUN mkdir klee_web && mkdir geoip

# Download geoip 
RUN wget -P ./geoip/ https://geolite.maxmind.com/download/geoip/database/GeoLite2-City.mmdb.gz
RUN wget -P ./geoip/ https://geolite.maxmind.com/download/geoip/database/GeoLite2-Country.mmdb.gz
RUN gunzip -f ./geoip/GeoLite2-City.mmdb.gz
RUN gunzip -f ./geoip/GeoLite2-Country.mmdb.gz

# create web user  --> maybe move this before starting the application.
# RUN useradd -r klee_web
# USER klee_web
# maybe remove these folders later, but for now create the web folders:
RUN mkdir -p /src/web/logs

# ---- FRONTEND INSTALLATIONS ----
RUN apt-get update
RUN apt install sudo
# TODO: possibly add env variable for when to do this command.
RUN curl -sL https://deb.nodesource.com/setup_6.x | sudo -E bash -
RUN apt install nodejs
# RUN npm install npm@latest -g  # LEAVE THIS OUT?
RUN npm install -g grunt-cli
WORKDIR /titb
RUN npm install grunt
RUN npm install grunt-contrib-sass
RUN npm install grunt-contrib-watch
RUN npm install grunt-contrib-copy
RUN npm install grunt-contrib-concat
RUN npm install grunt-contrib-uglify
RUN npm install -g bower
COPY .bowerrc Gruntfile.js bower.json package.json package-lock.json requirements.txt /titb/
# TODO: delete the above files from the Docker /titb/src/klee_web folder
COPY . /titb/src/klee_web
RUN npm install 

# WILL MAYBE BREAK RUBY
RUN apt install -y ruby-full
RUN gem install sass

# ---- NGINX INSTALLATIONS ??? skip?? ----

# ---- DEPLOY INSTALLATIONS ----
RUN pip install -r /titb/requirements.txt
COPY admin_psw.sh /src/web
# RUN useradd -r -s /bin/bash klide
# USER klide
# NOTE: these differ between ci and no ci
RUN bower install --config.interactive=false --allow-root
RUN grunt
# # TODO: maybe make ARG for application_dir

# TODO: remove this after testing and add the klee-web-environment like with worker
COPY admin_psw.sh /src/web/admin_psw.sh
COPY environment_dev.sh /etc/profile.d/klee-web-environment.sh

# TODO maybe move this line up somewhere -> find better way to copy worker
COPY worker /titb/src/
# RUN . /etc/profile.d/klee-web-environment.sh && cd /titb/src/klee_web && python manage.py migrate --noinput

# RUN . /etc/profile.d/klee-web-environment.sh && cd /titb/src/klee_web && python manage.py collectstatic --noinput
# RUN . /src/web/admin_psw.sh
# START THE APPLICATION WITHOUT SUPERVISOR!




# TODO: need to copy the python runner file and run the application!

