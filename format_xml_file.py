# -*- coding:UTF-8 -*-

'''
Created on 2015年11月23日

@author: caifh
'''

import creditutils.file_util as myfile
from xml.dom import minidom
import argparse
import os
from xml.etree import ElementTree

def indent(elem, level=0):
    interval = "  "
    i = "\n" + level*interval
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + interval
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def format_xml_file(file_path):
    header = myfile.read_file_first_line(file_path)
    root = ElementTree.parse(file_path).getroot()
    indent(root)
#     ElementTree.dump(root)
    content = ElementTree.tostring(root,'utf-8').decode()
#     print(content)
    myfile.write_to_file(file_path, header + content, 'utf-8')

def format_xml_file_for_pretty(file_path):
    header = myfile.read_file_first_line(file_path)
    
    dom = minidom.parse(file_path)
    root = dom.documentElement
    
    pretty_xml_str = root.toprettyxml()
#         print(pretty_xml_str)
    myfile.write_to_file(file_path, header + pretty_xml_str, 'utf-8')
        
        
# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='format xml file.')
    parser.add_argument('file', metavar='file', help='format xml file')
    
#     parser.print_help()

    return parser.parse_args(src_args)    

def main(args):
    file_path = os.path.abspath(args.file)
    
    if os.path.exists(file_path):
        format_xml_file(file_path)
    else:
        info = '{} not exists'.format(file_path)
        print(info)
        
        
if __name__ == '__main__':
    # 用于显示获取 apk 相关信息
#     apk_items = apk.get_apk_info(apk_path)
#     print(apk_items)
    
    args = get_args()
    main(args)
    
    
    print('to the end')