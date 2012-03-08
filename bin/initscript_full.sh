#!/bin/bash

# this does *everything*, builds a fully-stocked image

# don't ask me no questions and I won't tell you no lies 
export DEBIAN_FRONTEND=noninteractive

# import PGP keys
gpg --keyserver  hkp://keys.gnupg.net --recv-keys 1C4CBDCDCD2EFD2A
gpg -a --export CD2EFD2A | apt-key add -

# set up the percona repo
echo "deb http://repo.percona.com/apt lucid main
deb-src http://repo.percona.com/apt lucid main" >/etc/apt/sources.list.d/percona.list

apt-get update
apt-get --force-yes -y install xfsprogs xfsdump
apt-get --force-yes --yes install percona-server-common-5.5  percona-server-server-5.5 percona-server-test-5.5  percona-server-client-5.5 libmysqlclient18  libmysqlclient-dev xtrabackup
apt-get --force-yes --yes install python-swift swift policycoreutils python-mysqldb python-nova libdbd-mysql-perl libdbi-perl python-pip python-dev
apt-get install -qqy git
apt-get --force-yes -y install lvm2
pip install --upgrade pika
pip install --upgrade amqplib
pip install --upgrade kombu 
pip install --upgrade mysql-python
easy_install pika

# remove last line in /etc/fstab which has the old mount point
sed -i '$d' /etc/fstab

# change root/admin password
/usr/bin/mysqladmin -u root password hpcs 

# now shut down
/etc/init.d/mysql stop

mv /var/lib/mysql /var/lib/mysql.bak

umount /mnt

# remove innodb log file since log file size is changed
rm /var/lib/mysql.bak/ib_logfile*

# copy stock my.cnf
echo "[mysqld]
# this is a VERY stock my.cnf. I know, it needs to be tuned.
user=mysql

datadir=/var/lib/mysql
log = /var/log/mysql/query.log

innodb_buffer_pool_size=500M
innodb_log_file_size=100M
innodb_file_per_table 
" > /etc/mysql/my.cnf


fdisk /dev/vdb <<EOF
d
n
p
1


t
8e
w
EOF

pvcreate /dev/vdb1
vgcreate data /dev/vdb1
lvcreate --size 20G --name mysql-data data
mkfs.xfs /dev/data/mysql-data

mkdir /var/lib/mysql

chown mysql:mysql /var/lib/mysql

echo -e "\n/dev/data/mysql-data\t/var/lib/mysql\txfs\tdefaults\t0\t0\n" >> /etc/fstab

mount -a 

cp -a /var/lib/mysql.bak/* /var/lib/mysql/

chown -R mysql:mysql /var/lib/mysql

# start
/etc/init.d/mysql start

# this WILL be dynamic
#/usr/bin/mysql -u root -phpcs -e "grant all privileges on mysql.* to 'os_admin'@'localhost' identified by 'hpcs' with grant option;" 

# create agent DB account
# TODO: get privileges set up so agent can't read user, vice versa
/usr/bin/mysql -u root -phpcs -e "grant all privileges on *.* to 'os_admin'@'localhost' identified by 'hpcs' with grant option;"
# create user account. TODO: this will be passed via the API
/usr/bin/mysql -u root -phpcs -e "grant all privileges on *.* to 'dbas'@'%' identified by 'hpcs' with grant option;"



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

#echo 'export PYTHONPATH=/home/nova/reddwarf/swiftapi' >> /root/.bashrc
#source /root/.bashrc

ln -s /home/nova/.my.cnf /root/.my.cnf

cd reddwarf
ln -s /home/nova/reddwarf/smartagent/startup/smartagent /etc/init.d/smartagent
sudo /etc/init.d/smartagent start
