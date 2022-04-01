# Installation
## python library
```
sudo python -m pip install psutil
sudo python -m pip install pika
sudo python -m pip install netifaces
sudo python -m pip install getmac
sudo python -m pip install pytest
sudo python -m pip install MySQL-python
sudo python -m pip install networkx
sudo python -m pip install numpy
sudo python -m pip install pandas
sudo python -m pip install -i https://pypi.gurobi.com gurobipy
sudo python -m pip install ryu
sudo python -m pip uninstall tinyrpc
sudo python -m pip install tinyrpc==0.8
sudo python -m pip install eventlet==0.30.2
sudo python -m pip install ruamel.yaml==0.15.52
sudo python -m pip install matplotlib
sudo python -m pip install scapy
sudo python -m pip install grpcio
sudo python -m pip install grpcio-tools
sudo python -m pip install docker
sudo python -m pip install paramiko
sudo python -m pip install sklearn
```

```
sudo python -m pip install paramiko enum34 psutil pika netifaces getmac pytest networkx numpy pandas gurobipy tinyrpc==0.8 ruamel.yaml==0.15.52 matplotlib scapy grpcio grpcio-tools docker sklearn ryu 
```

```
apt-get install python-tk
```

## Ansible-playbook
delete python module enum and install enum34
```
sudo apt-get install -y software-properties-common
sudo apt-add-repository -y ppa:ansible/ansible
sudo apt-get update
sudo apt-get install -y ansible
ansible-playbook -i localhost, -c local ./install.yml
```

## SAM python environment
### Auto (Recommendation)
```
python environmentSetter.py
```

### Manual
```
cd /usr/local/lib/python2.7/dist-packages
sudo vim selfAdaptiveMano.pth
(write) PATH_TO_THIS_PROJECT
```

## RabbitMQ
### install erlang 20.3.8.26-1 (please make sure the version number)
```
wget https://packages.erlang-solutions.com/erlang-solutions_1.0_all.deb
sudo dpkg -i erlang-solutions_1.0_all.deb
sudo apt-get update
sudo apt-get install esl-erlang=1:20.3.8.26-1
```

### rabbitmq3.7.0-1 (please make sure the version number)
```
echo "deb https://dl.bintray.com/rabbitmq/debian xenial main" | sudo tee /etc/apt/sources.list.d/bintray.rabbitmq.list
wget -Ohttps://dl.bintray.com/rabbitmq/Keys/rabbitmq-release-signing-key.asc | sudo apt-key add -
sudo apt-get update
sudo apt-get install rabbitmq-server
systemctl start rabbitmq-server.service
```

## Mysql database
### Install python mysql
#### Ubuntu 16.04
```
sudo apt-get install libmysqlclient-dev
sudo python -m pip install MySQL-python
```
#### Ubuntu 18.04
```
sudo apt-get install build-essential python-dev libmysqlclient-dev
sudo apt update
sudo apt install mysql-server
sudo mysql_secure_installation
sudo apt-get install gcc python3-dev
sudo apt-get install python-mysqldb
```

#### Ubuntu 20.04
```
sudo wget https://raw.githubusercontent.com/paulfitz/mysql-connector-c/master/include/my_config.h -O /usr/include/mysql/my_config.h
sudo add-apt-repository 'deb http://archive.ubuntu.com/ubuntu bionic main'
sudo apt update
sudo apt install -y python-mysqldb
```

### add user dbAgent with password 123
```
mysql -u root -p
mysql> CREATE USER 'dbAgent'@'localhost' IDENTIFIED BY '123';
mysql> GRANT ALL PRIVILEGES ON * . * TO 'dbAgent'@'localhost';
```

### add databases Orchestrator, Dashboard, Measurer
```
mysql> create database Orchestrator;
mysql> create database Dashboard;
mysql> create database Measurer;
```

## BESS (Only need for client server)
```
Install BESS according to the guide on https://github.com/NetSys/bess
```

## DPDK environment (Only need for client server)
export $RTE_SDK to the directory of dpdk in bess, for example:
``` 
export RTE_SDK=/home/t1/Projects/bess/deps/dpdk-17.11/
export RTE_TARGET=x86_64-native-linuxapp-gcc
```

## RYU App
### Set ryu app environment variable "path"
```
RYU_APP_PATH=/usr/local/lib/python2.7/dist-packages/ryu/app
```
