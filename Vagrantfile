# -*- mode: ruby -*-
# vi: set ft=ruby :
BOX_IMAGE = "ubuntu/bionic64"
WORKER_COUNT = 1
MASTER_IP = "192.168.33.10"
MASTER_NAME = "master"

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
    ansible.config_file       = "ansible.cfg"

    # make IP of master VM discoverable.
    ansible.host_vars = {
      MASTER_NAME => {"http_host" => MASTER_IP}
    }

    ansible.groups = {
      "master" => [MASTER_NAME],
      "worker" => ["worker-[1:#{WORKER_COUNT}]"],
      "testing" => ["testing"],
    }

    ansible.extra_vars = {ci: false}
    ansible.playbook          = "provisioning/vagrant.yml"
    ansible.galaxy_role_file  = "requirements.yml"
    # TODO(andronat): This path should been taken from ansible.cfg. This is a bug in Vagrant.
    ansible.galaxy_roles_path = "~/.ansible-galaxy"
    # ansible.verbose = "vvvv"

    # uncomment following line to only provision tasks with specified tags.
    # ansible.tags              = "deploy_container"
  end

  config.vm.define MASTER_NAME do |master|
    master.vm.box = BOX_IMAGE
    master.disksize.size = '30GB'
    master.vm.hostname = MASTER_NAME
    master.vm.network "private_network", ip: MASTER_IP
  end

  (1..WORKER_COUNT).each do |i|
    config.vm.define "worker-#{i}" do |subconfig|
      subconfig.vm.box = BOX_IMAGE
      subconfig.vm.hostname = "worker-#{i}"
      subconfig.vm.network "private_network", ip: "192.168.33.#{i + 10}"
    end
  end

  config.vm.define "testing" do |testing|
    testing.vm.box = BOX_IMAGE
    testing.vm.hostname = "testing"
    testing.vm.network "private_network", ip: "192.168.33.9"
  end

  config.vm.provider "virtualbox" do |v|
    v.memory = 2048
    v.cpus = 2
  end
end
