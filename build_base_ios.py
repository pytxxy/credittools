# -*- coding:UTF-8 -*-
import os
import subprocess
import pprint
import time
import argparse
import xmltodict
import creditutils.file_util as myfile
import creditutils.svn_util as svn
import creditutils.git_util as git
import filecmp
import ftp_upload as sftp
import re
import shutil
import creditutils.zip_util as myzip
import tempfile
import traceback
import sys

# 更改plist文件指定键的值
def update_plist_item(info_plist_path, key, value):
    #     infoPlist="$project_path/pycredit/projects/pytxxy_ios/pytxxy_ios/pytxxy_ios-Info.plist"
    display_cmd_str = '/usr/libexec/PlistBuddy -c "Print {}" "{}"'.format(key, info_plist_path)
    update_cmd_str = '/usr/libexec/PlistBuddy -c "Set {} {}" "{}"'.format(key, value, info_plist_path)

    os.system(update_cmd_str)
    rtn = subprocess.check_output(display_cmd_str, shell=True, universal_newlines=True)
    set_rlt = rtn.strip()
    set_exception_info = 'to set {} item with {}, but set with {}!'.format(key, value, set_rlt)
    #     print(set_build_no_info)
    if value != set_rlt:
        raise Exception(set_exception_info)
    else:
        print('update {} with {} success.'.format(key, value))


# 更改build number
def update_build_no(info_plist_path, build_no):
    build_no = str(build_no)
    update_plist_item(info_plist_path, 'CFBundleVersion', build_no)


# 更改version
def update_version_name(info_plist_path, ver_name):
    ver_name = str(ver_name)
    update_plist_item(info_plist_path, 'CFBundleShortVersionString', ver_name)


class BuildConfigParser:
    ROOT_FLAG = 'config'
    PROJECT_FLAG = 'project'
    WORKSPACE_FLAG = 'workspace'
    PRJ_PATH_FLAG = 'prj_path'
    INFO_PLIST_FLAG = 'info_plist'
    SCHEME_FLAG = 'scheme'
    MAIN_FLAG = 'main'
    TARGET_PATH_FLAG = 'target_path'
    CODE_URL_FLAG = 'code_url'
    ENV_FLAG = 'env'
    DEV_FLAG = 'dev'
    TEST_FLAG = 'test'
    PRE_FLAG = 'pre'
    PRO_FLAG = 'pro'
    EXPORT_FLAG = 'export'
    OCR_CER_FLAG = 'ocr_cer'
    TARGET_FLAG = 'target'
    E_FLAG = 'e'
    P_FLAG = 'p'
    BUILD_INFO_TEMPLET_FLAG = 'build_info_templet'
    COVERRAGE_SHELL_PATH = 'coverageshell'
    ENV_LIST_FLAG = 'env_list'
    COVERAGE_FLAG = 'coverage'
    TINGYUN_KEY_FLAG = 'tingyun_appkey'
    COMPLIE_FLAG = 'complie'
    PODS_PATH = 'pods_path'
    INIT_RUBY_PAYH = 'init_ruby_path'

    def __init__(self, config_path):
        self.config_path = config_path

    def parse(self):
        doc = xmltodict.parse(myfile.read_file_content(self.config_path))
        self.data = doc[BuildConfigParser.ROOT_FLAG]

    def get_config(self):
        return self.data


class ProBuildConfig:
    def __init__(self, ori_data, work_path):
        self.ori_data = ori_data
        self.work_path = work_path

    def test(self):
        pass


class BuildManager:
    def __init__(self, args):
        # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)
        # pprint.pprint(vars(self))

        self.work_path = os.path.abspath(self.work_path)

        # 解析基础配置文件路径
        if not self.base_config:
            base_config_dirs = ['config', 'base', 'update_config.xml']
            base_config = os.sep.join(base_config_dirs)
        else:
            base_config = self.base_config
        self.base_config = self.work_path + os.sep + base_config

        # 先解析配置
        configParser = BuildConfigParser(self.base_config)
        configParser.parse()
        self.ori_build_config = configParser.get_config()
        self.app_build_cofig = self.ori_build_config[self.app_code]
        # project目录
        ori_project_path = self.work_path + os.sep + self.app_build_cofig[BuildConfigParser.WORKSPACE_FLAG][
            BuildConfigParser.PRJ_PATH_FLAG] + os.sep + 'master'
        if self.branch:
            ori_project_path = self.work_path + os.sep + self.app_build_cofig[BuildConfigParser.WORKSPACE_FLAG][
                BuildConfigParser.PRJ_PATH_FLAG] + os.sep + self.branch
        self.project_path = myfile.normalpath(ori_project_path)
        self.pods_path = self.project_path + os.sep + self.app_build_cofig[BuildConfigParser.WORKSPACE_FLAG][BuildConfigParser.PODS_PATH]
        self.init_ruby_path = self.project_path + os.sep + self.app_build_cofig[BuildConfigParser.WORKSPACE_FLAG][BuildConfigParser.INIT_RUBY_PAYH]



    def _get_detail_env(self, ver_env):
        env_list_dict = self.ori_build_config[BuildConfigParser.ENV_LIST_FLAG]
        if ver_env in env_list_dict:
            return env_list_dict[ver_env]

    def _get_pro_build_config(self):
        # 指定项目地址
        params = {}
        scheme_flag = 'scheme'
        configuration_flag = 'configuration'
        export_method_flag = 'export_method'
        workspace_flag = 'workspace'
        project_flag = 'project'
        output_directory_flag = 'output_directory'
        archive_path_flag = 'archive_path'
        ipa_path_flag = 'ipa_path'
        output_name_flag = 'output_name'
        export_options_flag = 'export_options'

        if scheme_flag in self.app_build_cofig[BuildConfigParser.WORKSPACE_FLAG]:
            params[scheme_flag] = self.app_build_cofig[BuildConfigParser.WORKSPACE_FLAG][scheme_flag]

        params[configuration_flag] = self.ori_build_config[BuildConfigParser.ENV_FLAG][self.ver_env][self.ver_type]
        params[export_method_flag] = self.ori_build_config[BuildConfigParser.EXPORT_FLAG][self.ver_type][self.ver_env]

        # 判断当前项目是工程集，还是单个工程，再配置相应的参数
        curr_prj_flag = None
        for prj_item in [workspace_flag, project_flag]:
            if prj_item in self.app_build_cofig[BuildConfigParser.WORKSPACE_FLAG]:
                curr_prj_flag = prj_item
                break

        if not curr_prj_flag:
            raise Exception('Error build parameter!')

        params[curr_prj_flag] = self.project_path + os.sep + self.app_build_cofig[BuildConfigParser.WORKSPACE_FLAG][
            curr_prj_flag]
        params[curr_prj_flag] = myfile.normalpath(params[curr_prj_flag])

        # 指定输出路径
        #         time_str = str(int(time.time()))
        # 将时间格式化
        curr_time = time.localtime()
        time_str = time.strftime('%Y%m%d_%H%M%S', curr_time)
        if self.output_dir:
            params[output_directory_flag] = self.output_dir + os.sep + self.ver_env + os.sep + time_str
        else:
            params[output_directory_flag] = self.work_path + os.sep + \
                                        self.app_build_cofig[BuildConfigParser.WORKSPACE_FLAG][
                                            BuildConfigParser.TARGET_PATH_FLAG] + os.sep + self.ver_env + os.sep + time_str
        params[output_directory_flag] = myfile.normalpath(params[output_directory_flag])
        self.output_directory = params[output_directory_flag]

        # 指定输出归档文件地址
        date_str = time.strftime('%Y%m%d', curr_time)
        params[archive_path_flag] = "{}/xcarchive-{}-{}-{}.xcarchive".format(params[output_directory_flag],
                                                                             self.ver_name, self.ver_code, date_str)

        # 指定输出ipa地址
        params[ipa_path_flag] = "{}/ipa".format(params[output_directory_flag])

        # 指定输出ipa名称
        params[output_name_flag] = "{}-{}-{}-{}.ipa".format(self.ver_name, self.ver_code, self.api_ver, date_str)

        self.ipa_output_path = params[output_directory_flag] + os.sep + params[output_name_flag]
        self.ipa_name = params[output_name_flag]

        # 指定证书名称
        common_plist_filename = "common_env_{}.plist".format(self.app_code)
        testfligth_plist_filename = "testFlight_{}.plist".format(self.app_code)
        cert_config_dirs = ['config', 'base', common_plist_filename]
        if self.ver_env == 'flight':
            cert_config_dirs = ['config', 'base', testfligth_plist_filename]
        cert_config = os.sep.join(cert_config_dirs)
        cert_config_path = self.work_path + os.sep + cert_config
        params[export_options_flag] = cert_config_path

        pprint.pprint(params)

        return params

    def build(self, param_map):
        #     str_format = '/usr/local/bin/gym --workspace {workspace} --scheme {scheme} --clean --configuration {configuration} --archive_path {archive_path} --export_method {export_method} --output_directory {output_directory} --output_name {output_name}'
        #     str_format_head = 'fastlane gym --use_legacy_build_api '
        str_format_head = 'fastlane gym '
        str_format_tail = ' --clean --configuration {configuration} --archive_path {archive_path} --export_method {export_method} --output_directory {output_directory} --output_name {output_name} --export_options {export_options}'
        item_format = '--{} {{{}}}'

        opt_format_items = []
        for opt_item in ['workspace', 'project', 'scheme']:
            if opt_item in param_map:
                opt_format_items.append(item_format.format(opt_item, opt_item))

        str_format = str_format_head + ' '.join(opt_format_items) + str_format_tail
        cmd_str = str_format.format(**param_map)
        #     os.system('which gym')
        #     cmd_str = 'which gym'
        #os.system(cmd_str)

        try:
            print("current_path: " + os.getcwd())
            print("cmd_str: " + cmd_str)
            os.system(cmd_str)

            return True
        except subprocess.CalledProcessError:
                # 打印异常堆栈信息
            excep_str = traceback.format_exc()
            print(excep_str)
            raise

    def process(self):
        git_flag = 'use_git'
        if not hasattr(self, git_flag):
            self.use_git = False

        # 进行代码更新操作
        if self.to_update:
            code_url = self.app_build_cofig[BuildConfigParser.CODE_URL_FLAG]
            if self.use_git:
                git.checkout_or_update(self.project_path, code_url, self.code_ver, self.branch)
            else:
                # 根据参数配置svn用户名和密码
                username_flag = 'svn_user'
                password_flag = 'svn_pwd'
                if hasattr(self, username_flag) and hasattr(self, password_flag):
                    #                 print('{}: {}'.format(username_flag, self.svn_user))
                    #                 print('{}: {}'.format(password_flag, self.svn_pwd))
                    svn.set_user_info(getattr(self, username_flag), getattr(self, password_flag))

                svn.checkout_or_update(self.project_path, code_url, self.code_ver)
        # 获取当前代码版本号
        if self.use_git:
            git_root = git.get_git_root(self.project_path)
            self.code_ver = git.get_revision(git_root)
        else:
            self.code_ver = svn.get_revision(self.project_path)
        print('current code version is ' + str(self.code_ver))
        # 进行版本编译操作
        if self.to_build:
            to_check_vals = ['ver_name', 'ver_code', 'ver_env', 'ver_type']
            for name in to_check_vals:
                value = getattr(self, name)
                if not value:
                    info = 'Please specify the {}.'.format(name)
                    print(info)
                    exit(1)

            # 参数非空判断验证通过开始进行正式业务逻辑
            self.pro_build_config = self._get_pro_build_config()
            self.pre_build()
            self.build(self.pro_build_config)
            if os.path.isfile(self.ipa_output_path):
                # 将编译信息写文件
                build_info_format = self.ori_build_config[BuildConfigParser.BUILD_INFO_TEMPLET_FLAG]
                build_info = build_info_format.format(ver_name=self.ver_name, code_ver=self.code_ver,
                                                      ver_code=self.ver_code)
                build_info_path = self.output_directory + os.sep + 'readme-{}-{}.txt'.format(self.ver_name,
                                                                                             self.ver_code)
                myfile.write_to_file(build_info_path, build_info, encoding='utf-8')
                str_info = 'Build success, current code version is {}.'.format(self.code_ver)
                print(str_info)
            else:
                str_info = 'Build failed, current code version is {}.'.format(self.code_ver)
                raise Exception(str_info)





            # 将*.ipa包上传到sftp服务器
            if self.to_upload_sftp:

                # 复制podfile.lock 到目标文件夹
                pods_lock_file = self.pods_path + os.sep + 'Podfile.lock'
                shutil.copy(pods_lock_file, self.output_directory)

                # 为防止上传的东西太多，将部分文件打成zip包
                print('Archiving data file')
                tmp_folder = tempfile.mkdtemp()
                dst_zip_file = self.output_directory + os.sep + '%s_data.zip'%(self.ipa_name)
                myfile.process_dir_src_to_dst(self.output_directory, tmp_folder, self.process_func)
                myzip.zip_dir(tmp_folder, dst_zip_file)
                shutil.rmtree(tmp_folder)
                for file in os.listdir(self.output_directory):
                    if os.path.splitext(file)[1] == '.xcarchive':
                        xcarchive_file_path = os.path.join(self.output_directory, file)
                        shutil.rmtree(xcarchive_file_path)
                try:
                    sftp.upload_to_sftp(self.work_path, self.ver_name, self.ver_env, self.code_ver, self.app_code, self.output_directory,
                                    'IOS', '', self.ipa_name, self.ipa_name)
                except Exception as e:
                    raise Exception('upload To Ftp Error')

    # 复制文件到目标文件夹并删除源文件
    def process_func(self, src_file, dst_file):
        if os.path.splitext(src_file)[1] != '.ipa':
            myfile.replace_file(src_file, dst_file)
            os.remove(src_file)

    def pre_build(self):
        # 更新版本名称及编译编号
        info_plist_path = self.project_path + os.sep + self.app_build_cofig[BuildConfigParser.WORKSPACE_FLAG][
            BuildConfigParser.INFO_PLIST_FLAG]
        info_plist_path = myfile.normalpath(info_plist_path)

        update_build_no(info_plist_path, self.ver_code)
        update_version_name(info_plist_path, self.ver_name)

        # 更新OCR授权文件
        # target = self.project_path + os.sep + self.ori_build_config[BuildConfigParser.OCR_CER_FLAG][
        #     BuildConfigParser.TARGET_FLAG]
        # target = myfile.normalpath(target)
        # source = self.project_path + os.sep + self.ori_build_config[BuildConfigParser.OCR_CER_FLAG][self.ver_type]
        # source = myfile.normalpath(source)
        # if not filecmp.cmp(source, target, shallow=False):
        #     myfile.replace_file(source, target)
        #     str_info = 'replace ocr certificate with {} type.'.format(self.ver_type)
        #     print(str_info)
        # else:
        #     str_info = 'ramain ocr certificate with {} type.'.format(self.ver_type)
        #     print(str_info)


def main(args):
    manager = BuildManager(args)
    manager.process()


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='update code, build.')
    parser.add_argument('work_path', metavar='work_path', help='working directory')

    parser.add_argument('-c', metavar='base_config', dest='base_config',
                        help='base configure file, path relative to work path')
    parser.add_argument('-u', dest='to_update', action='store_true', default=False,
                        help='indicate to get or update code firstly')
    parser.add_argument('-b', dest='to_build', action='store_true', default=False, help='indicate to build')
    parser.add_argument('-v', metavar='code_ver', dest='code_ver', action='store', default=None,
                        help='indicate updating to special code version')

    parser.add_argument('--vername', metavar='ver_name', dest='ver_name', help='version name')
    parser.add_argument('--vercode', metavar='ver_code', dest='ver_code', help='version code')
    parser.add_argument('--verenv', metavar='ver_env', dest='ver_env', type=str,
                        choices=['dev', 'test', 'test2', 'pre', 'pregray', 'pro', 'gray', 'flight'],
                        help='dev: develop environment; test: test environment; test2: test2 environment; pre: pre-release environment; pregray: pre-release gray environment;  pro: production environment; gray: gray environment; flight: Testflight;')
    parser.add_argument('--vertype', metavar='ver_type', dest='ver_type', type=str, choices=['e', 'p'],
                        help='e: enterprise; p: personal;')
    parser.add_argument('--upload', dest='to_upload_sftp', action='store_true', default=False,
                        help='need to upload to sftp Server;')
    parser.add_argument('--branch', metavar='branch', dest='branch', help='branch name')

    #     parser.print_help()

    return parser.parse_args(src_args)
