# Pre-requiste
Only support python2.7, python3.6.9+, python3.9+

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
pip install paramiko enum34 psutil pika netifaces \
                    getmac pytest networkx numpy pandas \
                    tinyrpc==0.8 ruamel.yaml==0.15.52 matplotlib \
                    eventlet==0.30.2 scapy grpcio grpcio-tools \
                    docker sklearn ryu MySQL-python cPickle \
```

## python3
```
pip3 uninstall tinyrpc enum
pip3 install enum34 psutil pika netifaces \
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

### MessageAgent gRPC
```
cd ~/Projects/SelfAdaptiveMano/sam/base/messageAgentAuxillary
protoc -I=./protos --python_out=./ ./protos/messageAgent.proto
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

### generate rabbitMQ client conf
```
python sam/base/rabbitMQSetter.py
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
sudo apt-get install libmysqlclient-dev
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

## RYU App (Only need for management and controller server)
### Set ryu app environment variable "path"
```
RYU_APP_PATH=/usr/local/lib/python2.7/dist-packages/ryu/app
```
