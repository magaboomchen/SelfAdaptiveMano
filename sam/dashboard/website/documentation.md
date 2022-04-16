# Django 1.9 Documentation
https://www.h5w3.com/doc/django-docs-1.9-en/intro/tutorial04.html

# Directory
DjangoWeb: 项目文件夹的名称，可以重命名
DjangoWeb/DjangoWeb: 网站的模块
DjangoWeb/webserver: 一个app，每个网站可以有多个apps

# 数据库相关
# webserver/models.py
里面定义的是一个数据类
可以通过Model提供的方法将数据存入数据库
python manage.py migrate命令可以根据models.py定义的数据类在数据库中构建相应的tables

## django的mysql数据库table格式
https://docs.djangoproject.com/en/1.8/ref/models/fields/#django.db.models.Field
https://zhuanlan.zhihu.com/p/74423815

## 查看models对应的sql，但不进行migrate
python3 manage.py sqlmigrate APP_NAME COMMIT_ID

## 简明的数据库交互介绍
https://docs.djangoproject.com/en/1.8/intro/overview/

# 用户管理相关
django封装了用户管理功能，可以直接调用
创建超级用户：python manage.py createsuperuser

# admin
admin的作用就是可以通过website添加object
https://docs.djangoproject.com/en/1.10/intro/overview/#a-dynamic-admin-interface-it-s-not-just-scaffolding-it-s-the-whole-house

# 解析httprequest的过程
urls.py中存储了url表，每个表项由匹配域和行为组成。匹配域就是一个url的正则表达式，行为是一个app的urls.py文件路径。
过程：
用户请求的url被django接收到后，先去DjangoWeb/DjangoWeb/urls中去匹配表项，获取到表项的行为：一个app的urls.py的文件路径。
然后再去对应的app中的urls.py中去匹配，会匹配到该app的views.py文件中的函数。

# Templates
一定要把html放在DjangoWeb/APP_NAME/templates/APP_NAME/下，否则会出现不同的app的html冲突的问题。

# 实时展示数据
https://blog.csdn.net/inch2006/article/details/80182238
https://blog.csdn.net/weixin_45753467/article/details/113148552
