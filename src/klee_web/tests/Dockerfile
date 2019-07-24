FROM python:3.6

# install python tests
RUN pip install flake8
RUN pip install httpie

# # install JS E2E tests
COPY src/klee_web/ /titb/src/klee_web
COPY run_tests.sh /titb/
WORKDIR /titb/src/klee_web/tests

# ## be able to launch docker
RUN curl -sSL https://get.docker.com/ | sh
RUN apt install sudo

WORKDIR /titb
RUN pip install -r src/klee_web/requirements.txt

CMD /bin/bash src/klee_web/tests/run_tests.sh 
