# -*- coding:UTF-8 -*-

'''
Created on 2014年4月27日

@author: cfh
'''

import re
import os

import creditutils.file_util as myfile
import argparse
import json
import pprint

_NAME_FLAG = 'name'
_VER_CODE_FLAG = 'versionCode'
_VER_NAME_FLAG = 'versionName'
 
class JsonConfigUpdater:
    INTERFACE_FLAG = 'interface'
    ID_FLAG = 'id'
    
    def __init__(self, file_path, is_pure):
        self.file_path = file_path
        self.is_pure = is_pure
        
        
    # 更新配置文件中的相关信息
    def process(self):
        self._update_json_file()
    
    
    def _update_json_file(self):
        src = open(self.file_path, encoding='utf-8')
        with src:
            obj = json.load(src)
            if self.is_pure:
                src_obj = obj
            else:
                src_obj = obj["interface"]
        
        src_obj = self._sort_array(src_obj)
#         src_obj.sort(key=self._cmp_item)
        
        if src_obj:
#             output = json.dumps(src_obj, ensure_ascii=False, sort_keys=True, indent=4)
#             output = re.sub('("describe":\s*"[^"]*")(\s*,\s+)("id":\s*"[^"]*")(\s*,)', self._replace_ptn, output)
            output = self._join_array(src_obj)
#             print(output)

        
        if not self.is_pure:
            src_content = myfile.read_file_content(self.file_path)
            self.array_str = output
            output = re.sub('("interface":\s*)(\[[^\]]*\])', self._replace_dst_ptn, src_content)
            
#         print('-' * 120)
#         print(output)
        myfile.write_to_file(self.file_path, output, 'utf-8')

    def _sort_array(self, src_array):
        recs = {}
        sort_src = []
        uniq_src = set()
        dst = []
        for item in src_array:
            index = int(item[JsonConfigUpdater.ID_FLAG])
            if index not in uniq_src:
                sort_src.append(index)
                uniq_src.add(index)
                recs[index] = item
            
        sort_src.sort()
        for key in sort_src:
            dst.append(recs[key])
            
        return dst
    
    def _cmp_item(self, item):
        return item[JsonConfigUpdater.ID_FLAG]

    def _replace_ptn(self, match):
        return match.group(3) + match.group(2) + match.group(1) + match.group(4)
    
    def _replace_dst_ptn(self, match):
        return match.group(1) + self.array_str
    
    def _join_array(self, src_array):
        src_strs = []
        for item in src_array:
            src_strs.append(self._join_item(item))
            
        array_format = '[\r\n{}'  + '\r\n' + ']'
        return array_format.format(',\r\n'.join(src_strs))
    
    def _join_item(self, item):
        item_format = ' ' * 8 + '{{\r\n{}'  + '\r\n' + ' ' * 8 + '}}'
        line_format = ' ' * 16 + '"{}": "{}"'
        line_ori_format = ' ' * 16 + '"{}": {}'
        line_order = ['id', 'describe', 'protocol', 'path', 'connTimeout', 'socketTimeout', 'encrypt']
        src_strs = []
        for line_name in line_order:
            if line_name in item:
                if type(item[line_name]) == str:
                    src_strs.append(line_format.format(line_name, item[line_name]))
                else:
                    src_strs.append(line_ori_format.format(line_name, item[line_name]))
                
        return item_format.format(',\r\n'.join(src_strs))
        
# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='sort json config array file.')
    parser.add_argument('config_path', metavar='config', help='upgrade thie json array config file')
    parser.add_argument('-p', dest='is_pure', action='store_true', default=False, help='indicate to update pure json array file')
    
#     parser.print_help()

    return parser.parse_args(src_args)    

def main(args):
    config_path = os.path.abspath(args.config_path)
    
    # 更新xml配置具体文件
    updater = JsonConfigUpdater(config_path, args.is_pure)
    updater.process()

    
if __name__ == '__main__':
    args = get_args()
    main(args)
    
    # 排序测试
#     persons=[{'name':'zhang3','age':15},{'name':'li4','age':12}]
#     pprint.pprint(persons)
#     persons.sort(key=lambda a:a['age'])
#     pprint.pprint(persons)
    
    
    print('to the end')