# Vagrant

Vagrant is used to create VMs on the local machine which mirror the production environment as closely as possible.

Currently, there is one **Master** VM, at least one **Worker** VM, and one **Testing** VM in production. This architecture is mirrored by Vagrant on the local machine.

## Starting Vagrant

```bash
vagrant up
```

This is the command to start the VMs for the first time. It will read the `Vagrantfile` in the root directory and create all the necessary VMs and also provision them.

```yml
  config.vm.synced_folder ".", "/titb",
    owner: "vagrant",
    group: "www-data",
    mount_options: ["dmode=777,fmode=777"]
```

These lines within the Vagrantfile ensure that the source code is copied into the VMs and also synchronised. This is convenient as it enables the developer to make changes in the code on the local machine which are immediately reflected in the code within the VMs.

The Ansible Playbook that is being used to provision the machines is specified here:

```yml
ansible.playbook          = "provisioning/vagrant.yml"
```

It is also possible to use a different playbook for provisioning.

## Reprovisioning After Changes to the Code

Once the code has been updated locally, it is not necessary to restart the entire VM. You can reprovision the running VMs with:

```bash
vagrant provision
```

If the code that has changed only concerns e.g. the Master VM, you can specify to only provision this VM with

```bash
vagrant provision master
```

This will also work with the Worker (here use `worker1`, `worker2`, ...) and the Testing VM. Specifying isolated VMs will work with every vagrant command which is mentioned in this documentation.

Ansible has a tagging system. You can only provision specific Ansible rules with specific tags. For example, to only restart the Docker containers uncomment the following line:

```yml
ansible.tags              = "deploy_container"
```

If you made changes to the `Vagrantfile` outside of the

```yml
config.vm.provision "ansible" do |ansible|
```

scope you need to run:

```bash
vagrant reload
```

to reflect the changes in the VMs. This can be useful e.g. when you want to turn off the `config.vm.synced_folder` option. Delete the required lines and reload the VMs. Most of the time the command `vagrant provision` does the necessary changes to the VM without requiring a `vagrant reload`.

## Debugging a Vagrant VM

To debug a VM or access the logs you ssh into the VMs by running:

```bash
vagrant ssh <VM-name>
```

## Destroying Vagrant VMs

To destroy the vagrant VMs simply run

```bash
vagrant destroy -f
```

Sometimes it is worth to destroy the VM and restarting it completely to test functionalities before pushing to production.

## Increasing the Number of Worker VMs

The biggest computational bottleneck in the Klee Web application is running the KLEE application on the submitted code. This is managed by the Workers which can be scaled up and down flexibly in production.

There are two ways to scale the number of Workers:

- Increase the number of Worker VMs
- Increase the number of running Worker containers within each Worker VM.

### Changing the number of Worker VMs

In the development environment, this is simply done by changing this line in the `Vagrantfile`:

```yml
WORKER_COUNT = 1
```

Then the new Workers need to be created with `vagrant up` as described above. Once provisioned, they will automatically register themselves without any changes to the Master VM.

In production, you would need to create the VM and provision it as well. Please refer to the DEPLOY.md documentation.

### Changing the number of Worker container instances per Worker VM

Alternative to creating new VMs, you can also try out to have more Worker instances within each VM. This will not change the overall computing power, but the concurrency will be increased.

To do that you need to change the provisioning rule for the Worker within `provisioning/roles/worker/defaults/main.yml`.

```yml
number_of_workers: 2
```

To scale the running instances of Workers change the number of workers to any positive number greater or equal to 1.

After the change, reprovision the VMs with

```bash
vagrant provision
```

### Test It Out!

You can quickly test what difference it makes to have one Worker or multiple instances of Workers running. Open the website at [192.168.33.10](http://192.168.33.10) in multiple tabs. Run the `regexp.c` example on all the tabs at the same time with only one Worker running on one Worker VM.

Then, try to either create more Worker VMs or run more Worker instances per Worker VM and repeat the test. You should notice an increase in the parallel execution of the task.

## Provisioning Like in the Production Environment

You can create local VMs with the same Ansible Playbook, environmental variables, and secrets as in the production environment. To do so comment out the folder synchronisation

```yml
# config.vm.synced_folder ".", "/titb",
#   owner: "vagrant",
#   group: "www-data",
#   mount_options: ["dmode=777,fmode=777"]
```

This is important as in production there is no synchronisation of folders either. Instead, the code is pulled from the master branch of the klee-web GitHub repository.

Use the production Ansible Playbook for provisioning and require to ask for the Ansible Vault password.

```yml
ansible.playbook          = "provisioning/production.yml"
ansible.ask_vault_pass    = true
# ansible.playbook          = "provisioning/vagrant.yml"
```

It is best to destroy the VM and restart them

```bash
vagrant destroy -f
vagrant up
```

You will be prompted for the Ansible Vault password, which you can take from the `~/.klee_vault_password` file in your root directory. If you do not have such a file you can get it from the maintainers of Klee Web.

Doing this can give you additional reassurance to test the application before pushing the code and restarting the production environment.

Please note that before provisioning the production environment you need to either have all the updates pushed onto the main fork's master branch or change the variable `git_repo` within the `/provisioning/group_vars/all` file to specify the URL to your GitHub fork.
