# -*- coding:UTF-8 -*-
'''
Created on 2017年5月30日

@author: caifh
'''

import os
import creditutils.file_util as myfile
import argparse
import creditutils.trivial_util as utility

def copy_specified_item(src_dir, dst_dir, file_list_path):
    if not os.path.exists(src_dir):
        raise Exception('{} not exists!'.format(src_dir))
    
    if not os.path.exists(file_list_path):
        raise Exception('{} not exists!'.format(file_list_path))
    
    file_list = myfile.read_valid_string_list_from_file(file_list_path)
#     print(file_list)
    src_itmes = os.listdir(src_dir)
    if src_itmes:
        for item in src_itmes:
            curr_path = os.path.join(src_dir, item)
            if os.path.exists(curr_path) and os.path.isfile(curr_path):
                root, ext = os.path.splitext(item)
                if root in file_list:
                    src_path = os.path.join(src_dir, item)
                    dst_path = os.path.join(dst_dir, item)
                    myfile.replace_file(src_path, dst_path)
                    str_info = 'copy {} to {}.'.format(src_path, dst_path)
                    print(str_info)

# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='copy specified items.')
    parser.add_argument('src', metavar='src', help='the source directory to copy.')
    parser.add_argument('dst', metavar='dst', help='the destine directory to store.')
    parser.add_argument('config', metavar='config', help='the configure file from which to read item record.')
    
#     parser.print_help()

    return parser.parse_args(src_args)

def main(args):
    copy_specified_item(args.src, args.dst, args.config)
    
if __name__ == '__main__':
#     src_dir = r'E:\apk\3.1.0\channel_normal'
#     dst_dir = r'E:\apk\3.1.0\channel_to_upload'
#     file_list_path = r'E:\repository\build_script_ori\android\pytxxy\config\channel\V3.0.0\to_upload_20170530.non'
#     test_args = '{} {} {}'.format(src_dir, dst_dir, file_list_path).split()
    test_args = None
    args = get_args(test_args)
    utility.measure_time(main, args)