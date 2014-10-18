Testing in the browser
=======================

Getting started on development
===============================

Make sure you have virtualbox and vagrant installed.

First clone the repo:

    git clone https://github.com/ainsej/testing-in-the-browser.git
    
To ssh into the virtual machine:
   
    vagrant up
    vagrant ssh
    
To build the docker container:

    Keep note of the build number will be needed to run the image.
    
    #For a pre built image
    sudo docker pull ains/klee 
    #Or to build from scratch
    sudo docker build /titb/worker/klee/
    
To run a file inside the container:

(This isn't 100% correct will edit it shortly but still useful for now)

    sudo docker run -it -v PATH_TO_FILE:/code IMAGE bash
    llvm-gcc -I /src/klee/include --emit-llvm -c -g /code/FILE.c
    klee FILE.o
