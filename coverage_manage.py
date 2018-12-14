'''
Created on 2017年8月2日

@author: caifh
'''
import argparse
import time
from creditutils import str_util
import os
import creditutils.exec_cmd as exec_cmd
import creditutils.file_util as myfile

_PACK_TYPE_REINSTALL = 0 # 重新安装
_PACK_TYPE_INSTALL = 1 # 直接安装

class Manager:
    def __init__(self, args):
        # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)
    
        self.work_path = os.path.abspath(self.work_path)
        self.src_path = os.path.abspath(self.src_path)
        
        self.bin_dir_name = 'bin'
        self.bin_path = os.path.join(self.work_path, self.bin_dir_name)
        self.main_bin_name = os.path.basename(self.work_path)
#         self.start_bin_name = 'run_server'
#         self.stop_bin_name = 'stop_server'
        
    def process(self):
        if self.to_compile:
            build_cmd = 'go build'
            exec_cmd.run_cmd_for_code_in_specified_dir(self.src_path, build_cmd, print_flag=True)
            
        # 如果有需要则先停止服务
        if self.type == _PACK_TYPE_REINSTALL:
#             stop_cmd = os.path.join(self.bin_path, self.stop_bin_name)
#             exec_cmd.run_cmd_for_code_in_specified_dir(self.work_path, stop_cmd, print_flag=True)

            stop_cmd = 'kill -9 $(pgrep {}) > /dev/null 2>&1'.format(self.main_bin_name)
            exec_cmd.run_cmd_with_system_in_specified_dir(self.work_path, stop_cmd, print_flag=True)
            
        # 更新可执行文件
        src_path = os.path.join(self.src_path, self.main_bin_name)
        dst_path = os.path.join(self.bin_path, self.main_bin_name)
        myfile.replace_file(src_path, dst_path)
        
        # 增加可执行权限
        add_permission_cmd = 'chmod a+x {}'.format(self.main_bin_name)
        exec_cmd.run_cmd_with_system_in_specified_dir(self.bin_path, add_permission_cmd, print_flag=True)
        
        # 启动服务
        start_cmd = os.path.join(os.path.join('.', self.bin_dir_name), self.main_bin_name)
        exec_cmd.run_cmd_with_system_in_specified_dir(self.work_path, start_cmd, print_flag=True)

# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='reinstall coverage.')
    parser.add_argument('work_path', metavar='work_path', help='working directory')
    parser.add_argument('src_path', metavar='src_path', help='source project directory')
    parser.add_argument('-c', dest='to_compile', action='store_true', default=False, help='indicate to compile source code firstly')
    
    src_group = parser.add_mutually_exclusive_group()
    src_group.add_argument('-r', dest='type', action='store_const', default=_PACK_TYPE_REINSTALL, const=_PACK_TYPE_REINSTALL, help='indicate to reinstall which must stop the server and replace the binary')
    src_group.add_argument('-i', dest='type', action='store_const', default=_PACK_TYPE_REINSTALL, const=_PACK_TYPE_INSTALL, help='indicate to just install')
    
#     parser.print_help()

    return parser.parse_args(src_args)    

def main(args):
    manager = Manager(args)
    manager.process()
    
if __name__ == '__main__':
    begin = time.time()
    
    test_args = None
    args = get_args(test_args)
    main(args)
    
    end = time.time()
    time_info = str_util.get_time_info(begin, end)
    
    #输出总用时
    print('===Finished. Total time: {}==='.format(time_info))