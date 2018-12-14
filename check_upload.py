'''
Created on 2017年9月20日

@author: caifh
'''

import pycurl
from io import BytesIO
import argparse
import time

import oss2

import creditutils.str_util as str_utils
import os
import re
import creditutils.file_util as myfile


def calculate_file_crc64(file_name, block_size=64 * 1024, init_crc=0):
    """计算文件的MD5
    :param file_name: 文件名
    :param block_size: 计算MD5的数据块大小，默认64KB
    :return 文件内容的MD5值
    """
    with open(file_name, 'rb') as f:
        crc64 = oss2.utils.Crc64(init_crc)
        while True:
            data = f.read(block_size)
            if not data:
                break
            crc64.update(data)

    return crc64.crc


def get_header_str(url):
    buffer = BytesIO()
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.HEADER, True)
    c.setopt(c.NOBODY, True)  # header only, no body
    c.setopt(c.WRITEDATA, buffer)
    c.perform()
    c.close()

    body = buffer.getvalue()
    #     print(body)
    return body.decode('utf-8')


def get_header_map(url):
    ptn_str = '([^:]+)\s*\:([^:]+)'
    ptn = re.compile(ptn_str)
    str_info = get_header_str(url)

    data = {}
    if str_info:
        lines = str_info.split('\r\n')
        for line in lines:
            match = ptn.match(line)
            if match:
                data[match.group(1).strip()] = match.group(2).strip()

    return data


class Header:
    content_length_label = 'Content-Length'
    date_label = 'Date'
    last_modified_label = 'Last-Modified'
    crc64 = 'x-oss-hash-crc64ecma'


class ProcessManager:
    def __init__(self, args):
        # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)
        #         pprint.pprint(vars(self))

        self.src = os.path.abspath(self.src)
        net_sep = '/'
        if not self.prefix.endswith(net_sep):
            self.prefix = self.prefix + net_sep
        self.right_list = []
        self.error_list = []

    def process(self):
        if os.path.isdir(self.src):
            myfile.process_dir(self.src, self.process_func)
        elif os.path.isfile(self.src):
            self.process_func(self.src)
        else:
            if not os.path.exists(self.src):
                raise Exception('{} not exists!'.format(self.src))
            else:
                raise Exception('{} unknown type file!'.format(self.src))

            #         if self.right_list:
            #             print('success upload files:')
            #             for item in self.right_list:
            #                 print(item)

        if self.error_list:
            print('failed to upload files:')
            for item in self.error_list:
                print(item)

    def process_func(self, src_file):
        if os.path.isfile(src_file):
            file_size = os.path.getsize(src_file)
            local_crc64 = calculate_file_crc64(src_file)
            file_url = self.prefix + os.path.basename(src_file)
            header = get_header_map(file_url)
            length = int(header[Header.content_length_label])
            oss_crc64 = int(header[Header.crc64])
            if file_size == length and local_crc64 == oss_crc64:
                print('file_size {} and crc64 {}'.format(file_size, local_crc64))
                self.right_list.append(src_file)
                print('success uploaded {}.'.format(src_file))
            else:
                self.error_list.append(src_file)
                print('failed to upload {}!'.format(src_file))
        else:
            if not os.path.exists(src_file):
                raise Exception('{} not exists!'.format(src_file))
            else:
                raise Exception('{} unknown type file!'.format(src_file))


def main(args):
    manager = ProcessManager(args)
    manager.process()


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='check uploaded file consistency')
    parser.add_argument('src', metavar='src', help='source file or directory')
    parser.add_argument('prefix', metavar='prefix', help='download url prefix')

    #     parser.print_help()

    return parser.parse_args(src_args)


if __name__ == '__main__':
    begin = time.time()

    #     test_args = ''.split()
    test_args = None
    args = get_args(test_args)
    main(args)

    end = time.time()
    time_info = str_utils.get_time_info(begin, end)

    # 输出总用时
    print('===Finished. Total time: {}==='.format(time_info))
