# Pre-requisite
Only support python2.7, python3.6.9+, python3.7.2+, python3.8.1+ and python3.9+

# Installation
## apt
```
sudo apt-get install python-tk python-eventlet python-routes \
                     python-webob python-paramiko
```

## python2
```
pip uninstall tinyrpc enum
pip install -i https://pypi.gurobi.com gurobipy
pip install pytest paramiko enum34 psutil pika netifaces \
                    getmac pytest networkx numpy pandas \
                    tinyrpc==0.8 ruamel.yaml==0.15.52 matplotlib \
                    eventlet==0.30.2 scapy grpcio grpcio-tools \
                    docker sklearn ryu MySQL-python==1.2.5
```

## python3
```
pip3 uninstall tinyrpc enum
pip3 install pytest enum34 psutil pika netifaces==0.11.0 \
                getmac pytest networkx numpy pandas \
                gurobipy tinyrpc==0.8 matplotlib \
                scapy grpcio grpcio-tools docker \
                sklearn ryu paramiko ruamel.yaml==0.16.0 \
                eventlet==0.30.2 PyMySQL
```

## [Deprecated]Ansible-playbook
```
sudo apt-get install -y software-properties-common
sudo apt-add-repository -y ppa:ansible/ansible
sudo apt-get update
sudo apt-get install -y ansible
ansible-playbook -i localhost, -c local ./install.yml
```

## SAM python environment
### Method1: Auto (Recommendation)
```
python sam/base/environmentSetter.py
```

### Method2: Manual
```
ABSOLUTE_PATH_TO_THIS_PROJECT=pwd
cd /usr/local/lib/python2.7/dist-packages
sudo cat > selfAdaptiveMano.pth << EOF
${ABSOLUTE_PATH_TO_THIS_PROJECT}
EOF
```

## RabbitMQ
### Ubuntu 20.04 LTS
```
chmod +x ./installRabbitMQ.sh
./installRabbitMQ.sh
```

### configure the rabbitMQ server
```
rabbitmqctl add_user mq 123456
rabbitmqctl set_user_tags mq administrator
rabbitmqctl set_permissions -p "/" mq ".*" ".*" ".*"
rabbitmqctl list_permissions -p /
```

### generate rabbitMQ client conf
```
python sam/base/rabbitMQSetter.py
```

### Verify rabbitMQ installation
```
python -m pytest ./sam/base/test/unit/test_messageAgent.py -s
```

## [DON'T_EXECUTE_THIS]MessageAgent gRPC protos compile
We have compile the protos files, you don't need compile them again.
If there is something wrong with gRPC protos, you could regenerate them as follows:
```
python -m grpc_tools.protoc -I./base/messageAgentAuxillary/protos --python_out=./base/messageAgentAuxillary  --grpc_python_out=./base/messageAgentAuxillary    ./base/messageAgentAuxillary/protos/messageAgent.proto
```
Then, you need change "import messageAgent_pb2 as messageAgent__pb2" to "import sam.base.messageAgentAuxillary.messageAgent_pb2 as messageAgent__pb2".
And many other gRPC generated code has path problem, you should fix them.

## Mysql database
### Install python mysql
#### Ubuntu 16.04
```
sudo apt-get install libmysqlclient-dev
sudo python -m pip install MySQL-python
sudo service mysql start
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
https://www.digitalocean.com/community/tutorials/how-to-install-mysql-on-ubuntu-20-04
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
export RTE_SDK=${PATH_TO_DPDK}
export RTE_TARGET=x86_64-native-linuxapp-gcc
```

## RYU App (Only need for management and controller server)
### Set ryu app environment variable "path"
```
RYU_APP_PATH=/usr/local/lib/python2.7/dist-packages/ryu/app
```

## Java Apps
```
sudo apt install default-jre
sudo apt install default-jdk
cd sam/serverController/vnfController/click/ControlSocket
javac ./ControlSocket.java 
```

## Disable OS Auto update (For bess server)
```
sudoedit /etc/apt/apt.conf.d/20auto-upgrades
```
Change content FROM:
```
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
```
TO:
```
APT::Periodic::Update-Package-Lists "0";
APT::Periodic::Download-Upgradeable-Packages "0";
APT::Periodic::AutocleanInterval "0";
APT::Periodic::Unattended-Upgrade "1";
```