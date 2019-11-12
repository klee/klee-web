FROM python:3.8-buster

# Install Docker dependencies
RUN apt-get update
RUN apt-get install -y sudo docker.io

# Create non-root user with sudo access
RUN useradd -r worker
RUN echo "worker ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

WORKDIR /worker
COPY . /worker/worker
RUN pip install -r ./worker/requirements.txt

CMD celery worker --app worker.worker --loglevel=info
