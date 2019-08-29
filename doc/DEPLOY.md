Deployment to DoC Cloud
==========

## VM Creation

Login to cloudstack with the doc domain.
Create a new instance with the following details:
* Template: Ubuntu v14.04 30Gb (Non CSG)
* Compute offering	CPU: 2 cores 2GHz & RAM: 2Gb
* OS Type:	Ubuntu 14.04 (64-bit)

##### Note: RAM size can vary

Alternatively, speak to CSG to create this VM for you.

After the instance has been created correctly, note the hostname.
It will be in a format like cloud-vm-XX-YY.doc.ic.ac.uk
Where XX and YY are the penultimate and ultimate bytes of the IP address.

## VM Setup

* SSH into each VM from the Cloudstack console
* Add your SSH key (you can use a guide like [this](https://www.ssh.com/ssh/copy-id) to add the SSH key)
* Run `sudo visudo` and replace
```%sudo   ALL=(ALL:ALL) ALL```
with
```%sudo   ALL=(ALL:ALL) NOPASSWD: ALL```
##### Note: This step is done to allow sudoers to become other users without asking for password

## Deployment
* First, ensure that the code is up-to-date on the master branch of the main fork of this repository.
    * If you want to provision from another fork or another branch, open the `provisioning/group_vars/all` file and change the GitHub link on this line 
```bash
git_repo: https://github.com/klee/klee-web
```

* Open the file provisioning/hosts
* Add the VM hostname to all the roles you wish to be deployed on the VM in this format
```cloud-vm-XX-YY.doc.ic.ac.uk```
    * There should be only one hostname for the `master` and `testing` group, and at least one for the `worker` group.
* Add your imperial username as the Ansible ssh user
```bash
[all:vars]
# Change the user below to your imperial account
ansible_ssh_user=<your username>
```
* Run
```bash
$ ansible-galaxy install -r ./requirements.yml -f
$ ansible-playbook -i provisioning/hosts --vault-password-file=~/.klee_vault_password provisioning/production.yml -v
```

A more detailed introduction to how Ansible works is described in the `Ansible.md` file.

## Adding Workers
If the service becomes slow to respond you can add additional Workers. To do so 
* acquire a new VM from the DoC Cloud 
* set it up as in the steps above 
* add the new address to the provisioning/hosts file
* Reprovision the VMs with the above mentioned Ansible commands.

If you want to run more Worker container instances per Worker VM, see the *Changing the number of Worker container instances per Worker VM* header in the VAGRANT.md documentation file. This will not increase computing power but can increase concurrency in execution. 
