#!/bin/bash

# don't ask me no questions and I won't tell you no lies 
export DEBIAN_FRONTEND=noninteractive

# import PGP keys
gpg --keyserver  hkp://keys.gnupg.net --recv-keys 1C4CBDCDCD2EFD2A
gpg -a --export CD2EFD2A | apt-key add -

# set up the percona repo
echo "deb http://repo.percona.com/apt lucid main
deb-src http://repo.percona.com/apt lucid main" >/etc/apt/sources.list.d/percona.list

apt-get update
apt-get --force-yes --yes install percona-server-common-5.5  percona-server-server-5.5 percona-server-test-5.5  percona-server-client-5.5 libmysqlclient18  libmysqlclient-dev xtrabackup

# change root password
/usr/bin/mysqladmin -u root password hpcs

# now shut down
/etc/init.d/mysql stop

# we will be moving this to a new mount point
mv /var/lib/mysql /var/lib/mysql.bak

# copy stock my.cnf
echo "[mysqld]
user=mysql

datadir=/var/lib/mysql

innodb_buffer_pool_size=2G
innodb_log_file_size=100M
innodb_file_per_table 
" > /etc/mysql/my.cnf

# remove innodb log file since log file size is changed
rm /var/lib/mysql.bak/ib_logfile*

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

# install lvm
apt-get -y install lvm2

# creat physical volume
pvcreate /dev/vdb1

# create volume group
vgcreate data /dev/vdb1

# create logical volume - this needs to be changed to account for flavor (size)
lvcreate --size 100G --name mysql-data data

# install xfs utils
apt-get -y install xfsprogs xfsdump

# format
mkfs.xfs /dev/data/mysql-data

# create mount point
mkdir /var/lib/mysql

# change ownership
chown mysql:mysql /var/lib/mysql

# get mount point into fstab
echo -e "\n/dev/data/mysql-data\t/var/lib/mysql\txfs\tdefaults\t0\t0\n" >> /etc/fstab

# mount
mount -a 
 
# copy data
cp -a /var/lib/mysql.bak/* /var/lib/mysql/

# ensure ownership
chown -R mysql:mysql /var/lib/mysql

# start
/etc/init.d/mysql start

# this WILL be dynamic
/usr/bin/mysql -u root -phpcs -e "grant all privileges on *.* to 'root'@'%' identified by 'hpcs' with grant option;"

# change root/admin password
/usr/bin/mysqladmin -u root password hpcs 
# create agent DB account
# TODO: get privileges set up so agent can't read user, vice versa
/usr/bin/mysql -u root -phpcs -e "grant all privileges on *.* to 'os_admin'@'localhost' identified by 'hpcs' with grant option;"
# create user account. TODO: this will be passed via the API
/usr/bin/mysql -u root -phpcs -e "grant all privileges on *.* to 'dbas'@'%' identified by 'hpcs' with grant option;"

apt-get install -qqy git
gid="$(getent passwd mysql | cut -f4 -d:)"
useradd -m -g $gid nova
cd /home/nova
sudo mkdir lock
sudo mkdir logs

mkdir /var/lib/mysql-backup
chown nova:mysql /var/lib/mysql-backup

sudo git clone https://github.com/hpcloud/reddwarf.git

chown nova:mysql -R /home/nova/

# Create a .my.cnf for the Agent
echo "[client]
user=os_admin
password=hpcs
" > /home/nova/.my.cnf

echo 'export PYTHONPATH=/home/nova/reddwarf/swiftapi' >> /root/.bashrc
source /root/.bashrc

ln -s /home/nova/.my.cnf /root/.my.cnf

######## TEMPORARY agent.config file ########
#echo "[messaging]
#rabbit_host: 15.185.163.167
#
#[database]
#initial_password: hpcs
#" > /home/nova/agent.config
##########################

apt-get install -qqy python-pip python-dev
pip install pika
pip install mysql-python
pip install swift
pip install --upgrade python-daemon
cd reddwarf
ln -s /home/nova/reddwarf/smartagent/smartagent_launcher.py /etc/init.d/smartagent
sudo /etc/init.d/smartagent start
