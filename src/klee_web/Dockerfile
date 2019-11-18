FROM python:3.8-buster

# Install Node.js, Ruby and other frontend tools
RUN curl -sL https://deb.nodesource.com/setup_12.x | bash -
RUN apt-get install -y ruby-full nodejs
RUN npm install -g bower grunt-cli
RUN gem install sass

COPY ./requirements.txt /
RUN pip install -r /requirements.txt
RUN rm /requirements.txt

WORKDIR /kleeweb
COPY . /kleeweb

RUN DEVELOPMENT=1 ./build.sh

CMD ./run.sh
