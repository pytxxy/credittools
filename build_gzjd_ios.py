# -*- coding:UTF-8 -*-
import os
import time
import argparse
import creditutils.file_util as myfile
import build_base_ios as build_base
import creditutils.str_util as str_utils
    

class BuildManager(build_base.BuildManager):   
    def pre_build(self):
        # 先恢复正常的编译配置
        reinit_config_script_path = self.project_path + os.sep + 'GZJD/init.rb'
        reinit_config_script_path = myfile.normalpath(reinit_config_script_path)
        # 执行初始化恢复操作
        str_format = 'ruby {}'
        cmd_str = str_format.format(reinit_config_script_path)
        print(cmd_str)
        os.system(cmd_str)
        # 更新版本名称及编译编号
        info_plist_path = self.project_path + os.sep + self.ori_build_config[build_base.BuildConfigParser.WORKSPACE_FLAG][build_base.BuildConfigParser.INFO_PLIST_FLAG]
        info_plist_path = myfile.normalpath(info_plist_path)
        
        build_base.update_build_no(info_plist_path, self.ver_code)
        build_base.update_version_name(info_plist_path, self.ver_name)
        
def main(args):
    manager = BuildManager(args)
    manager.process()

# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='update code, build.')
    parser.add_argument('work_path', metavar='work_path', help='working directory')
    
    parser.add_argument('-c', metavar='base_config', dest='base_config', help='base configure file, path relative to work path')
    parser.add_argument('-u', dest='to_update', action='store_true', default=False, help='indicate to get or update code firstly')
    parser.add_argument('-b', dest='to_build', action='store_true', default=False, help='indicate to build')
    parser.add_argument('-v', metavar='code_ver', dest='code_ver', action='store', default=None,
                        help='indicate updating to special code version')
    parser.add_argument('--git', dest='use_git', action='store_true', default=False,
                        help='indicate to use git update code')
    
    parser.add_argument('--vername', metavar='ver_name', dest='ver_name', help='version name')
    parser.add_argument('--vercode', metavar='ver_code', dest='ver_code', help='version code')
    parser.add_argument('--verenv', metavar='ver_env', dest='ver_env', type=str, choices=['dev', 'test', 'pre', 'pro', 'flight'], help='dev: develop environment; test: test environment; pre: pre-release environment; pro: production environment; flight: Testflight;')
    parser.add_argument('--vertype', metavar='ver_type', dest='ver_type', type=str, choices=['e', 'p'], help='e: enterprise; p: personal;')
    parser.add_argument('--upload', dest='to_upload_sftp', action='store_true', default=False,
                        help='need to upload to sftp Server;')
    parser.add_argument('--branch', metavar='branch', dest='branch', help='branch name')
#     parser.print_help()

    return parser.parse_args(src_args)    
     
if __name__=='__main__':
    begin = time.time()
    test_args = None
    args = get_args(test_args)
    main(args)
    end = time.time()
    
    time_info = str_utils.get_time_info(begin, end)
    
    #输出总用时
    print('===Finished. Total time: {}==='.format(time_info))
