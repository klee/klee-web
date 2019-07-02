# CHANGE THIS TO PYTHON IMAGE -> 3.7, choose the latest one. whatever is longest maintained.
FROM ubuntu:latest

# Install Python dependencies
RUN apt-get update
RUN apt-get --assume-yes install python3.6 ; update-alternatives --install /usr/bin/python3 \
    python3 /usr/bin/python3.6 1
RUN apt --assume-yes install python3-pip
COPY requirements.txt /titb/src/requirements.txt
WORKDIR /titb/src/
RUN pip3 install -r requirements.txt
RUN rm requirements.txt

RUN apt --assume-yes install docker.io
RUN apt install sudo

# create non-root user with sudo access
RUN useradd -r worker
RUN echo "worker ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

ARG environment
ARG python_runner
ARG klee_environment_path
ARG worker_path=/titb/src/worker
COPY ${environment} ${klee_environment_path}
COPY . ${worker_path}
COPY ${python_runner} ${worker_path}/${python_runner}

USER worker
