#!/bin/bash

# make sure emphemeral is NOT mounted
umount /dev/vdb
umount /mnt

# stop mysql.
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

# get mount point into fstab
echo -e "\n/dev/data/mysql-data\t/var/lib/mysql\txfs\tdefaults\t0\t0\n" >> /etc/fstab

# create mount point
mkdir /var/lib/mysql

# mount
mount -a 

# copy data from backup
cp -a /var/lib/mysql.bak/* /var/lib/mysql

# change ownership
chown mysql:mysql /var/lib/mysql

# start
service mysql start

cd /home/nova/reddwarf
git pull
git checkout 0.4.0

######## TEMPORARY agent.config file ########
#echo "[messaging]
#rabbit_host: 15.185.163.167
#
#[database]
#initial_password: hpcs
#" > /home/nova/agent.config
##########################

sudo /etc/init.d/smartagent start
