#!/bin/bash

# stop mysql
service mysql stop

# back up data directory
mv /var/lib/mysql /var/lib/mysql.bak

# partition, set as LVM
# this WILL be dynamic/generated depending on what hosts the user wants to allow, for now we open wide
fdisk /dev/vdb <<EOF
n
p
1


t
8e
w
EOF

# creat physical volume
pvcreate /dev/vdb1

# create volume group
vgcreate data /dev/vdb1

# create logical volume - this needs to be changed to account for flavor (size)
lvcreate --size 20G --name mysql-data data

# format
mkfs.xfs /dev/data/mysql-data

# create mount point
mkdir /var/lib/mysql

# copy data from backup
cp -a /var/lib/mysql.bak /var/lib/mysql

# change ownership
chown mysql:mysql /var/lib/mysql

# get mount point into fstab
echo -e "\n/dev/data/mysql-data\t/var/lib/mysql\txfs\tdefaults\t0\t0\n" >> /etc/fstab

# mount
mount -a 
 
# start
/etc/init.d/mysql start

cd /home/nova
sudo git clone https://github.com/hpcloud/reddwarf.git
cp /home/nova/reddwarf/smartagent/startup/disk_prep /etc/init.d
cp /home/nova/reddwarf/smartagent/startup/smartagent /etc/init.d
cp /home/nova/reddwarf/smartagent/startup/mysql.conf /etc/init.d
cp /home/nova/reddwarf/smartagent/startup/sudoers /etc
update-rc.d disk_prep defaults 85
update-rc.d smart_agent defaults 90

# make sure nova owns
chown -R nova:mysql /home/nova

######## TEMPORARY agent.config file ########
#echo "[messaging]
#rabbit_host: 15.185.163.167
#
#[database]
#initial_password: hpcs
#" > /home/nova/agent.config
##########################

cd reddwarf
ln -s /home/nova/reddwarf/smartagent/smartagent_launcher.py /etc/init.d/smartagent
sudo /etc/init.d/smartagent start
