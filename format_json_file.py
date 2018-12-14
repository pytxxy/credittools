# -*- coding:UTF-8 -*-

'''
Created on 2015年5月8日

@author: caifh
'''
import json
import creditutils.file_util as myfile
import argparse
import os

def format_json_file(filepath):
    src = open(filepath, encoding='utf-8')
    with src:
        obj = json.load(src)
        
#             pprint.pprint(obj)
#             print('-'*160)
    
    if obj:
        output = json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=4)
#         print(output)

        myfile.write_to_file(filepath, output, 'utf-8')

# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='format json file with indent.')
    parser.add_argument('filepath', metavar='file', help='the target json file to format')
    
#     parser.print_help()

    return parser.parse_args(src_args)    

def main(args):
    filepath = os.path.abspath(args.filepath)
    format_json_file(filepath)
    
    
if __name__ == '__main__':
    args = get_args()
    main(args)
    
    print('to the end')