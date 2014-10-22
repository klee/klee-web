Testing in the browser
=======================

Getting started on development
===============================

Make sure you have virtualbox and vagrant installed.

First clone the repo:

    git clone https://github.com/klee-web/klee-web.git
    
To ssh into the virtual machine:
   
    vagrant up
    vagrant ssh
    
To build the docker container:

    Keep note of the build number will be needed to run the image.
    
    #For a pre built image
    sudo docker pull kleeweb/klee 
    #Or to build from scratch
    sudo docker build /titb/python/worker/klee/
    
To run a file inside the container:

    sudo docker run -it -v PATH_TO_FILE:/code IMAGE bash
    llvm-gcc -I /src/klee/include --emit-llvm -c -g /code/FILE.c
    klee FILE.o
