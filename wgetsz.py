#!/usr/bin/python3

'''
Created on 2017年8月5日

@author: caifh
'''
import subprocess
import re
import os
import sys
import argparse
import time


# import wget

# 获取以秒为单位的两个时间点之间的差值，返回以XXmXXs的时间格式字符串
def get_time_info(begin, end):
    elapsed = end - begin
    sec_per_min = 60
    m = elapsed // sec_per_min
    s = elapsed % sec_per_min
    time_info = '{}m{}s'.format(round(m), round(s))
    return time_info


# 通过url地址下载文件到服务器
def get_file(url):
    # 该方式实现相对优雅，3.5及以后的版本才支持"run"方法
    cmd_str = 'wget "{}"'.format(url)
    cp = subprocess.run(cmd_str, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    result = cp.stdout

    # 该方式也可以达到想要的效果
    # proc = subprocess.Popen(cmd_str, shell=True,  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    # result, _ = proc.communicate()

    print(result)
    ptn_str = '‘([^‘’]+)’\s+saved'
    ptn = re.compile(ptn_str, flags=(re.I | re.M))
    match = ptn.search(result)
    value = None
    if match:
        value = match.group(1)

    # print('name: ', value)

    return value


def download(file_name):
    cmd_str = 'sz {}'.format(file_name)
    # print(os.getcwd())
    print(cmd_str)
    subprocess.check_call(cmd_str.split())


def process(url):
    file_name = get_file(url)
    # file_name = wget.download(url)
    download(file_name)


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(
        description='In remote host, first get file with "wget" command, then use "sz" comand to download the file got to local host.')

    parser.add_argument('url', metavar='url', help='the url address to download file.')

    #     parser.print_help()

    return parser.parse_args(src_args)


def main(args):
    process(args.url)


if __name__ == '__main__':
    begin = time.time()

    test_args = None
    args = get_args(test_args)
    main(args)

    end = time.time()
    time_info = get_time_info(begin, end)

    # 输出总用时
    print('===Finished. Total time: {}==='.format(time_info))
