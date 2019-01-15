# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/xenial64"

  # Create a private network, which allows host-only access to the machine
  # using a specific IP.
  config.vm.network "private_network", ip: "192.168.33.10"

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
    ansible.config_file       = "ansible.cfg"
    ansible.playbook          = "provisioning/vagrant.yml"
    ansible.galaxy_role_file  = "requirements.yml"
    # TODO(andronat): This path should been taken from ansible.cfg. This is a bug in Vagrant.
    ansible.galaxy_roles_path = "~/.ansible-galaxy"
    # ansible.verbose = "vvvv"
  end

  config.vm.provider "virtualbox" do |v|
    v.memory = 2048
    v.cpus = 2
  end
end
