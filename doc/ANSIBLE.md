# Ansible

Ansible is used in this project to provision the VMs in production as well as in the development stage. This doc will give a quick overview of how a developer might interact with Ansible.

## Provisioning with Playbooks

An Ansible Playbook is the entry point for provisioning one or multiple VMs. For example, the playbook for the production environment exists in `provisioning/production.yml`.

To provision in production, you use the command

```bash
ansible-galaxy install -r ./requirements.yml -f

ansible-playbook -i provisioning/hosts --vault-password-file=~/.klee_vault_password provisioning/production.yml -v
```

The first command downloads some standardized playbooks onto your local machine. The second command specifies an inventory file, the location of the Ansible Vault password, and the Playbook.

Conveniently, provisioning in Ansible is idempotent and efficient. Even if you provision with the same playbook multiple times, Ansible only actually executes a task if it would change something in the VM.

### Inventory File

The inventory file allows grouping between the different VMs. It can look like this:

```bash
[master]
cloud-vm-41-210.doc.ic.ac.uk

[worker]
cloud-vm-40-70.doc.ic.ac.uk
cloud-vm-41-188.doc.ic.ac.uk

[testing]
cloud-vm-41-189.doc.ic.ac.uk

[all:vars]
ansible_ssh_user=<Your VM login username>
```

When provisioning, the rules can be applied to one or more groups in parallel. In this case, when provisioning the group `worker`, two VMs are provisioned at the same time. If you wanted to create three workers instead of only two, you could simply add a third URL in the `[worker]` group. This VM would need to be configured as pointed out in the DEPLOY.md documentation file.

### The Playbook

The playbook is what defines which hosts (according to the inventory file's groups) are provisioned and how.

```yml
- hosts: master
  remote_user: vagrant
  become: yes
  vars_files:
    - vars/secrets.yml
    - vars/master-prod.yml
    - vars/common.yml
  roles:
    - env_files
    - redis
    - db
    - web
```

This is a part of the `provisioning/production.yml` file. It specifies that the roles should only be executed on the `master` VMs, three variable files, and four roles should be used for provisioning.

### Variable Files

`vars_files` hold the variables for the Ansible tasks and offer a single place where variables can be held. This follows the [DRY](https://en.wikipedia.org/wiki/Don%27t_repeat_yourself) principle.

Variables can be substituted with the help of [Jinja2 templating](https://jinja.palletsprojects.com/en/2.10.x/).

### Roles

Roles hold the actual steps that are being used to provision the VMs. For example, in the `db` role the configuration files for the PostgreSQL database are created according to the variables in the vars_files. Then the custom PostgreSQL Docker image is built and run.

Roles offer a convenient way to group provisioning tasks.

### Only Running Specific Tags

Within the roles are different tags for specific tasks. For example, re-deploying a container always has the `deploy_container` tag. The task to pull the code from the GitHub repository is tagged with `pull_code`. If you wanted to pull the latest changes and restart the containers, without changing the dependencies, run

```bash
ansible-playbook -i provisioning/hosts --vault-password-file=~/.klee_vault_password provisioning/production.yml -v -t "deploy_container" -t "pull_code"
```

## Vault for Secrets

One convenient feature of Ansible is the **Ansible Vault**. It can keep files password encrypted so these files can be pushed onto GitHub safely.

One file with secret variables is the `provisioning/vars/secrets.yml` file. It holds secrets such as the PostgreSQL database passwords.

All you need to access these secrets is the password which you can get from the maintainers of this project. You can place the password within a file called `.klee_vault_password` into your home directory on your local machine. With the command

```bash
ansible-vault view --vault-password-file=~/.klee_vault_password provisioning/vars/secrets.yml
```

you can view the passwords. With

```bash
ansible-vault edit --vault-password-file=~/.klee_vault_password provisioning/vars/secrets.yml
```

you can amend them.
