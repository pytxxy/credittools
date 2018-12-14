# -*- coding:UTF-8 -*-

'''
Created on 2014年4月27日

@author: cfh
'''
import argparse
import os

import creditutils.apk_util as apk_util
import creditutils.trivial_util as util
import sys


def main(args):
    apk_path = os.path.abspath(args.src)
    apk_items = apk_util.get_apk_info(apk_path)
    # print(apk_items)

    str_format = 'package: {0}, name: {1}, version: {2}, verCode: {3}'
    str_info = str_format.format(apk_items['name'], apk_items['label'], apk_items['versionName'],
                                 apk_items['versionCode'])
    print(str_info)


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='get information of android apk file.')
    parser.add_argument('src', metavar='src',
                        help='source android apk file')

    return parser.parse_args(src_args)


if __name__ == '__main__':
    test_args = None
    input_args = get_args(test_args)
    util.measure_time(main, input_args)
