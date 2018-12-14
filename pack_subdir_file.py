# -*- coding:UTF-8 -*-

'''
Created on 2017年6月3日

@author: caifh
'''
import argparse
import os
import re
import creditutils.zip_util as zip
import creditutils.trivial_util as utility
import creditutils.file_util as myfile

class PackManager:
    _PACK_SIZE_PTN = '^([1-9]\d*)([kKmMgG]?)$'
    _SIZE_OF_K = 1024
    _SIZE_OF_M = _SIZE_OF_K * _SIZE_OF_K
    _SIZE_OF_G = _SIZE_OF_K * _SIZE_OF_K * _SIZE_OF_K
    _UNIT_SIZE_MAP = {
      'k': _SIZE_OF_K,
      'm': _SIZE_OF_M,
      'g': _SIZE_OF_G
    }
    _DST_NAME_FORMAT = '{}_{:02d}.zip'
    
    def __init__(self, args):
    # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)
    
        self.src = os.path.abspath(self.src)
        self.dst = os.path.abspath(self.dst)
        if self.config:
            self.config = os.path.abspath(self.config)
            self.file_list = myfile.read_valid_string_list_from_file(self.config)
        else:
            self.file_list = None
        
        if not self.name_pre:
            self.name_pre = os.path.basename(self.src)
            
        if not self.max_size and not self.max_num:
            raise Exception('Must specify one of max_size or max_num!')
        elif self.max_num:
            self.num_limit = self.max_num
            if self.num_limit <= 0:
                raise Exception('The value of num_limit must greater than 0, but the current value is {}!'.format(self.num_limit))
        elif self.max_size:
            self.size_limit = self._get_max_pack_size(self.max_size)
            if self.size_limit <= 0:
                raise Exception('The value of size_limit must greater than 0, but the current value is {}!'.format(self.size_limit))
        
    def _get_max_pack_size(self, size_str):
        match_rlt = re.match(PackManager._PACK_SIZE_PTN, size_str)
        if match_rlt:
            count = int(match_rlt.group(1))
            unit_flag = match_rlt.group(2)
            unit = 1
            if unit_flag:
                unit = PackManager._UNIT_SIZE_MAP[unit_flag.lower()]
                
            return count * unit
        else:
            raise Exception('{} is invalid max size information!'.format(size_str))
    
    def _get_file_list(self, src_dir):
        target_list = []
        sub_list = os.listdir(src_dir)
        for item in sub_list:
            if self.file_list:
                name, ext = os.path.splitext(item)
                if name not in self.file_list:
                    continue
                    
            item_path = os.path.join(src_dir, item)
            if os.path.isfile(item_path):
                target_list.append(item)
                
        return target_list
    
    def process(self):
        if self.max_num:
            self.process_with_max_number_limit()
#             pass
        else:
            self.process_with_max_size_limit()
#             pass
    
    def process_with_max_number_limit(self):
        target_list = self._get_file_list(self.src)
        i = 0
        index = 1
        filelist = []
        
        for item in target_list:
            item_path = os.path.join(self.src, item)
            i += 1
            
            if i < self.num_limit:
                filelist.append(item_path)
            elif i == self.num_limit:
                filelist.append(item_path)
                
                dst_path = os.path.join(self.dst, PackManager._DST_NAME_FORMAT.format(self.name_pre, index))
                zip.zip_files(filelist, dst_path, self.src, to_print=True)
                
                i = 0
                index += 1
                filelist = []
            else:
                raise Exception('It is impossible to get here!')
        
        if filelist:
            dst_path = os.path.join(self.dst, PackManager._DST_NAME_FORMAT.format(self.name_pre, index))
            zip.zip_files(filelist, dst_path, self.src, to_print=True)
                    
    def process_with_max_size_limit(self):
        target_list = self._get_file_list(self.src)
        total = 0
        index = 1
        filelist = []
        
        for item in target_list:
            item_path = os.path.join(self.src, item)
            item_size = os.path.getsize(item_path)
            curr_total = total + item_size
            if curr_total <= self.size_limit:
                filelist.append(item_path)
                total = curr_total
            else:
                if filelist:
                    dst_path = os.path.join(self.dst, PackManager._DST_NAME_FORMAT.format(self.name_pre, index))
                    zip.zip_files(filelist, dst_path, self.src, to_print=True)
                            
                    index += 1
                    filelist = []
                    filelist.append(item_path)
                    total = item_size
                else:
                    raise Exception('{} size {} is large than {}!'.format(item_path, item_size, self.size_limit))
        
        if filelist:
            dst_path = os.path.join(self.dst, PackManager._DST_NAME_FORMAT.format(self.name_pre, index))
            zip.zip_files(filelist, dst_path, self.src, to_print=True)
            
# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='pack the files of primary sub directory.')
    
    parser.add_argument('src', metavar='src', help='the source directory to pack.')
    parser.add_argument('dst', metavar='dst', help='the destine directory to store.')
    parser.add_argument('-p', metavar='name_pre', dest='name_pre', action='store', default=None, help='the prefix of specify target packed file name')
    parser.add_argument('-c', metavar='config', dest='config', action='store', default=None,
                        help='the configure file from which to read item record to pack.')

    limit_group = parser.add_mutually_exclusive_group()
    limit_group.add_argument('--number', metavar='max_num', dest='max_num', type=int, default=None, help='the max total size of all files to pack as one packed file.')
    limit_group.add_argument('--size', metavar='max_size', dest='max_size', default=None, help='the max total size of all files to pack as one packed file.')

#     parser.print_help()

    return parser.parse_args(src_args)    

def main(args):
    manager = PackManager(args)
    manager.process()

    
if __name__ == '__main__':
#     test_args = 'a b -i -u'.split()
    test_args = None
    args = get_args(test_args)
    utility.measure_time(main, args)
