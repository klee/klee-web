FROM python:3.8-rc-buster

# Install Docker dependencies
RUN apt-get update
RUN apt --assume-yes install docker.io
RUN apt install sudo

# create non-root user with sudo access
RUN useradd -r worker
RUN echo "worker ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

COPY requirements.txt /titb/src/requirements.txt
WORKDIR /titb/src/
RUN pip install -r requirements.txt
RUN rm requirements.txt

CMD /src/python_runner.sh celery -l INFO -A worker.worker worker
