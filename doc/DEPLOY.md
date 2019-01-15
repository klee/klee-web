Deployment to DoC Cloud
==========

## VM Creation

Login to cloudstack with the doc domain
Create a new instance with the following details:
* Template: Ubuntu v14.04 30Gb (Non CSG)
* Compute offering	CPU: 2 cores 2GHz & RAM: 2Gb
* OS Type:	Ubuntu 14.04 (64-bit)

##### Note: RAM size can vary

After the instance has been created correctly, note the hostname
It will be in a format like cloud-vm-XX-YY.doc.ic.ac.uk
Where XX and YY are the penultimate and ultimate bytes of the IP address.

## VM Setup

* SSH into the VM from the Cloudstack console
* Create a user named Ubuntu
```bash
adduser --ingroup sudo ubuntu
```
* Login ubuntu and add your SSH key to ease the login process for ansible
* Run `sudo visudo` and replace
```%sudo ALL=NOPASSWD: ALL```
with
```%sudo ALL=(ALL) NOPASSWD: ALL```
##### Note: This step is done to allow sudoers to become other users without asking for password

## Deployment
* Open the file provisioning/hosts
* Add the VM hostname to all the roles you wish to be deployed on the VM in this format
```cloud-vm-XX-YY.doc.ic.ac.uk:22 ansible_ssh_user=ubuntu```
* Run
```bash
ansible-galaxy install -r ./requirements.yml -f
ansible-playbook -i provisioning/hosts --vault-password-file=~/.klee_vault_password provisioning/production.yml -v
```
