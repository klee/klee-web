FROM python:3.8-rc-buster

# be able to launch docker
RUN curl -sSL https://get.docker.com/ | sh
RUN apt install sudo

# install python requirements
RUN pip install flake8
RUN pip install httpie
COPY ./requirements.txt /requirements.txt
RUN pip install -r /requirements.txt && rm -f /requirements.txt
