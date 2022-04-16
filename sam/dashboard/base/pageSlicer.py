# Create your views here.
# -*- coding: utf-8 -*-


# class DisplayedObj(object):
#     def __init__(self, displayedList, totalList, displayedPageNum):
#         self.list = displayedList
#         self.number = displayedPageNum
#         if len(totalList)%11 == 0:
#             self.totalNumber = int((len(totalList) - len(totalList)%11)/11)
#         else:
#             self.totalNumber = int((len(totalList) - len(totalList)%11)/11+1)
#         if displayedPageNum == 1:
#             self.has_previous = False
#         else:
#             self.has_previous = True
#         if displayedPageNum*11 >= self.totalNumber:
#             self.has_next = False
#         else:
#             self.has_next = True


class PageSlicer(object):
    def __init__(self):
        pass

    def getObjsListOnPage(self, objs, displayedPageNum):
        startObjNum = (displayedPageNum-1)*11
        endObjNum = min(displayedPageNum*11-1, len(objs)-1)
        # displayedObjs = DisplayedObj (objs[startObjNum: endObjNum+1], objs, displayedPageNum)
        return objs[startObjNum: endObjNum+1]
        # return displayedObjs

