#!/bin/bash
#

set -e

BIN_PATH=$(cd "$(dirname "$0")"; pwd -P)
WORK_PATH=${BIN_PATH}/../

# ansible real machine name: e41aa6eaa3e3

SSH_KEYS='
---start
fewensa
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAneSmM1VlnYEI2iLApYFQmzLt8hxAT9r2UgbgW/JdnC fewensa@mook
ansible
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINFvM1upegm161AR3yKzLTx90b6e0UHtWdeJEBDfYRP+ ansible@anxio
dokmana
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGGMDqrKslP5bqf9NNfoQCvzKpnXFQ8FvdqIMI8EydPe dokploy
coolia
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJe32WxuFcTNA5TkBK8BavwB8QoRcCmjE54/+OrKeT9d coolify-generated-ssh-key
---end
'

IFS=$'\n'

PROCESSING=false
FJUMP=1
USERNAME=
NEWUSER=false

for LINE in $SSH_KEYS; do
  if [ "${LINE}" == "---end" ]; then
    break
  fi
  if [ "${LINE}" == "---start" ]; then
    PROCESSING=true
    continue
  fi
  if [ "${PROCESSING}" == "false" ]; then
    continue
  fi

  if [ "${FJUMP}" == "1" ]; then
    USERNAME=${LINE}
    if id "$LINE" &>/dev/null; then
      NEWUSER=fasle
      echo "${LINE} exists"
    else
      useradd -m ${LINE}
      echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME
      mkdir -p /home/$USERNAME/.ssh
      NEWUSER=true
      echo 'created '${LINE}
    fi

    FJUMP=2
  else
    if [ "${NEWUSER}" == "true" ]; then
      echo ${LINE} >> /home/$USERNAME/.ssh/authorized_keys
      chown -R $USERNAME:$USERNAME /home/$USERNAME/.ssh/
      chmod 700 /home/$USERNAME/.ssh/
      chmod 600 /home/$USERNAME/.ssh/authorized_keys
    fi
    FJUMP=1
    USERNAME=''
    NEWUSER=fasle
  fi
done






## simple
#USERNAME=ansible
#useradd -m $USERNAME
#echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME
#
#mkdir -p /home/$USERNAME/.ssh
#echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOmRUFeLCn7z37pEENbyB4HHviSs5cM3sfBAh+GMRUe6 ansible@cntb' >> /home/$USERNAME/.ssh/authorized_keys
#
#chown -R $USERNAME:$USERNAME /home/$USERNAME/.ssh/
#chmod 700 /home/$USERNAME/.ssh/
#chmod 600 /home/$USERNAME/.ssh/authorized_keys
#


