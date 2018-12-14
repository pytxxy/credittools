# -*- coding:UTF-8 -*- # 标识为


import sys,os
import creditutils.base_util as base

def func_flag():
    pass # do stuff

global __modpath__
__modpath__ = base.module_path(func_flag)

def getpath():
    path_getcwd = os.getcwd()
    path_realpath = os.path.split(os.path.realpath(__modpath__))[0]
    path_abspath = os.path.split(os.path.abspath(sys.argv[0]))[0]
    path_syspath = sys.path[0]
    print(("path_getcwd is: %s" %path_getcwd))
    print(("path_realpath is: %s " %path_realpath))
    print(("path_abspath is: %s " %path_abspath))
    print(("path_sys is: %s" %path_syspath))


if __name__ == '__main__':
    getpath()