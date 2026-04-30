#cloud-config
autoinstall:
  version: 1
  locale: en_US.UTF-8
  keyboard:
    layout: us
  source:
    id: ubuntu-server-minimal
  storage:
    layout:
      name: direct
  network:
    network:
      version: 2
      ethernets:
        ens160:
          dhcp4: true
  user-data:
    package_upgrade: true
    packages:
      - openssh-server
      - python3
      - sudo
      - open-vm-tools
    users:
      - name: ${ssh_username}
        gecos: Management User
        groups: [sudo]
        lock_passwd: true
        shell: /bin/bash
        sudo: ALL=(ALL) NOPASSWD:ALL
        ssh_authorized_keys:
          - ${ssh_public_key}
  ssh:
    install-server: true
    allow-pw: false
  shutdown: reboot
