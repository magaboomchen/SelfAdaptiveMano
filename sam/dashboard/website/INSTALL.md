# 环境信息
数据库名称：mysitedb
django1.9.5
python3.6
OS：Ubuntu 16.04

PS：不需要SaltStack和Zabbix！

# 安装mysql数据库
```
sudo apt-get install libmysqlclient-dev
sudo service mysql start
sudo mysql -u root -p
mysql> CREATE USER 'dbAgent'@'localhost' IDENTIFIED BY '123';
mysql> GRANT ALL PRIVILEGES ON * . * TO 'dbAgent'@'localhost';
mysql> create database mysitedb;
mysql> create database OBServer;
mysql> create database Dashboard;
mysql> create database Measurer;

sudo apt-get install python3-pymysql
sudo apt install python-setuptools
```

# 安装Django模块
```
sudo pip3 install Django==1.9.5 -i https://pypi.tuna.tsinghua.edu.cn/simple
sudo pip3 install salt
```

# 初始化mysql数据库
```
python3 manage.py makemigrations 
python3 manage.py migrate
python3 manage.py createsuperuser 
```

# 修改代码错误
sam\dashboard\DjangoWeb\DjangoWeb\settings.py中
STATIC_ROOT = os.path.join(BASE_DIR,'/static/')

# 启动Django
python3 ./manage.py runserver 0.0.0.0:8080

#浏览器输入如下url打开管理页面
http://127.0.0.1:8080/admin/

# 安装部分SAM依赖模块
```
sudo python -m pip install enum34 psutil pika netifaces getmac pytest networkx numpy pandas gurobipy ryu tinyrpc==0.8 ruamel matplotlib scapy grpcio grpcio-tools docker
apt-get install python-tk

# Install mysql on Ubuntu 18.04
sudo apt-get install build-essential python-dev libmysqlclient-dev
sudo apt update
sudo apt install mysql-server
sudo mysql_secure_installation
sudo apt-get install gcc python3-dev
sudo apt-get install python-mysqldb
```

# 更新到Django3.2.8（放弃。可以说明dashboard不算编排系统，所以不考虑其安全性。）

* 更新Django
```
pip3 install Django==3.2.8
```

* 删除pymysql，重新安装mysqlclient
```
sudo apt-get remove python3-pymysql
pip3 install -U mysqlclient
```

* 引入mysqlclient模块
```
sam\dashboard\DjangoWeb\DjangoWeb\__init__.py中更改为：
import MySQLdb
```

* 修改API
```
sam\dashboard\DjangoWeb\webserver\models.py: 
```
