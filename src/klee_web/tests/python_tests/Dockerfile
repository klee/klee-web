FROM python:3.6

# be able to launch docker
RUN curl -sSL https://get.docker.com/ | sh
RUN apt install sudo

# install python requirements
RUN pip install flake8
RUN pip install httpie
COPY src/klee_web/requirements.txt /requirements.txt
RUN pip install -r /requirements.txt && rm -f /requirements.txt

CMD /bin/bash /titb/src/klee_web/tests/python_tests/run_tests.sh 
