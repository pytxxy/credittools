# -*- coding:UTF-8 -*-

'''
Created on 2014年4月27日

@author: cfh
'''

import sys
import xml.dom.minidom as minidom
import re
import os
import time

import creditutils.apk_util as apk
import creditutils.file_util as myfile
import creditutils.hash_util as myhash
import argparse
import json
import pprint

_NAME_FLAG = 'name'
_VER_CODE_FLAG = 'versionCode'
_VER_NAME_FLAG = 'versionName'
 
class ApkConfigUpdater:
    
    def __init__(self, file_path):
        self.file_path = file_path
        
    # 更新配置文件中的相关信息
    def process(self, apk_path, apk_items, is_xml):
        if is_xml:
            self._update_xml_file(apk_path, apk_items)
        else:
            self._update_json_file(apk_path, apk_items)
    
    def _update_xml_file(self, apk_path, apk_items):
        header = myfile.read_file_first_line(self.file_path)
        
        dom = minidom.parse(self.file_path)
        root = dom.documentElement
        
        info_item = root.getElementsByTagName('info')[0]
        
        # 更新包名
        ver_item = info_item.getElementsByTagName('package')[0]
        ver_item.setAttribute('value', apk_items[_NAME_FLAG])
        
        # 更新版本号
        ver_item = info_item.getElementsByTagName('version')[0]
        ver_item.setAttribute('value', apk_items[_VER_CODE_FLAG])
        
        # 更新版本名称
        res_item = info_item.getElementsByTagName('release')[0]
#         res_item.setAttribute('value', time.strftime('%Y-%m-%d', time.localtime()))
        res_item.setAttribute('value', apk_items[_VER_NAME_FLAG])
        
        file_item = root.getElementsByTagName('file')[0]
        
        # 更新文件大小
        size_item = file_item.getElementsByTagName('size')[0]
        size_item.setAttribute('value', str(os.path.getsize(apk_path)))
        
        # 更新hash值
        sha1_item = file_item.getElementsByTagName('hash')[0]
        sha1_item.setAttribute('value', myhash.get_file_sha1(apk_path))
        
        # 更新md5值
        md5_item = file_item.getElementsByTagName('md5')[0]
        md5_item.setAttribute('value', myhash.get_file_md5(apk_path))
        
        # 修改指定项的文本使用该方式
#         item.childNodes[0].nodeValue = func(item.childNodes[0].nodeValue)
#         print(root.toxml())
        
        myfile.write_to_file(self.file_path, header + root.toxml(), 'utf-8')
    
    def _update_json_file(self, apk_path, apk_items):
        src = open(self.file_path, encoding='utf-8')
        with src:
            obj = json.load(src)
            
#             pprint.pprint(obj)
#             print('-'*160)
            
            info_item = obj['info']
        
            # 更新包名
            info_item['package'] = apk_items[_NAME_FLAG]
            
            # 更新版本号
            info_item['verCode'] = apk_items[_VER_CODE_FLAG]
            
            # 更新版本名称
            info_item['verName'] = apk_items[_VER_NAME_FLAG]
            
            file_item = obj['file']
            
            # 更新文件大小
            file_item['size'] = str(os.path.getsize(apk_path))
            
            # 更新hash值
            file_item['hash'] = myhash.get_file_sha1(apk_path)
            
            # 更新md5值
            file_item['md5'] = myhash.get_file_md5(apk_path)
        
        if obj:
            output = json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=4)
#             print(output)

            myfile.write_to_file(self.file_path, output, 'utf-8')
            
            print('generated ' + self.file_path)
            
        
# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='update upgrade config file.')
    parser.add_argument('config_path', metavar='config', help='upgrade config file for template or target when -u specified')
    parser.add_argument('publish_path', metavar='source', help='upgrade info source file path')
    parser.add_argument('-u', dest='is_update', action='store_true', default=False, help='indicate to update the config file')
    parser.add_argument('-x', dest='is_xml', action='store_true', default=False, help='indicate the config file type as xml, not default json')
    parser.add_argument('-m', dest='mode', action='store', default=None, help='indicate the environment mode, such as develop, test or produce')
    
#     parser.print_help()

    return parser.parse_args(src_args)    

def main(args):
    config_path = os.path.abspath(args.config_path)
    apk_path = os.path.abspath(args.publish_path)
    apk_items = apk.get_apk_info(apk_path)
    name_sep = '_'
    
    if not args.is_update:
        if args.is_xml:
            suffix = '.xml'
        else:
            suffix = '.json'
            
        dst_path = os.path.dirname(apk_path) + os.sep + apk_items[_NAME_FLAG] + name_sep + apk_items[_VER_CODE_FLAG]
        if args.mode:
            dst_path = dst_path + name_sep + args.mode.lower()
            
        dst_path = dst_path + suffix
        
        myfile.replace_file(config_path, dst_path)
    else:
        dst_path = config_path
    
    # 更新xml配置具体文件
    updater = ApkConfigUpdater(dst_path)
    updater.process(apk_path, apk_items, args.is_xml)
    
if __name__ == '__main__':
    # 用于显示获取 apk 相关信息
#     apk_items = apk.get_apk_info(apk_path)
#     print(apk_items)
    
    args = get_args()
    main(args)
    
    
    print('to the end')