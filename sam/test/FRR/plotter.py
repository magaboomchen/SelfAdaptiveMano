#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
import os.path
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

import drawkit.figure_style as fs
from drawkit.figure_style import *


class Plotter(object):
    def __init__(self):
        self.X_TICK_SPACING = 10
        self.colorList = ['r','b','g','c','m','k','orange','plum','gold','lime']
        self.markerList = ['s','o','v','*','<','>',',']

    def drawThroughput(self, bandwidth, savePath):
        xticklabels = [str(x) for x in range(-5,100,5)]
        # xticklabels = range(-1,100,5)
        data_set=[bandwidth]
        line_name_set=['UFFR']
        xlabel_name='Time(s)'
        ylabel_name='Bandwidth(Mbps)'

        self.pointChart(data_set, savePath, line_name_set, xlabel_name, ylabel_name,
            x_tick_spacing = self.X_TICK_SPACING,
            figure_size=SMALL_FIGURE_SIZE, xticklabels=xticklabels)

    def drawDropRate(self, dropRateList, line_name_set, savePath):
        xticklabels = [str(x) for x in range(-5,100,5)]
        # xticklabels = range(-1,100,5)
        data_set = dropRateList
        xlabel_name ='Time(s)'
        ylabel_name ='DropRate(%)'

        self.pointChart(data_set, savePath, line_name_set,
            xlabel_name, ylabel_name,
            vLineList=[(8*2,0,100),(24*2,0,100)],
            figText=[(0.27, 0.7, "Link Failure"),
                (0.63, 0.7, "Server Failure")],
            x_tick_spacing=self.X_TICK_SPACING,
            xmin_limit=0, xmax_limit=70,
            ymin_limit=1, ymax_limit=0,
            grid_on=True, tight=False,
            figure_size=SMALL_FIGURE_SIZE, xticklabels=xticklabels,
            color_list=self.colorList, marker_list=self.markerList)

    def drawE2EDelay(self, delayList, line_name_set, savePath):
        xticklabels = [str(x) for x in range(-5,100,5)]
        # xticklabels = range(-1,100,1)
        print(xticklabels)
        data_set = delayList
        xlabel_name = 'Time(s)'
        ylabel_name = 'Delay(ms)'

        self.pointChart(data_set, savePath, line_name_set,
            xlabel_name, ylabel_name,
            vLineList=[(8*2,20,60),(24*2,20,60)],
            figText=[(0.27, 0.7, "Link Failure"),
                (0.63, 0.7, "Server Failure")],
            x_tick_spacing=self.X_TICK_SPACING,
            xmin_limit=0, xmax_limit=70,
            ymin_limit=1, ymax_limit=0,
            grid_on=True, tight=False,
            figure_size=SMALL_FIGURE_SIZE, xticklabels=xticklabels,
            color_list=self.colorList, marker_list=self.markerList)

    def pointChart(self, data_set,
            savepath, line_name_set,
            xlabel_name, ylabel_name,
            vLineList=None, hLineList=None,
            figText=None,
            title_name='', xticklabels=' ',
            figure_size=fs.LINEof3_FIGURE_SIZE,
            x_tick_spacing=-1,
            y_tick_spacing=-1,
            xmin_limit=1, xmax_limit=0,
            ymin_limit=1, ymax_limit=0,
            grid_on=False, tight=True,
            xscale_value='None',
            yscale_value='None',
            color_list= [], linestyle_list = [],
            marker_list = [], patterns_tuple = ()
        ):

        # draw the figure
        fig,ax=plt.subplots(figsize=figure_size)

        line_set_type=len(line_name_set)  # line_set的种类
        #print(line_set_type)
        if line_set_type==1 and len(data_set) != 1:
            # 特殊情况，只有一种line，输入格式可能是一维list，需要改成二维list
            data_set=[data_set]
        lines_n=len(data_set[0])
        index=np.arange(0,0+lines_n,1)

        # set figure style
        mycolor = []
        mylinestyle = []
        mymarker = []
        mypatterns =()

        if color_list == []:
            mycolor = fs.mycolor
        else:
            mycolor = color_list
        if linestyle_list == []:
            mylinestyle = fs.mylinestyle
        else:
            mylinestyle = linestyle_list
        if marker_list == []:
            mymarker = fs.mymarker
        else:
            mymarker = marker_list
        if patterns_tuple == ():
            mypatterns = fs.patterns
        else:
            mypatterns = patterns_tuple

        for i in range(line_set_type):
            ax.plot(index,data_set[i], color=mycolor[i], linestyle=mylinestyle[i],
                linewidth=fs.LINE_WIDTH, 
                label=line_name_set[i],
                marker=mymarker[i], markeredgecolor=mycolor[i], 
                markerfacecolor=(1, 1, 1, 1), markersize=fs.MARKER_SIZE,
                markeredgewidth=fs.MARKEREDGE_WIDTH)

        # vertical line
        if vLineList != None:
            for vLine in vLineList:
                (x, ymin, ymax) = vLine
                plt.vlines(x, ymin, ymax, colors = "orange", linestyles = "dashed")

        # fig text
        for fText in figText:
            (xPosition, yPosition, text) = fText
            plt.figtext(xPosition, yPosition, text,
                fontsize=fs.LEGEND_SIZE, fontweight='bold', rotation="vertical", color="orange")

        # legend
        legend = ax.legend(fontsize=fs.LEGEND_SIZE, edgecolor='k')
        frame = legend.get_frame()
        frame.set_linewidth(fs.LEGEND_EDGE_WIDTH)
        if grid_on == True:
            ax.grid(linestyle='--', linewidth=fs.GRID_WIDTH)
        ax.set_axisbelow(True)

        #print(data_set)
        #print(index)
        # set xticks
        if xticklabels!=' ':
            #print(xticklabels)
            ax.set_xticks(index)
            ax.set_xticklabels(xticklabels)

        #delete the upper and right frame
        #ax.spines['right'].set_visible(False)
        #ax.spines['top'].set_visible(False)

        #set x(y) axis (spines)
        ax.spines['bottom'].set_linewidth(fs.XY_SPINES_WIDTH)
        ax.spines['bottom'].set_color('k')
        ax.spines['left'].set_linewidth(fs.XY_SPINES_WIDTH)
        ax.spines['left'].set_color('k')

        # set x(y) scale
        if xscale_value != 'None':
            plt.xscale(xscale_value)
        if yscale_value != 'None':
            plt.yscale(yscale_value)

        # set x(y) limits
        if xmin_limit<=xmax_limit:
            ax.set_xlim(xmin=xmin_limit,xmax=xmax_limit)
        if ymin_limit<=ymax_limit:
            ax.set_ylim(ymin=ymin_limit,ymax=ymax_limit)

        #set x(y) label
        plt.xlabel(xlabel_name,fontweight='normal',fontsize=fs.XY_LABEL_SIZE,fontname="Times New Roman",color='k',horizontalalignment='center',x=0.5)
        ax.xaxis.labelpad = 2.5
        plt.ylabel(ylabel_name,fontweight='normal',fontsize=fs.XY_LABEL_SIZE,fontname="Times New Roman",color='k',horizontalalignment='center',y=0.5)
        ax.yaxis.labelpad = 2.5
        plt.title(title_name,fontweight='normal',fontsize=fs.TITLE_SIZE,fontname="Times New Roman",color='k',horizontalalignment='center',x=0.5,y=1)

        for tick in ax.xaxis.get_major_ticks():
            tick.label.set_fontsize(fs.TICK_LABEL_SIZE)
            tick.label.set_fontweight('normal')#tick.label.set_rotation('vertical')
            tick.label.set_color('k')

        for tick in ax.yaxis.get_major_ticks():
            tick.label.set_fontsize(fs.TICK_LABEL_SIZE)
            tick.label.set_fontweight('normal')#tick.label.set_rotation('vertical')
            tick.label.set_color('k')

        ax.tick_params(direction='in')

        # tick density
        if x_tick_spacing>=0:
            ax.xaxis.set_major_locator(ticker.MultipleLocator(x_tick_spacing))
        if y_tick_spacing>=0:
            ax.yaxis.set_major_locator(ticker.MultipleLocator(y_tick_spacing))

        # save figure
        if tight==True:
            fig.tight_layout()
        plt.savefig(savepath)
        #plt.show()
        plt.close('all')
        return 0