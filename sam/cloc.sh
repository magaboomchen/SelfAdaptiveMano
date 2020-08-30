#!/bin/bash

#cloc --exclude-dir=./test/,./base/test,./serverController/classifierController/test/,./serverController/sffController,./serverController/vnfController,./serverController/builtin_pb/,./serverController/serverManager/test/,./mediator/test/,./ryu/test/,./serverAgent/test/ --exclude-ext=pyc .


cloc --exclude-dir=test,builtin_pb  --exclude-ext=pyc .
