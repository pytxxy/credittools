# -*- coding:UTF-8 -*-
import os
import time
import argparse
import creditutils.file_util as myfile
import filecmp
import build_base_ios as build_base
import creditutils.str_util as str_utils
import creditutils.exec_cmd as exec_cmd
from datetime import datetime

class BuildConfigParser(build_base.BuildConfigParser):
    pass

class BuildManager(build_base.BuildManager):
    def pre_build(self):
        # 在需要更新代码条件下先进行pod update更新操作
        if self.to_update and self.use_git:
            # 执行"pod install"下载新增的库配置,在执行pod update更新相关的库
            pod_path = self.pods_path
            pod_path = myfile.normalpath(pod_path)
            cmd_update_local_pod = 'pod repo update PYPodSpec'
            cmd_str = 'pod install'
            cmd_update_str = 'pod update --no-repo-update'
            pods_path = pod_path + os.sep + 'Pods'
            pods_path = myfile.normalpath(pods_path)
            exec_cmd.run_cmd_with_system_in_specified_dir(pod_path, cmd_update_local_pod, print_flag=True)
            if os.path.exists(pods_path):
                exec_cmd.run_cmd_with_system_in_specified_dir(pod_path, cmd_update_str, print_flag=True)
            else:
                exec_cmd.run_cmd_with_system_in_specified_dir(pod_path, cmd_str, print_flag=True)
            
        # 先恢复正常的编译配置
        reinit_config_script_path = self.init_ruby_path
        reinit_config_script_path = myfile.normalpath(reinit_config_script_path)
        # 执行初始化恢复操作
        str_format = 'ruby {}'
        cmd_str = str_format.format(reinit_config_script_path)
        print(cmd_str)
        os.system(cmd_str)
        
        # 更新版本名称及编译编号
        info_plist_path = self.project_path + os.sep + self.app_build_cofig[BuildConfigParser.WORKSPACE_FLAG][BuildConfigParser.INFO_PLIST_FLAG]
        info_plist_path = myfile.normalpath(info_plist_path)
        
        build_base.update_build_no(info_plist_path, self.ver_code)
        build_base.update_version_name(info_plist_path, self.ver_name)

        if(self.app_code == 'txxy' or self.app_code == 'xycx' or self.app_code == 'pyqx'):
            notification_info_plist_path = self.project_path + os.sep + self.app_build_cofig[BuildConfigParser.WORKSPACE_FLAG]['notification_info_plist']
            notification_info_plist_path = myfile.normalpath(notification_info_plist_path)
            build_base.update_build_no(notification_info_plist_path, self.ver_code)
            build_base.update_version_name(notification_info_plist_path, self.ver_name)
        # 更新代码配置库版本信息
        code_ver_pre = 'git_'
        if not self.use_git:
            code_ver_pre = 'svn_'
        build_base.update_plist_item(info_plist_path, 'CODE_REVISION', code_ver_pre + self.code_ver)
        
        # 更新标识当前是否是编译demo版本的标志
        #build_base.update_plist_item(info_plist_path, 'THIRD_PARTY_TEST', str(self.demo_label).lower())

        # 更新构建时间
        build_base.update_plist_item(info_plist_path, 'build_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


        # 更新api版本号
        build_base.update_plist_item(info_plist_path, 'TxxyVersion', self.api_ver)

        
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
    parser.add_argument('-v', metavar='code_ver', dest='code_ver', action='store', default=None, help='indicate updating to special code version')
    parser.add_argument('--git', dest='use_git', action='store_true', default=False, help='indicate to use git update code')
    
    parser.add_argument('--vername', metavar='ver_name', dest='ver_name', help='version name')
    parser.add_argument('--vercode', metavar='ver_code', dest='ver_code', help='version code')
    parser.add_argument('--verenv', metavar='ver_env', dest='ver_env', type=str, choices=['dev', 'test', 'test2', 'pre', 'pregray', 'pro', 'gray', 'flight'], help='dev: develop environment; test: test environment; test2: test2 environment; pre: pre-release environment; pregray: pre-release gray environment;  pro: production environment; gray: gray environment; flight: Testflight;')
    parser.add_argument('--vertype', metavar='ver_type', dest='ver_type', type=str, choices=['e', 'p'], help='e: enterprise; p: personal;')
    parser.add_argument('--apiver', metavar='api_ver', dest='api_ver', help='api version code')
    parser.add_argument('--app', metavar='app_code', dest='app_code', type=str, default='txxy', choices=['txxy','xycx', 'gzjd', 'pyqx'], help='app code name')
    parser.add_argument('--output', metavar='output_dir', dest='output_dir', help='ipa output directory')
    
    parser.add_argument('--svnuser', metavar='svn_user', dest='svn_user', help='subversion username')
    parser.add_argument('--svnpwd', metavar='svn_pwd', dest='svn_pwd', help='subversion password')
    
    parser.add_argument('--upload', dest= 'to_upload_sftp', action= 'store_true', default=False, help='need to upload to sftp Server;')
    parser.add_argument('--demo', metavar='demo_label', dest='demo_label', type=str, default='normal', choices=['normal', 'bridge', 'hotloan'], help='normal: normal entry; bridge: bridge entry; hotloan: hot loan entry;')
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
