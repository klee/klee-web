FROM python:3.8-buster

# Install Node.js, Ruby and other frontend tools
RUN curl -sL https://deb.nodesource.com/setup_12.x | bash -
RUN apt-get install -y ruby-full nodejs
RUN npm install -g bower grunt-cli
RUN gem install sass

WORKDIR /titb/src/klee_web
COPY . /titb/src/klee_web

RUN pip install -r ./requirements.txt

ENV DEVELOPMENT=1
RUN ./build.sh

CMD ./build.sh \
  && python manage.py migrate --noinput \
  && python manage.py update_admin_user --username=admin --password=$ADMIN_PASSWORD \
  && uwsgi --master --uid www-data --gid www-data -s /tmp/uwsgi.sock -w wsgi:application --chmod-socket=666
