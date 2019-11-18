# -*- mode: ruby -*-
# vi: set ft=ruby :

BOX_IMAGE = "ubuntu/bionic64"
MASTER_IP = "192.168.33.10"

Vagrant.configure("2") do |config|

  config.ssh.forward_agent = true

  # Share an additional folder to the guest VM. The first argument is
  # the path on the host to the actual folder. The second argument is
  # the path on the guest to mount the folder. And the optional third
  # argument is a set of non-required options.
  config.vm.synced_folder ".", "/titb",
    owner: "vagrant",
    group: "www-data",
    mount_options: ["dmode=777,fmode=777"]

  config.vm.provision "ansible" do |ansible|
    ansible.config_file = "ansible.cfg"

    ansible.groups = {
      "master" => ["master-vm"],
      "workers" => ["worker-vm"],
      "testing" => ["testing-vm"],
      "vagrant:children" => ["master", "workers", "testing"],
      "vagrant:vars" => {"master_ip" => MASTER_IP},
    }

    ansible.playbook          = "provisioning/vagrant.yml"
    ansible.galaxy_role_file  = "requirements.yml"
    # TODO(andronat): This path should been taken from ansible.cfg. This is a bug in Vagrant.
    ansible.galaxy_roles_path = "~/.ansible-galaxy"
    # ansible.verbose = "vvvv"

    # uncomment following line to only provision tasks with specified tags.
    # ansible.tags              = "deploy_container"
  end

  config.vm.define "master-vm" do |master|
    master.vm.box = BOX_IMAGE
    master.disksize.size = '30GB'
    master.vm.hostname = "master-vm"
    master.vm.network "private_network", ip: MASTER_IP
  end

  config.vm.define "worker-vm" do |subconfig|
    subconfig.vm.box = BOX_IMAGE
    subconfig.vm.hostname = "worker-vm"
    subconfig.vm.network "private_network", ip: "192.168.33.11"
  end

  config.vm.provider "virtualbox" do |v|
    v.memory = 2048
    v.cpus = 2
  end
end
