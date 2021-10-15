# Create your views here.
# -*- coding: utf-8 -*-
from django.core.paginator import PageNotAnInteger,  InvalidPage, EmptyPage
from django.shortcuts import render

from django.contrib.auth.decorators import login_required

from sam.dashboard.dashboardInfoBaseMaintainer import *
from sam.dashboard.base.pageSlicer import *


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

def getPageNumFromHttpRequest(req):
    try:    #如果请求的页码少于1或者类型错误，则跳转到第1页
        page = int(req.GET.get("page",1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1
    return page

def getAllUsersFromDataBase():
    dibm = DashboardInfoBaseMaintainer('localhost', 'dbAgent', '123')
    users = dibm.getAllUser()
    # users = dibm.getUserQuerySet()  #导入User表
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

def getNumDict(pageNum, totalPagenum):
    numDict={}
    if pageNum == 1:
        numDict['hasPreviousPage'] = False
    else:
        numDict['hasPreviousPage'] = True
    if pageNum == totalPagenum:
        numDict['hasNextPage'] = False
    else:
        numDict['hasNextPage'] = True
    numDict['nextPageNum'] = pageNum + 1
    numDict['previousPageNum'] = pageNum -1
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
    return render(req, 'userlist.html',
            {'displayedUsersList' : displayedUsersList,
                'pageRange': pageRange,
                'totalPageNum': totalPageNum,
                'pageNum': pageNum,
                'numDict': numDict
            })


