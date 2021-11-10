# Create your views here.
# -*- coding: utf-8 -*-

import time
import socket
import platform
import sys,os
import json
import subprocess
import smtplib
import logging

from django.http import HttpResponse
from django.core.paginator import PageNotAnInteger, Paginator, InvalidPage, EmptyPage
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.contrib import auth
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.db.models import Count,Sum
from .models import hostinfo
from django.http import JsonResponse
from django.core import serializers
from .models import monitorMemory
import urllib.request, urllib.parse, urllib.request
import salt.client
from webserver.forms import UserForm,RegisterForm,AlterForm,hostadimnForm,monitorForm,autoArrMinionForm
from email.mime.text import MIMEText
from email.header import Header


from django.core.paginator import PageNotAnInteger,  InvalidPage, EmptyPage
from django.shortcuts import render

from django.contrib.auth.decorators import login_required

from sam.dashboard.dashboardInfoBaseMaintainer import *
from sam.measurement.dcnInfoBaseMaintainer import *
from sam.orchestration.orchInfoBaseMaintainer import *
from sam.dashboard.base.pageSlicer import *
from sam.base.pickleIO import *


# class displayedUsersList(list):
#     def __init__(self):
#         pass

#     def getPageNums(self,  totalPageNum, pageNum):
#         self.totalPageNum = totalPageNum
#         self.pageNum = pageNum
#         if pageNum < totalPageNum:
#             self.hasNextPage = True
#             self.nextPageNum = pageNum + 1
#         else:
#             self.hasNextPage = False
#         if pageNum == 1:
#             self.hasPreviousPage = False
#         else:
#             self.hasPreviousPage = True
#             self.previousPageNum = pageNum - 1
#         return self

def login(req):
    '''
    登录验证
    '''
    print("login page")
    nowtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    if req.method == 'GET':
        uf = UserForm()
        return render(req,'login.html', {'uf': uf,'nowtime': nowtime })
    else:
        print("not GET")
        uf = UserForm(req.POST)
        if uf.is_valid():
            username = req.POST.get('username', '')
            password = req.POST.get('password', '')
            user = auth.authenticate(username = username, password = password)
            if user is not None and user.is_active:
                print("A")
                auth.login(req,user)
                return render(req, 'index.html')
            else:
                print("B")
                print(user, user.is_active)
                return render(req, 'login.html', {'uf': uf,'nowtime': nowtime, 'password_is_wrong': True})
        else:
            return render(req, 'login.html', {'uf': uf,'nowtime': nowtime })

@login_required
def index(req):
    system = platform.system()
    if system == 'Windows':
        version = platform.version()
        OsVersion = system + '. '+ version
    else:
        node = platform.node()
        OsVersion = node + '@' + system
    return render(req, 'index.html', {'OsVersion': OsVersion})

@login_required
def logout(req):
    '''
    注销
    '''
    auth.logout(req)
    return HttpResponseRedirect('/webserver/login/')

@login_required
def userAdd(req):
    '''
    添加用户
    '''
    # print("req.method: {0}".format(req.method))
    # sys.stdout.flush()
    if req.method == "POST":
        user_add = RegisterForm(req.POST)
        if user_add.is_valid():
            data = user_add.cleaned_data
            print (data)
            add_user = data.get('add_user')
            add_password = data.get('add_password')
            add_email = data.get('add_email', '')
            add_isactive = data.get('add_isactive')
            user = User()
            user.username = add_user
            user.set_password(add_password)
            user.email = add_email
            user.is_active = add_isactive
            user.save()
            return render(req, 'useradd.html', {'add_newuser': add_user})
        else:
            errors = user_add.errors
            return render(req, 'useradd.html',{'add_FormInput': user_add,'errors': errors})
    else:
        user_add = RegisterForm()
    return render(req, 'useradd.html', {'add_FormInput': user_add})
@login_required
def userAlter(req, id):
    '''
    修改用户
    '''
    user_alter = AlterForm(req.POST)
    if req.method == "POST":
        if user_alter.is_valid():
            alter_data = user_alter.cleaned_data
            print(alter_data)
            alter_email = alter_data.get('alter_email')
            alter_isactive = alter_data.get('alter_isactive')
            alt = User.objects.get(id=id)
            alt.email = alter_email
            alt.is_active = alter_isactive
            alt.save()
            return HttpResponseRedirect('/webserver/user/list/')
        else:
            errors = user_alter.errors
            return render(req, 'useralter.html', {'alter_FormInput': user_alter, 'errors': errors})
    else:
        try:
            UpdateUser = User.objects.only('username').get(id=id).username
            old_eamil = User.objects.only('email').get(id=id).email
            old_is_active = User.objects.only('is_active').get(id=id).is_active
            if old_is_active:
                old_is_active = 1
            else:
                old_is_active = 0

            form = AlterForm(
                initial={'alter_email': old_eamil}
            )
            return render(req, 'useralter.html', {'alter_FormInput': form, 'UpdateUser': UpdateUser, 'alter_is_active':old_is_active})
        except:
            post = get_object_or_404(User, id=id)
            form = AlterForm(instance=post)
            return render(req, 'useralter.html', {'form': form})

@login_required
def serverList(request,id = 0):
    '''
    服务器列表
    '''
    if id != 0:
        hostinfo.objects.filter(id = id).delete()
    if request.method == "POST":
        getHostInfo()
        print(request.POST)
        pageSize = request.POST.get('pageSize')   # how manufactoryy items per page
        pageNumber = request.POST.get('pageNumber')
        offset = request.POST.get('offset')  # how many items in total in the DB
        search = request.POST.get('search')
        sort_column = request.POST.get('sort')   # which column need to sort
        order = request.POST.get('order')      # ascending or descending
        if search:    #    判断是否有搜索字
            all_records = hostinfo.objects.filter(id=search,asset_type=search,business_unit=search,idc=search)
        else:
            all_records = hostinfo.objects.all()   # must be wirte the line code here

        if sort_column:   # 判断是否有排序需求
            sort_column = sort_column.replace('asset_', '')
            if sort_column in ['id','asset_type','sn','name','management_ip','manufactory','type']:   # 如果排序的列表在这些内容里面
                if order == 'desc':   # 如果排序是反向
                    sort_column = '-%s' % (sort_column)
                all_records = hostinfo.objects.all().order_by(sort_column)
            elif sort_column in ['salt_minion_id','os_release',]:
                # server__ 表示asset下的外键关联的表server下面的os_release或者其他的字段进行排序
                sort_column = "server__%s" % (sort_column)
                if order == 'desc':
                    sort_column = '-%s'%(sort_column)
                all_records = hostinfo.objects.all().order_by(sort_column)
            elif sort_column in ['cpu_model','cpu_count','cpu_core_count']:
                sort_column = "cpu__%s" %(sort_column)
                if order == 'desc':
                    sort_column = '-%s'%(sort_column)
                all_records = hostinfo.objects.all().order_by(sort_column)
            elif sort_column in ['rams_size',]:
                if order == 'desc':
                    sort_column = '-rams_size'
                else:
                    sort_column = 'rams_size'
                all_records = hostinfo.objects.all().annotate(rams_size = Sum('ram__capacity')).order_by(sort_column)
            elif sort_column in ['localdisks_size',]:  # using variable of localdisks_size because there have a annotation below of this line
                if order == "desc":
                    sort_column = '-localdisks_size'
                else:
                    sort_column = 'localdisks_size'
                #     annotate 是注释的功能,localdisks_size前端传过来的是这个值，后端也必须这样写，Sum方法是django里面的，不是小写的sum方法，
                # 两者的区别需要注意，Sum（'disk__capacity‘）表示对disk表下面的capacity进行加法计算，返回一个总值.
                all_records = hostinfo.objects.all().annotate(localdisks_size=Sum('disk__capacity')).order_by(sort_column)

            elif sort_column in ['idc',]:
                sort_column = "idc__%s" % (sort_column)
                if order == 'desc':
                    sort_column = '-%s'%(sort_column)
                all_records = hostinfo.objects.all().order_by(sort_column)

            elif sort_column in ['trade_date','create_date']:
                if order == 'desc':
                    sort_column = '-%s'%sort_column
                all_records = User.objects.all().order_by(sort_column)

        all_records_count=all_records.count()

        if not offset:
            offset = 0
        if not pageSize:
            pageSize = 10    # 默认是每页20行的内容，与前端默认行数一致
        pageinator = Paginator(all_records, pageSize)   # 开始做分页
        page = int(int(offset) / int(pageSize) + 1)
        response_data = {'total': all_records_count, 'rows': []}
        for server_li in pageinator.page(page):
            response_data['rows'].append({
                "id": server_li.id if server_li.id else "",
                "hostname": server_li.hostname if server_li.hostname else "",
                "IP":server_li.IP if server_li.IP else "",
                "Mem":server_li.Mem if server_li.Mem else "",
                "CPU": server_li.CPU if server_li.CPU else "",
                "CPUS": server_li.CPUS if server_li.CPUS else "",
                "OS": server_li.OS if server_li.OS else "",
                "virtual1": server_li.virtual1 if server_li.virtual1 else "",
                "status": server_li.status if server_li.status else "",
            })
        return HttpResponse(json.dumps(response_data))
    return render(request, 'serverlist.html')


           
            

@login_required
def hostAdmin(request):
    '''
    批量执行命令
    '''
    if request.method == 'POST':
        # local = salt.client.LocalClient() # api
        search = hostadimnForm(request.POST)
        cmd_host = request.POST.get('hostlist', '')
        funlist = request.POST.get('funlist', '')
        command = request.POST.get('command','')
        if cmd_host == '':
            cmd_host = '*'
        if command != '':
            if '"' in command:
                command = command.replace('"',"'")
            (status, result) = subprocess.getstatusoutput(
                " ssh 127.0.0.1 'salt \"" + cmd_host + "\" " + funlist + " \" " + command + " \" ' ")
            # result = local.cmd(cmd_host, funlist, [command])  # api
        else:
            (status, result) = subprocess.getstatusoutput(
                " ssh 127.0.0.1 'salt \"" + cmd_host + "\" " + funlist + " ' ")
            # result = local.cmd(cmd_host, funlist) # api
        result_dict = {
            'search': search,
            'result': result,
        }
        return render(request, 'hostadmin.html', result_dict)

    else:
        search = hostadimnForm()
        result_dict = {
            'search' : search,
        }
        return render(request, 'hostadmin.html', result_dict)


@login_required
def getMonitor(request):
    '''获取zabbix监控的主机列表'''
    monitorform = monitorForm()
    zabbix_host_info = dataHandle(func=getZabbixHost)
    monitor_hostnames = []
    cpuutils_now = ''
    cpuload_now = ''
    fsused_now = ''
    fsfree_now = ''
    for i in zabbix_host_info:
        monitor_hostid = i['hostid']
        monitor_hostname = i['host']
        monitor_hostnames = monitor_hostnames + [(monitor_hostid, monitor_hostname)]
    host_num  = len(monitor_hostnames)
    monitorform.fields['monitorHost'].choices = monitor_hostnames

    '''获取提交的主机ID'''
    try:
        if request.method == "POST":
            if "monitorHost" in request.POST:   # name为monitorHost的表单提交
                hostid = request.POST.get('monitorHost','')
            else:
                hostid = 10084
        else:
            hostid = 10084

        '''获取提交主机的itemids'''
        # itemids = dataHandle(func=getZabbixitem,hostid=hostid)

        '''获取CPU使用率'''
        cpuutils_dict = dataHandle(func=getZabbixCPUutil, hostid=hostid)

        '''获取CPU负载'''
        cpuload_dict = dataHandle(func=getZabbixCPUload, hostid=hostid)

        '''获取硬盘使用量'''
        fsused_dict = dataHandle(func=getfsused, hostid=hostid)

        '''获取硬盘总量'''
        fsfree_dict = dataHandle(func=getfsfree, hostid=hostid)

        for i in cpuutils_dict:
            cpuutils_now = i['prevvalue']  # CPU当前使用率百分比
        for i in cpuload_dict:
            cpuload_now = i['prevvalue']  # CPU当前负载百分比
        for i in fsused_dict:
            fsused_now = i['prevvalue'] # 磁盘使用量
        for i in fsfree_dict:
            fsfree_now = i['prevvalue'] # 磁盘空闲

    except KeyError as e:
        print (e)
        pass

    '''获取内存使用率最后15次的数据'''
    me_data = monitorMemory.objects.filter(hostid=hostid)[2:]
    '''返回的前端的字典'''
    monitor_dict = {
        "monitorform" : monitorform,    # 监控主机的表单
        "monitor_hostnames" : monitor_hostnames, # 监控的主机的下拉菜单列表
        "host_num" : host_num,    # 监控的主机个数
        "cpuutils_now" : cpuutils_now,  # CPU当前使用率
        "cpuload_now" : cpuload_now,    # CPU当前负载
        "fsused_now" : fsused_now,  # 磁盘使用量
        "fsfree_now" : fsfree_now, # 磁盘空闲
        "data" : me_data
    }
    return render(request, 'Monitor.html', monitor_dict)



@login_required
def serverAdd(request):
    result = ''
    check_ip_inro = 0   #检查主机是否存在，0不存在，1存在
    if request.method == "POST":
        form = autoArrMinionForm(request.POST)
        if form.is_valid():
            ip = request.POST.get('add_ip') # 需要安装minion端的ip
            username = request.POST.get('add_username') # 需要安装minion端的用户名
            password = request.POST.get('add_password') # 需要安装minion端的密码
            check_ip_list = hostinfo.objects.values_list('IP', flat=True) # 获取已经安装minion的ip列表
            for i in check_ip_list:  # 将有多个ip的主机ip分开，自成一个列表供匹配检查主机是否已经存在
                if " | " in i:
                    check_ip_list_two = i.split(" | ")
                    if ip in check_ip_list_two: # 判断输入的ip是否在主机列表中
                        check_ip_inro = 1
                        break
            if ip not in check_ip_list and check_ip_inro == 0:
                try:
                    os.system("echo '"+ip+":'>> /etc/salt/roster && \
                                echo '  host: " +ip+ "'>> /etc/salt/roster && \
                                echo '  user: " +username+ "'>> /etc/salt/roster && \
                                echo '  passwd: " +password+ "'>> /etc/salt/roster && \
                                echo '  sudo: True'>> /etc/salt/roster && \
                                echo '  tty: True'>> /etc/salt/roster && \
                                echo '  timeout: 10'>> /etc/salt/roster")
                    os.system("salt-ssh '" + ip + "' -ir 'easy_install certifi'") # 安装cretifi模块
                    (status_gethostname, resultgethostname) = subprocess.getstatusoutput("salt-ssh -ir '" + ip + "' 'hostname'") # 获取hostname
                    os.system("salt-ssh '" + ip + "' -ir 'echo ''"+ip+"' '"+resultgethostname+"''>> /etc/hosts'") # 添加hosts
                    (status, result) = subprocess.getstatusoutput("salt-ssh -i '"+ip+"' state.sls minions.install") # 执行安装命令，并返回结果
                except:
                    result = "注意：无法连接该主机，请检查ip和用户密码是否正确！"
            else:
                result = "提示：这台主机已加入主机列表！"
        else:
            result = "注意：请填写正确的ip、用户名或密码！"
    else:
        form = autoArrMinionForm()
    re = {
        "form": form,
        "result": result
    }
    return  render(request, "serveradd.html", re)

def getPageNumFromHttpRequest(req):
    try:    #如果请求的页码少于1或者类型错误，则跳转到第1页
        page = int(req.GET.get("page",1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1
    except TypeError:
        page = 1
    
    return page

def getAllUsersFromDataBase():
    dibm = DashboardInfoBaseMaintainer('localhost', 'dbAgent', '123')
    users = dibm.getAllUser()
    return users

def getAllUsersDictList(allUsersList):
    allUsersDictList = []
    userID=1
    for userTuple in allUsersList:
        userDict = {}
        userDict['name'] = userTuple[0]
        userDict['UUID'] = userTuple[1]
        userDict['type'] = userTuple[2]
        userDict['ID'] = userID
        allUsersDictList.append(userDict)
        userID = userID + 1
    return allUsersDictList

def getDisplayedUsersListOnPage(users, pageNum):
    ps = PageSlicer()
    try:
        displayedUsers = ps.getObjsListOnPage(users, pageNum)
    except(EmptyPage, InvalidPage, PageNotAnInteger):
        displayedUsers = ps.getObjsListOnPage(users, 1)
    return displayedUsers

def getPageRange(page, totalPageNum):
    afterRangeNum = 2     #当前页前显示2页
    beforeRangeNum = 2     #当前页后显示2页
    if page >= afterRangeNum and page <= totalPageNum - beforeRangeNum:
        pageRange = range(page - afterRangeNum,page + beforeRangeNum +1)
    elif page < afterRangeNum and page <= totalPageNum - beforeRangeNum:
        pageRange = range(1, page + beforeRangeNum + 1)
    elif page >= afterRangeNum and page > totalPageNum - beforeRangeNum:
        pageRange = range(page - afterRangeNum, totalPageNum + 1)
    else:
        pageRange = range(1, totalPageNum+1)
    return pageRange

def getTotalPageNum(usersNum, usersNumPerPage):
    if usersNum%usersNumPerPage == 0:
        totalPageNum = int((usersNum - usersNum%usersNumPerPage)/usersNumPerPage)
    else:
        totalPageNum = int((usersNum - usersNum%usersNumPerPage)/usersNumPerPage+1)
    return totalPageNum

def getNumDict(pageNum, totalPageNum):
    numDict={}
    if pageNum == 1:
        numDict['hasPreviousPage'] = False
    else:
        numDict['hasPreviousPage'] = True
    if pageNum == totalPageNum:
        numDict['hasNextPage'] = False
    else:
        numDict['hasNextPage'] = True
    numDict['nextPageNum'] = pageNum + 1
    numDict['previousPageNum'] = pageNum - 1
    
    if totalPageNum == 0:
        numDict['displayedTotalPageNum'] = 1
    else:
        numDict['displayedTotalPageNum'] = totalPageNum
    return numDict
        
@login_required
def showUserList(req):
    usersTupleList = getAllUsersFromDataBase()
    users = getAllUsersDictList(usersTupleList)
    pageNum = getPageNumFromHttpRequest(req)
    displayedUsersList = getDisplayedUsersListOnPage(users, pageNum)
    usersNumPerPage = 11
    totalPageNum = getTotalPageNum(len(users), usersNumPerPage)
    pageRange = getPageRange(pageNum, totalPageNum)
    numDict=getNumDict(pageNum, totalPageNum)
    print(numDict)
    return render(req, 'userlist.html',
            {'displayedUsersList' : displayedUsersList,
                'pageRange': pageRange,
                'totalPageNum': totalPageNum,
                'pageNum': pageNum,
                'numDict': numDict
            })

def getAllZonesFromDataBase():
    dibm = DashboardInfoBaseMaintainer('localhost', 'dbAgent', '123')
    zones = dibm.getAllZone()
    return zones

def getAllZonesDictList(allZonesList):
    allZonesDictList = []
    zoneID = 1
    for zoneTuple in allZonesList:
        zoneDict = {}
        zoneDict['name'] = zoneTuple[0]
        zoneDict['ID'] = zoneID
        allZonesDictList.append(zoneDict)
        zoneID = zoneID + 1
    return allZonesDictList

def getDisplayedZonesListOnPage(zones, pageNum):
    ps = PageSlicer()
    try:
        displayedzones = ps.getObjsListOnPage(zones, pageNum)
    except(EmptyPage, InvalidPage, PageNotAnInteger):
        displayedzones = ps.getObjsListOnPage(zones, 1)
    return displayedzones        

@login_required
def showZoneList(req):
    zonesTupleList = getAllZonesFromDataBase()
    zones = getAllZonesDictList(zonesTupleList)
    pageNum = getPageNumFromHttpRequest(req)
    displayedZonesList = getDisplayedZonesListOnPage(zones, pageNum)
    zonesNumPerPage = 11
    totalPageNum = getTotalPageNum(len(zones), zonesNumPerPage)
    pageRange = getPageRange(pageNum, totalPageNum)
    numDict=getNumDict(pageNum, totalPageNum)
    return render(req, 'zonelist.html',
            {'displayedZonesList' : displayedZonesList,
                'pageRange': pageRange,
                'totalPageNum': totalPageNum,
                'pageNum': pageNum,
                'numDict': numDict
            })

def getAllRoutingMorphicsFromDataBase():
    dibm = DashboardInfoBaseMaintainer('localhost', 'dbAgent', '123')
    RoutingMorphics = dibm.getAllRoutingMorphic()
    return RoutingMorphics

def getAllRoutingMorphicsDictList(allRoutingMorphicsList):
    allRoutingMorphicsDictList = []
    rmID = 1
    for RoutingMorphicTuple in allRoutingMorphicsList:
        RoutingMorphicDict = {}
        RoutingMorphicDict['name'] = RoutingMorphicTuple[0]
        RoutingMorphicDict['ID'] = rmID
        allRoutingMorphicsDictList.append(RoutingMorphicDict)
        rmID = rmID + 1
    return allRoutingMorphicsDictList

def getDisplayedRoutingMorphicsListOnPage(RoutingMorphics, pageNum):
    ps = PageSlicer()
    try:
        displayedRoutingMorphics = ps.getObjsListOnPage(RoutingMorphics, pageNum)
    except(EmptyPage, InvalidPage, PageNotAnInteger):
        displayedRoutingMorphics = ps.getObjsListOnPage(RoutingMorphics, 1)
    return displayedRoutingMorphics

@login_required
def showRoutingMorphicList(req):
    RoutingMorphicsTupleList = getAllRoutingMorphicsFromDataBase()
    RoutingMorphics = getAllRoutingMorphicsDictList(RoutingMorphicsTupleList)
    pageNum = getPageNumFromHttpRequest(req)
    displayedRoutingMorphicsList = getDisplayedRoutingMorphicsListOnPage(RoutingMorphics, pageNum)
    RoutingMorphicsNumPerPage = 11
    totalPageNum = getTotalPageNum(len(RoutingMorphics), RoutingMorphicsNumPerPage)
    pageRange = getPageRange(pageNum, totalPageNum)
    numDict=getNumDict(pageNum, totalPageNum)
    print(RoutingMorphics,pageNum,pageRange)
    return render(req, 'routingmorphiclist.html',
            {'displayedRoutingMorphicsList' : displayedRoutingMorphicsList,
                'pageRange': pageRange,
                'totalPageNum': totalPageNum,
                'pageNum': pageNum,
                'numDict': numDict
            })

def getAllServersFromDataBase():
    dibm = DCNInfoBaseMaintainer()
    dibm.enableDataBase("localhost", "dbAgent", "123")
    servers = dibm.getAllServer()
    return servers

def getAllServersDictList(allServersList):
    allServersDictList = []
    serverID = 1
    for serverTuple in allServersList:
        serverDict = {}
        serverDict['zoneName'] = serverTuple[1]
        serverDict['serverID'] = serverTuple[0]
        serverDict['IPV4'] = serverTuple[4]
        serverDict['cpuUtilization'] = serverTuple[5]
        serverDict['ID'] = serverID
        allServersDictList.append(serverDict)
        serverID = serverID + 1
    return allServersDictList

def getDisplayedServersListOnPage(servers, pageNum):
    ps = PageSlicer()
    try:
        displayedServers = ps.getObjsListOnPage(servers, pageNum)
    except(EmptyPage, InvalidPage, PageNotAnInteger):
        displayedServers = ps.getObjsListOnPage(servers, 1)
    return displayedServers 

@login_required
def showServerList(req):
    serversTupleList = getAllServersFromDataBase()
    servers = getAllServersDictList(serversTupleList)
    pageNum = getPageNumFromHttpRequest(req)
    displayedServersList = getDisplayedServersListOnPage(servers, pageNum)
    serversNumPerPage = 11
    totalPageNum = getTotalPageNum(len(servers), serversNumPerPage)
    pageRange = getPageRange(pageNum, totalPageNum)
    numDict=getNumDict(pageNum, totalPageNum)
    print(pageNum)
    return render(req, 'serverlist.html',
            {'displayedServersList' : displayedServersList,
                'pageRange': pageRange,
                'totalPageNum': totalPageNum,
                'pageNum': pageNum,
                'numDict': numDict
            })

def getAllSwitchsFromDataBase():
    dibm = DCNInfoBaseMaintainer()
    dibm.enableDataBase("localhost", "dbAgent", "123")
    switchs = dibm.getAllSwitch()
    return switchs
    
def getAllSwitchsDictList(allSwitchsList):
    allSwitchsDictList = []
    switchID = 1
    for switchTuple in allSwitchsList:
        switchDict = {}
        switchDict['zoneName'] = switchTuple[1]
        switchDict['switchID'] = switchTuple[2]
        switchDict['ID'] = switchID
        allSwitchsDictList.append(switchDict)
        switchID =switchID + 1
    return allSwitchsDictList

def getDisplayedSwitchsListOnPage(Switchs, pageNum):
    ps = PageSlicer()
    try:
        displayedSwitchs = ps.getObjsListOnPage(Switchs, pageNum)
    except(EmptyPage, InvalidPage, PageNotAnInteger):
        displayedSwitchs = ps.getObjsListOnPage(Switchs, 1)
    return displayedSwitchs 

@login_required
def showSwitchList(req):
    switchsTupleList = getAllSwitchsFromDataBase()
    switchs = getAllSwitchsDictList(switchsTupleList)
    pageNum = getPageNumFromHttpRequest(req)
    displayedSwitchsList = getDisplayedSwitchsListOnPage(switchs, pageNum)
    switchsNumPerPage = 11
    totalPageNum = getTotalPageNum(len(switchs), switchsNumPerPage)
    pageRange = getPageRange(pageNum, totalPageNum)
    numDict=getNumDict(pageNum, totalPageNum)
    print(pageNum)
    return render(req, 'switchlist.html',
            {'displayedSwitchsList' : displayedSwitchsList,
                'pageRange': pageRange,
                'totalPageNum': totalPageNum,
                'pageNum': pageNum,
                'numDict': numDict
            })
    
def getAllLinksFromDataBase():
    dibm = DCNInfoBaseMaintainer()
    dibm.enableDataBase("localhost", "dbAgent", "123")
    links = dibm.getAllLink()
    return links
    
def getAllLinksDictList(allLinksList):
    allLinksDictList = []
    linkID = 1
    for linkTuple in allLinksList:
        linkDict = {}
        linkDict['ID'] = linkID
        linkDict['SRC_ID'] = linkTuple[2]
        linkDict['DST_ID'] = linkTuple[3]
        linkDict['bandwidth'] = linkTuple[4]
        linkDict['utilization'] = linkTuple[5]
        allLinksDictList.append(linkDict)
        linkID = linkID + 1
    return allLinksDictList

def getDisplayedLinksListOnPage(links, pageNum):
    ps = PageSlicer()
    try:
        displayedLinks = ps.getObjsListOnPage(links, pageNum)
    except(EmptyPage, InvalidPage, PageNotAnInteger):
        displayedLinks = ps.getObjsListOnPage(links, 1)
    return displayedLinks 

@login_required
def showLinkList(req):
    linksTupleList = getAllLinksFromDataBase()
    links = getAllLinksDictList(linksTupleList)
    pageNum = getPageNumFromHttpRequest(req)
    displayedLinksList = getDisplayedLinksListOnPage(links, pageNum)
    linksNumPerPage = 11
    totalPageNum = getTotalPageNum(len(links), linksNumPerPage)
    pageRange = getPageRange(pageNum, totalPageNum)
    numDict=getNumDict(pageNum, totalPageNum)
    print(pageNum)
    return render(req, 'Linklist.html',
            {'displayedLinksList' : displayedLinksList,
                'pageRange': pageRange,
                'totalPageNum': totalPageNum,
                'pageNum': pageNum,
                'numDict': numDict
            })

def getAllRequestsFromDataBase():
    dibm = OrchInfoBaseMaintainer("localhost", "dbAgent", "123")
    requests = dibm.getAllRequest()
    return requests
    
def getAllRequestsDictList(allRequestsList):
    allRequestsDictList = []
    requestID = 1
    for requestTuple in allRequestsList:
        requestDict = {}
        requestDict['ID'] = requestID
        requestDict['requestUUID'] = requestTuple[0]
        requestDict['requestType'] = requestTuple[1]
        requestDict['SFC_UUID'] = requestTuple[2]
        requestDict['state'] = requestTuple[5]
        allRequestsDictList.append(requestDict)
        requestID = requestID + 1
    return allRequestsDictList

def getDisplayedRequestsListOnPage(requests, pageNum):
    ps = PageSlicer()
    try:
        displayedRequests = ps.getObjsListOnPage(requests, pageNum)
    except(EmptyPage, InvalidPage, PageNotAnInteger):
        displayedRequests = ps.getObjsListOnPage(requests, 1)
    return displayedRequests 

@login_required
def showRequestList(req):
    requestsTupleList = getAllRequestsFromDataBase()
    requests = getAllRequestsDictList(requestsTupleList)
    pageNum = getPageNumFromHttpRequest(req)
    displayedRequestsList = getDisplayedRequestsListOnPage(requests, pageNum)
    requestsNumPerPage = 11
    totalPageNum = getTotalPageNum(len(requests), requestsNumPerPage)
    pageRange = getPageRange(pageNum, totalPageNum)
    numDict=getNumDict(pageNum, totalPageNum)
    print(pageNum)
    return render(req, 'requestlist.html',
            {'displayedRequestsList' : displayedRequestsList,
                'pageRange': pageRange,
                'totalPageNum': totalPageNum,
                'pageNum': pageNum,
                'numDict': numDict
            })

def getAllSFCsFromDataBase():
    dibm = OrchInfoBaseMaintainer("localhost", "dbAgent", "123")
    SFCs = dibm.getAllSFC()
    return SFCs
    
def getAllSFCsDictList(allSFCsList):
    allSFCsDictList = []
    sfcID = 1
    for SFCTuple in allSFCsList:
        SFCDict = {}
        SFCDict['ID'] = sfcID
        SFCDict['zoneName'] = SFCTuple[0]
        SFCDict['SFC_UUID'] = SFCTuple[1]
        pickleSFC = PickleIO()
        rawSFCIIDList = SFCTuple[2]
        # print(rawSFCIIDList)
        SFCDict['SFCIIDList'] = pickleSFC.pickle2Obj(rawSFCIIDList)
        # print(SFCDict['SFCIIDList'])
        SFCDict['state'] = SFCTuple[3]
        allSFCsDictList.append(SFCDict)
        sfcID = sfcID + 1
    return allSFCsDictList

def getDisplayedSFCsListOnPage(SFCs, pageNum):
    ps = PageSlicer()
    try:
        displayedSFCs = ps.getObjsListOnPage(SFCs, pageNum)
    except(EmptyPage, InvalidPage, PageNotAnInteger):
        displayedSFCs = ps.getObjsListOnPage(SFCs, 1)
    return displayedSFCs 

@login_required
def showSFCList(req):
    SFCsTupleList = getAllSFCsFromDataBase()
    SFCs = getAllSFCsDictList(SFCsTupleList)
    pageNum = getPageNumFromHttpRequest(req)
    displayedSFCsList = getDisplayedSFCsListOnPage(SFCs, pageNum)
    SFCsNumPerPage = 11
    totalPageNum = getTotalPageNum(len(SFCs), SFCsNumPerPage)
    pageRange = getPageRange(pageNum, totalPageNum)
    numDict=getNumDict(pageNum, totalPageNum)
    print(pageNum)
    return render(req, 'SFClist.html',
            {'displayedSFCsList' : displayedSFCsList,
                'pageRange': pageRange,
                'totalPageNum': totalPageNum,
                'pageNum': pageNum,
                'numDict': numDict
            })

def getAllSFCIsFromDataBase():
    dibm = OrchInfoBaseMaintainer("localhost", "dbAgent", "123")
    SFCIs = dibm.getAllSFCI()
    return SFCIs
    
def getAllSFCIsDictList(allSFCIsList):
    allSFCIsDictList = []
    sfciID = 1
    for SFCITuple in allSFCIsList:
        SFCIDict = {}
        SFCIDict['ID'] = sfciID
        SFCIDict['SFCIID'] = SFCITuple[0]
        pickleSFCI = PickleIO()
        rawSFCIIIDList = SFCITuple[1]
        VNFIList = pickleSFCI.pickle2Obj(rawSFCIIIDList)
        SFCIDict['VNFIList'] = []
        for VNFIs in VNFIList:
            SFCIDict['VNFIList'].append(VNFIs.vnfiID)
        SFCIDict['state'] = SFCITuple[2]
        SFCIDict['orchestrationTime'] = SFCITuple[4]
        allSFCIsDictList.append(SFCIDict)
        sfciID = sfciID + 1
    return allSFCIsDictList

def getDisplayedSFCIsListOnPage(SFCIs, pageNum):
    ps = PageSlicer()
    try:
        displayedSFCIs = ps.getObjsListOnPage(SFCIs, pageNum)
    except(EmptyPage, InvalidPage, PageNotAnInteger):
        displayedSFCIs = ps.getObjsListOnPage(SFCIs, 1)
    return displayedSFCIs 

@login_required
def showSFCIList(req):
    SFCIsTupleList = getAllSFCIsFromDataBase()
    SFCIs = getAllSFCIsDictList(SFCIsTupleList)
    pageNum = getPageNumFromHttpRequest(req)
    displayedSFCIsList = getDisplayedSFCIsListOnPage(SFCIs, pageNum)
    SFCIsNumPerPage = 11
    totalPageNum = getTotalPageNum(len(SFCIs), SFCIsNumPerPage)
    pageRange = getPageRange(pageNum, totalPageNum)
    numDict=getNumDict(pageNum, totalPageNum)
    print(pageNum)
    return render(req, 'SFCIlist.html',
            {'displayedSFCIsList' : displayedSFCIsList,
                'pageRange': pageRange,
                'totalPageNum': totalPageNum,
                'pageNum': pageNum,
                'numDict': numDict
            })

def getAllVNFIsFromDataBase():
    dibm = OrchInfoBaseMaintainer("localhost", "dbAgent", "123")
    VNFIs = dibm.getAllVNFI()
    return VNFIs
    
def getAllVNFIsDictList(allVNFIsList):
    allVNFIsDictList = []
    vnfiID = 1
    for VNFIs in allVNFIsList:
        VNFIDict = {}
        VNFIDict['ID'] = vnfiID
        VNFIDict['VNFI_UUID'] = VNFIs.vnfiID
        VNFIDict['VNFIType'] = VNFIs.vnfType
        '''VNF_TYPE_CLASSIFIER = 0
VNF_TYPE_FORWARD = 1
VNF_TYPE_FW = 2
VNF_TYPE_IDS = 3
VNF_TYPE_MONITOR = 4
VNF_TYPE_LB = 5
VNF_TYPE_RATELIMITER = 6
VNF_TYPE_NAT = 7
VNF_TYPE_VPN = 8
VNF_TYPE_WOC = 9    # WAN Optimization Controller
VNF_TYPE_APPFW = 10 # http firewall
VNF_TYPE_VOC = 11
VNF_TYPE_DDOS_SCRUBBER = 12
VNF_TYPE_FW_RECEIVER = 13   # duplicate firewall in sfc
VNF_TYPE_NAT_RECEIVER = 14  # duplicate nat in sfc
# vnf type can't exceed 16, i.e. vnf type < 16
VNF_TYPE_MAX = 15'''
        VNFIDict['VNFIState'] = VNFIs.vnfiStatus
        allVNFIsDictList.append(VNFIDict)
        vnfiID = vnfiID + 1
    return allVNFIsDictList

def getDisplayedVNFIsListOnPage(VNFIs, pageNum):
    ps = PageSlicer()
    try:
        displayedVNFIs = ps.getObjsListOnPage(VNFIs, pageNum)
    except(EmptyPage, InvalidPage, PageNotAnInteger):
        displayedVNFIs = ps.getObjsListOnPage(VNFIs, 1)
    return displayedVNFIs 

@login_required
def showVNFIList(req):
    VNFIsTupleList = getAllVNFIsFromDataBase()
    VNFIs = getAllVNFIsDictList(VNFIsTupleList)
    pageNum = getPageNumFromHttpRequest(req)
    displayedVNFIsList = getDisplayedVNFIsListOnPage(VNFIs, pageNum)
    VNFIsNumPerPage = 11
    totalPageNum = getTotalPageNum(len(VNFIs), VNFIsNumPerPage)
    pageRange = getPageRange(pageNum, totalPageNum)
    numDict=getNumDict(pageNum, totalPageNum)
    print(pageNum)
    return render(req, 'VNFIlist.html',
            {'displayedVNFIsList' : displayedVNFIsList,
                'pageRange': pageRange,
                'totalPageNum': totalPageNum,
                'pageNum': pageNum,
                'numDict': numDict
            })