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
apt-get --force-yes --yes install python-swift swift policycoreutils python-mysqldb python-nova libdbd-mysql-perl libdbi-perl python-pip
apt-get install -qqy git
apt-get --force-yes -y install lvm2
pip install --upgrade pika
pip install --upgrade amqplib
pip install --upgrade kombu 
easy_install pika

# remove last line in /etc/fstab which has the old mount point
sed -i '$d' /etc/fstab

# change root/admin password
/usr/bin/mysqladmin -u root password hpcs 
# create agent DB account
# TODO: get privileges set up so agent can't read user, vice versa
/usr/bin/mysql -c "grant all privileges on *.* to 'os_admin'@'localhost' identified by 'hpcs' with grant option;"
# create user account. TODO: this will be passed via the API
/usr/bin/mysql -c "grant all privileges on *.* to 'dbas'@'localhost' identified by 'hpcs' with grant option;"

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
/usr/bin/mysql -u root -phpcs -e "grant all privileges on mysql.* to 'os_admin'@'localhost' identified by 'hpcs' with grant option;" 

useradd -d /home/nova -g mysql -m -s /bin/bash -p n0va nova
mkdir /home/nova/logs
mkdir /home/nova/lock
mkdir /home/nova/backup_logs
chown nova -R /home/nova/
mkdir /var/lib/mysql-backup
chown nova:mysql /var/lib/mysql-backup

cd /home/nova
git clone git clone git@github.com:hpcloud/reddwarf.git
cp /home/nova/reddwarf/smartagent/startup/disk_prep /etc/init.d
cp /home/nova/reddwarf/smartagent/startup/smartagent /etc/init.d
cp /home/nova/reddwarf/smartagent/startup/mysql.conf /etc/init.d
cp /home/nova/reddwarf/smartagent/startup/sudoers /etc
update-rc.d disk_prep defaults 85
update-rc.d smart_agent defaults 90
