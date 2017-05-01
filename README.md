Klee Web
=======================
[Try it out here!](http://klee.doc.ic.ac.uk/#)

[![CircleCI](https://circleci.com/gh/klee/klee-web.svg?style=svg)](https://circleci.com/gh/klee/klee-web)

Getting started on development
===============================

Make sure you have [VirtualBox](https://www.virtualbox.org/wiki/Downloads), [Vagrant](https://www.vagrantup.com/downloads.html), and [Ansible](http://docs.ansible.com/intro_installation.html) installed, using the links in this paragraph.

First clone the repo:

    git clone --recursive https://github.com/klee/klee-web.git

Start the development virtual machine (this may take a while on the first run):

    vagrant up

If the command fails during provisioning, you can retry using:

    vagrant provision

After provisioning has completed, klee-web will be available at [http://192.168.33.10](http://192.168.33.10)

The [klee/klee](https://registry.hub.docker.com/u/klee/klee/) image is grabbed using docker pull when provisioning occurs.


In order to invoke KLEE (from within the virtual machine):

    sudo docker run -t -v PATH_TO_SOURCE_DIR:/code klee/klee clang -I /home/klee/klee_src/include/klee/include -emit-llvm -c -g /code/FILE.c -o /code/FILE.bc
    sudo docker run -t -v PATH_TO_SOURCE_DIR:/code klee/klee klee FILE.bc


In order to see any server side changes run (from within the virtual machine):

    sudo supervisorctl reload


Running tests
===========================
Before submitting a pull request it's a good idea to run our test suite locally with the following command

    $ vagrant ssh -c "/titb/run_tests.sh"


Building Frontend
===========================

Make sure you have Node and npm installed and that you are inside a machine with a deployed web role (e.g. after vagrant provision).

At the root-level directory:
  ```bash
$ npm install -g bower
$ npm install -g grunt-cli
  ```

Then:

	$ npm install

Now that Grunt and Bower are installed, install the front-end packages with


  $ bower install

Finally, let Grunt do the rest of the work (compiling/minifying SASS/JS etc), with

	$ grunt

------

To watch for changes when modifying SASS, use

	$ grunt watch

