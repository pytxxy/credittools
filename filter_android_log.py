import creditutils.file_util as myfile
import re
import os
import argparse
import time
from creditutils import str_util

def get_exception_info(file_path):
    begin_tag = '----- Exception Begin -----'
    end_tag = '-----  Exception End  -----'
    FIND_FAILED_INDEX = -1
    
    content = myfile.read_file_content(file_path, encoding_='utf-8')
    
    begin = content.find(begin_tag)
    if begin != FIND_FAILED_INDEX:
        exception_info = content[begin+len(begin_tag):]
        end = exception_info.find(end_tag)
        if end != FIND_FAILED_INDEX:
            exception_info = exception_info[:end]
            return exception_info
        
    return None

def get_feature(exception_info, prefix='com.pycredit'):
    re_ptn_str = '^\s+at\s+([^\r\n]+)[\r\n]+'
    re_ptn = re.compile(re_ptn_str, re.I | re.M)
    if exception_info:
        rlts = re_ptn.findall(exception_info)
#         print(rlts)
        if rlts:
            count = 0
            max_cnt = 2
            features = []
            if prefix:
                for item in rlts:
                    if item.startswith(prefix) and count < max_cnt:
                        features.append(item)
                        count += 1
            else:
                for item in rlts:
                    if count < max_cnt:
                        features.append(item)
                        count += 1
                    
            return '&&'.join(features)
        
    return None

def get_feature_with_path(file_path, prefix='com.pycredit'):
    exception_info = get_exception_info(file_path)
    return get_feature(exception_info, prefix)

class ProcessManager:
    def __init__(self, args):
        # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)
#         pprint.pprint(vars(self))
    
        self.classified = {}
        self.left_items = []
    
    def copy_item(self, src_path):
        pre_butt = len(self.src)
        if not self.src.endswith(os.sep):
            pre_butt += 1
            
        dst_path = os.path.join(self.dst, src_path[pre_butt:])
        myfile.replace_file(src_path, dst_path)
    
    def process(self):
        if os.path.isdir(self.src):
            myfile.process_dir(self.src, self.process_func)
            
            for key in self.classified:
                src_path = self.classified[key][0]
                self.copy_item(src_path)
                
            for item in self.left_items:
                self.copy_item(item)
        else:
            if not os.path.exists(self.src):
                raise Exception('{} not exists!'.format(self.src))
            else:
                raise Exception('{} unknown type file!'.format(self.src))
    
    def process_func(self, src_file):
        if os.path.isfile(src_file):
            exception_info = get_exception_info(src_file)
            if exception_info:
                script_pnt_str = '.*ScriptError\d+\.log$'
                match = re.match(script_pnt_str, src_file, re.I)
                if not match:
                    feature = get_feature(exception_info)
                    if feature:
                        if feature in self.classified:
                            sub_items = self.classified[feature]
                        else:
                            sub_items = []
                            self.classified[feature] = sub_items
                            
                        sub_items.append(src_file)
                        print('classify "{}" to "{}" success.'.format(src_file, feature))
                    else:
                        feature = get_feature(exception_info, prefix=None)
                        if feature:
                            if feature in self.classified:
                                sub_items = self.classified[feature]
                            else:
                                sub_items = []
                                self.classified[feature] = sub_items
                                
                            sub_items.append(src_file)
                            print('classify "{}" to "{}" success.'.format(src_file, feature))
                        else:
                            self.left_items.append(src_file)
                            print('classify "{}" to left items success.'.format(src_file))
                else:
                    print('classify "{}" to script error type item.'.format(src_file))
            else:
                print('classify "{}" to other type item.'.format(src_file))
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
    parser = argparse.ArgumentParser(description='filter android logs, remove duplicate item.')
    parser.add_argument('src', metavar='src', help='source file or directory')
    parser.add_argument('dst', metavar='dst', help='target file or directory')
    
#     parser.print_help()
    
    return parser.parse_args(src_args)

def test_01():
    file_path = r'E:\temp\crash\20170907\pycredit-log\CrashLog-20170906182954-SecurityException-HUAWEI(NTS-AL00)-3.2.0(351).log'
#     file_path = r'E:\temp\crash\20170907\pycredit-log\CrashLog-2017-09-06-15-34-11-ScriptError1504683251276.log'
    info = get_feature_with_path(file_path)
    print(info)
 
if __name__=='__main__':
    begin = time.time()
    
#     test_args = ''.split()
    test_args = None
    args = get_args(test_args)
    main(args)
    
    end = time.time()
    time_info = str_util.get_time_info(begin, end)
    
    #输出总用时
    print('===Finished. Total time: {}==='.format(time_info))