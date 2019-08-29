Klee Web
=======================
[Try it out here!](http://klee.doc.ic.ac.uk/#)

[![CircleCI](https://circleci.com/gh/klee/klee-web.svg?style=svg)](https://circleci.com/gh/klee/klee-web)

Getting started on development
===============================

Make sure you have [VirtualBox](https://www.virtualbox.org/wiki/Downloads), [Vagrant](https://www.vagrantup.com/downloads.html), and [Ansible](http://docs.ansible.com/intro_installation.html) installed, using the links in this paragraph.

First clone the repo:

    git clone https://github.com/klee/klee-web.git

Install the necessary vagrant plugins:

    vagrant plugin install vagrant-disksize

Start the development virtual machine (this may take a while on the first run):

    vagrant up

If the command fails during provisioning, you can retry using:

    vagrant provision

After provisioning has completed, klee-web will be available at [http://192.168.33.10](http://192.168.33.10)

The [klee/klee](https://registry.hub.docker.com/u/klee/klee/) image is grabbed using docker pull when provisioning occurs.


In order to invoke KLEE (from within the virtual machine):

    sudo docker run -t -v PATH_TO_SOURCE_DIR:/code klee/klee clang -I /home/klee/klee_src/include/klee/include -emit-llvm -c -g /code/FILE.c -o /code/FILE.bc
    sudo docker run -t -v PATH_TO_SOURCE_DIR:/code klee/klee klee FILE.bc


In order to see any server side changes provision the machines again with:

    vagrant provision

A more detailed documentation on how to interact with Vagrant is provided in `doc/VAGRANT.md`.




Running tests
===========================
Before submitting a pull request it's a good idea to run our test suite locally.

To run the Flake8 and Javascript end-to-end tests run:

    $ vagrant ssh testing -c "/titb/run_global_tests.sh"

To run the Worker service unit tests run:

    $ vagrant ssh worker1 -c "/titb/run_unit_tests.sh"

Circle CI
=======

Circle CI is being used to run tests for commits before they get merged into the master branch on the main fork. 

It is important to understand that within the Circle CI testing VM there is only one VM overall where all processes run. This is different from the development and production environment where the application is distributed accross multipe VMs. Other than that it runs with the same Ansible Playbook as in the development stage. 

The provisioning of the Circle CI VM and the tests that are run can be found in the `.circleci/config.yml` file. 

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

Debugging Dockerized Services
===========================
The `doc/DEBUGGING_DOCKER.md` file holds a detailed discussion on best practices for working with dockerized services and tips for debugging Docker containers. 

Deploying to Production
===========================
Deployment is further explained in the `doc/DEPLOY.md` file.


Receiving Automated Production Status Emails
===========================
How to configure the automated emails is explained in the `doc/EMAIL_NOTIFICATIONS.ms` file.
