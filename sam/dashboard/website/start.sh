#!/bin/bash

sudo service mysql start
#python3 manage.py migrate
#python manage.py makemigrations polls
python3 ./manage.py runserver 0.0.0.0:8080 
