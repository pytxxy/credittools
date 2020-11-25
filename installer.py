# -*- coding:UTF-8 -*-

'''
Created on 2014年4月27日

@author: cfh
'''
import argparse
import os
import subprocess

import creditutils.apk_util as apk_util
import creditutils.trivial_util as util
import sys


def uninstall(package):
    if not (package and isinstance(package, str)):
        raise Exception(f'package name {package} is invalid!')

    cmd_str = f'adb uninstall {package}'
    print(cmd_str)
    subprocess.run(cmd_str, shell=True)


def install(apk_path):
    if not os.path.isfile(apk_path):
        raise Exception(f'{apk_path} is not a file!')

    cmd_str = f'adb install {apk_path}'
    print(cmd_str)
    subprocess.run(cmd_str, check=True, shell=True)


def main(args):
    apk_path = os.path.abspath(args.src)
    apk_items = apk_util.get_apk_info(apk_path)
    package = apk_items['name']
    uninstall(package)
    install(apk_path)


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='one tool that can install android apk.')
    parser.add_argument('src', metavar='src',
                        help='source android apk file')

    return parser.parse_args(src_args)


if __name__ == '__main__':
    test_args = None
    input_args = get_args(test_args)
    util.measure_time(main, input_args)
