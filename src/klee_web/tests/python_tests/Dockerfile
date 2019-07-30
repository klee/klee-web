FROM python:3.6

# install python tests
RUN pip install flake8
RUN pip install httpie

COPY src/klee_web/ /titb/src/klee_web
COPY run_tests.sh /titb/
# WORKDIR /titb/src/klee_web/tests/python_tests

# ## be able to launch docker
RUN curl -sSL https://get.docker.com/ | sh
RUN apt install sudo

WORKDIR /titb
RUN pip install -r src/klee_web/requirements.txt

CMD /bin/bash src/klee_web/tests/python_tests/run_tests.sh 

# TODO: the actual tests should probably NOT be copied in 
# HOWEVER, this will be tricky as the tests are in multiple locations.
    # could only copy the requirements file, and have the rest as a volume! 
    # can even delete the requirements file right after installation!
