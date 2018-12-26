# -*- coding:UTF-8 -*-
import os
import sys
import time

import re

import ftp_upload
import creditutils.file_util as file_util
import pprint
# import traceback
import creditutils.trivial_util as utility
import creditutils.git_util as git
import argparse
import subprocess
import xmltodict


class Label:
    workspace = 'workspace'
    prj_path = 'prj_path'
    prj_root = 'prj_root'
    main = 'main'
    target_path = 'target_path'
    output_directory = 'output_directory'
    output_name = 'output_name'

    static = 'static'
    config = 'config'
    code_url = 'code_url'
    build_info_template = 'build_info_template'

    is_test = 'is_test'
    default_chan = 'pycredit'

    dev = 'dev'
    miniid = 'miniid'
    beta = 'beta'
    formal = 'formal'
    appid = 'appid'
    name = 'name'

    info = 'info'
    test_switch = 'test_switch'
    file_item = 'file_item'

    env = 'env'
    label = 'label'
    ver_env = 'ver_env'
    ver_name = 'ver_name'
    ver_no = 'ver_no'
    code_ver = 'code_ver'
    formal_desc = 'formal_desc'
    whole_ver_name = 'whole_ver_name'
    branch = 'branch'
    submodule = 'submodule'

    # 是否支持网络环境手动选择、网络环境、代码版本信息、编译时间配置键值
    enable_test = 'enableTest'
    current_server_name = 'currentServerName'
    code_revision = 'codeRevision'
    build_time = 'buildTime'
    app_version = 'applicationVersion'


class MiniType:
    beta = 'beta'
    formal = 'formal'


class BuildCmd:
    map_key = ['ver_name', 'prj_root', 'formal_desc']
    cmd_name_format = 'cli -u {ver_name}@{prj_root} --upload-desc "{formal_desc}"'

    def __init__(self):
        # 先初始化默认值
        self.ver_name = '1.0.0'
        self.prj_root = None
        self.formal_desc = ''

    def update_value(self, info):
        self.ver_name = info[Label.whole_ver_name]
        self.prj_root = info[Label.prj_root]
        self.formal_desc = info[Label.formal_desc]

    def get_map(self):
        rtn_map = {}
        for item in BuildCmd.map_key:
            rtn_map[item] = getattr(self, item)

        return rtn_map

    def get_build_cmd(self, info):
        self.update_value(info)
        params = self.get_map()
        cmd_str = BuildCmd.cmd_name_format.format(**params)
        # print(cmd_str)

        return cmd_str


# 到指定目录执行小程序开发工具命令上传当前工程代码
def upload_project(work_path, cmd_str):
    dir_change = False
    success_str = 'upload success'
    pre_cwd = os.getcwd()
    if os.path.abspath(pre_cwd) != os.path.abspath(work_path):
        os.chdir(os.path.dirname(work_path))
        dir_change = True

    try:
        print(cmd_str)
        # os.system(cmd_str)
        # 获取转码存在问题，直接校验bytes数据str格式数据是否包含指定字符
        # result = subprocess.check_output(cmd_str, shell=True, universal_newlines=True)
        result = subprocess.check_output(cmd_str, shell=True)
        if success_str in str(result):
            return True
        else:
            return False
    except subprocess.CalledProcessError:
        raise
    finally:
        if dir_change:
            os.chdir(pre_cwd)


# 对整个工程内相关文件进行替换操作
class ProjectBuilder:
    def __init__(self, info):
        self.prj_root = info[Label.prj_root]
        self.info = info

        self.prj_root = self.info[Label.prj_root]
        config_file_path = os.path.join(self.prj_root, self.info[Label.info][Label.file_item])
        self.config_file_path = file_util.normalpath(config_file_path)
        env_config_path = os.path.join(self.prj_root, self.info[Label.env][Label.file_item])
        self.env_config_path = file_util.normalpath(env_config_path)

    # 更新通用信息
    def update_info(self):
        # 更新配置文件中的appid和projectname
        ver_env = self.info[Label.ver_env]
        evn_updater = EnvironmentUpdater(self.env_config_path)
        env_target_info = dict()
        env_src_data = self.info[Label.env][Label.miniid][ver_env]
        env_target_info[EnvironmentUpdater.APPID_FLAG] = env_src_data[Label.appid]
        env_target_info[EnvironmentUpdater.PRJ_NAME_FLAG] = env_src_data[Label.name]
        if self.info[Label.branch] != 'develop':
            env_target_info[EnvironmentUpdater.PRJ_NAME_FLAG] = env_src_data[Label.name] + '_{}'.format(
                self.info[Label.branch])
        evn_updater.update_info(env_target_info)

        # 更新是否支持网络环境手动选择、网络环境、代码版本信息、编译时间配置、版本名称信息
        # info_config_updater = InfoConfigUpdater(self.config_file_path)
        # target_info = dict()
        # target_info[Label.current_server_name] = self.info[Label.ver_env]
        # target_info[Label.code_revision] = self.info[Label.code_ver]
        # target_info[Label.build_time] = self.info[Label.build_time]
        # target_info[Label.app_version] = self.info[Label.whole_ver_name]
        # info_config_updater.update_info(target_info)

    def get_build_cmd(self):
        build_cmd = BuildCmd()
        return build_cmd.get_build_cmd(self.info)

    def build(self):
        print('building begin ...')

        cmd_str = self.get_build_cmd()
        if self.info[Label.is_test]:
            print(cmd_str)
            return True
        else:
            return upload_project(self.prj_root, cmd_str)


# 对网络环境配置进行更新
class EnvironmentUpdater:
    APPID_FLAG = 'appid'
    PRJ_NAME_FLAG = 'projectname'

    def __init__(self, src_path):
        self.src_path = src_path
        self.src_data = file_util.read_file_content(self.src_path)
        self.modify_flag = False

    def update_info(self, target_info):
        if target_info:
            self._update_config(target_info)

        if self.modify_flag:
            file_util.write_to_file(self.src_path, self.src_data, 'utf-8')

    # 使用直接替换的方式实现
    def _update_config(self, target_info):
        modify_flag = False
        #         print(self.src_data)
        ptn_str_format = '("{}"\s*:\s*"?)([^",]*)("?\s*,)'
        for key in target_info:
            ptn_str = ptn_str_format.format(key)
            ptn = re.compile(ptn_str, flags=(re.I | re.M))
            # 避免自引用和value值 串在一起引起混淆，所以在中间添加特殊字符进行分隔
            re_sep = re.escape('#!#!#')
            re_rep_unit = re_sep + re.escape(target_info[key])
            new_data = ptn.sub('\\1' + re_rep_unit + '\\3', self.src_data)
            new_data = new_data.replace(re_rep_unit, target_info[key])
            if new_data != self.src_data:
                modify_flag = True
                #                 print('-'*80)
                #                 print(new_data)
                self.src_data = new_data
                info_format = '{} has been set as {}.'
                print(info_format.format(key, target_info[key]))
            else:
                info_format = '{} remain as {}.'
                print(info_format.format(key, target_info[key]))

        if modify_flag:
            self.modify_flag = True


# 对配置信息进行更新
class InfoConfigUpdater:
    def __init__(self, src_path):
        self.src_path = src_path
        self.src_data = file_util.read_file_content(self.src_path)
        self.modify_flag = False

    def update_info(self, target_info):
        if target_info:
            self._update_config(target_info)

        if self.modify_flag:
            file_util.write_to_file(self.src_path, self.src_data, 'utf-8')

    # 使用直接替换的方式实现
    def _update_config(self, target_info):
        modify_flag = False
        # print(self.src_data)
        # 例子'const enableTest = true', 'var currentServerName = "dev"'
        ptn_str_format = '((?:(?:var)|(?:let)|(?:const))\s+{}\s*=\s*)((?:\w+)|(?:"[^"]+"))(\s+)'
        for key in target_info:
            ptn_str = ptn_str_format.format(key)
            ptn = re.compile(ptn_str, flags=re.M)
            # 避免自引用和value值 串在一起引起混淆，所以在中间添加特殊字符进行分隔
            re_sep = re.escape('#!#!#')
            target_str = target_info[key]
            if isinstance(target_str, bool):
                to_replace_str = str(target_str).lower()
            else:
                to_replace_str = '"{}"'.format(target_str)
            re_rep_unit = re_sep + re.escape(to_replace_str)
            new_data = ptn.sub('\\1' + re_rep_unit + '\\3', self.src_data)
            new_data = new_data.replace(re_rep_unit, to_replace_str)
            if new_data != self.src_data:
                modify_flag = True
                #                 print('-'*80)
                #                 print(new_data)
                self.src_data = new_data
                info_format = '{} has been set as {}.'
                print(info_format.format(key, target_info[key]))
            else:
                info_format = '{} remain as {}.'
                print(info_format.format(key, target_info[key]))

        if modify_flag:
            self.modify_flag = True


class BuildConfigParser:
    def __init__(self, config_path):
        self.config_path = config_path
        self.data = None

    def parse(self):
        doc = xmltodict.parse(file_util.read_file_content(self.config_path))
        self.data = doc[Label.config]

    def get_config(self):
        return self.data


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
        self.base_config = os.path.join(self.work_path, base_config)

        # 先解析配置
        config_parser = BuildConfigParser(self.base_config)
        config_parser.parse()
        self.ori_build_config = config_parser.get_config()

        # project目录
        ori_project_path = os.path.join(self.work_path, self.ori_build_config[Label.workspace][Label.prj_path])
        self.project_path = os.path.normpath(ori_project_path)
        self.project_code_path = None
        self.prj_root = None
        self.prj_code_ver = None
        self.pro_build_config = None

    def _get_whole_ver_name(self, label_map):
        # 确定是否要展示标识环境的标签
        ver_env_no_label = ''
        env_label = label_map[self.ver_env]
        if env_label:
            ver_env_no_label = '{}{:02d}'.format(env_label, self.ver_no)

        whole_ver_name = '{}{}'.format(self.ver_name, ver_env_no_label)
        return whole_ver_name

    # 配置每个工程个性化的内容
    def _get_pro_build_config(self):
        # 指定项目地址
        params = dict()

        params[Label.prj_root] = self.prj_root
        params[Label.main] = 'gzjdmini'
        params[Label.env] = self.ori_build_config[Label.env]
        params[Label.info] = self.ori_build_config[Label.info]

        params[Label.ver_env] = self.ver_env
        params[Label.branch] = self.branch

        # 将时间格式化
        curr_time = time.localtime()
        time_str = time.strftime('%Y%m%d_%H%M%S', curr_time)
        build_time = time.strftime('%Y%m%d %H:%M:%S', curr_time)

        relative_target_path = self.ori_build_config[Label.workspace][Label.target_path]
        output_directory = os.path.normpath(os.path.join(self.work_path, relative_target_path))
        params[Label.output_directory] = os.path.join(output_directory, self.ver_env, time_str)

        self.output_directory = params[Label.output_directory]

        params[Label.ver_name] = self.ver_name
        self.whole_ver_name = self._get_whole_ver_name(self.ori_build_config[Label.env][Label.label])
        params[Label.whole_ver_name] = self.whole_ver_name

        params[Label.code_ver] = self.prj_code_ver
        params[Label.is_test] = self.is_test
        params[Label.formal_desc] = self.formal_desc
        params[Label.build_time] = build_time

        pprint.pprint(params)

        return params

    def process(self):
        self.project_code_path = os.path.join(self.project_path, self.branch)

        # 进行代码更新操作
        if self.to_update:
            code_url = self.ori_build_config[Label.config][Label.code_url]
            git.checkout_or_update(self.project_code_path, code_url, self.code_ver, self.branch)

        # 设置配置信息并获取当前代码版本号
        self.prj_root = git.get_git_root(self.project_code_path)
        self.prj_code_ver = git.get_revision(self.prj_root)

        if self.to_update:
            if Label.submodule in self.ori_build_config[Label.config]:
                submodules = self.ori_build_config[Label.config][Label.submodule]
                for submodule in submodules:
                    submodule_name = submodule
                    sub_branch = submodules[submodule_name][Label.branch]
                    git.update_submodules(self.prj_root, modules_name=submodule_name, branch=sub_branch,
                                          need_remote=self.sub_remote)

        print('current code version is ' + self.prj_code_ver)

        # 下面这部分代码依赖于前面成员变量的初始化，请不要随意调整执行位置
        if self.to_update:
            self._update_local_build_file()

        # 进行版本编译操作
        if self.to_build:
            # 参数非空判断验证
            to_check_values = ['ver_name']
            for name in to_check_values:
                value = getattr(self, name)
                if not value:
                    info = 'Please specify the {}.'.format(name)
                    print(info)
                    exit(1)

            self.pro_build_config = self._get_pro_build_config()
            rtn = self.build_app(self.pro_build_config)

            if rtn:
                # 将编译信息写文件
                self._write_build_info()
                str_info = 'Build success, code version is {}.'.format(self.prj_code_ver)
                print(str_info)

                # 进行编译好的版本提交操作
                if hasattr(self, 'to_upload') and self.to_upload and not self.pro_build_config[Label.is_test]:
                    self._upload_file(self.pro_build_config[Label.whole_ver_name], self.ver_env)
            else:
                str_info = 'Build failed, code version is {}.'.format(self.prj_code_ver)
                print(str_info)

    def build_app(self, info):
        prj_builder = ProjectBuilder(info)
        prj_builder.update_info()
        return prj_builder.build()

    def _update_local_build_file(self):
        pass

    # 将编译信息写到文件中
    def _write_build_info(self):
        build_info_format = self.ori_build_config[Label.build_info_template]
        build_info = build_info_format.format(ver_name=self.whole_ver_name, code_ver=self.prj_code_ver,
                                              formal_desc=self.formal_desc)
        readme_file_name = 'readme-{}.txt'.format(self.whole_ver_name)
        build_info_path = os.path.join(self.output_directory, readme_file_name)
        parent_dir = os.path.dirname(build_info_path)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)

        file_util.write_to_file(build_info_path, build_info, encoding='utf-8')

    def _upload_file(self, whole_ver_name, ver_env):
        # ftp_config_path = os.path.join(self.work_path, 'config')
        ftp_config_path = self.work_path
        print('ver_name_info:', whole_ver_name)
        print('ver_env: ', ver_env)

        ftp_upload.upload_to_sftp(ftp_config_path, whole_ver_name, ver_env, self.prj_code_ver, mobile_os='wechat')


def main(args):
    manager = BuildManager(args)
    manager.process()


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='update code if need, build if need.')
    parser.add_argument('work_path', metavar='work_path', help='working directory')

    parser.add_argument('-c', metavar='base_config', dest='base_config',
                        help='base configure file, path relative to work path')
    parser.add_argument('-u', dest='to_update', action='store_true', default=False,
                        help='indicate to get or update code firstly')
    parser.add_argument('-b', dest='to_build', action='store_true', default=False, help='indicate to build')
    parser.add_argument('-v', metavar='code_ver', dest='code_ver', action='store', default=None,
                        help='indicate updating to special version')

    parser.add_argument('--vername', metavar='ver_name', dest='ver_name', help='version name')
    parser.add_argument('--verno', metavar='ver_no', dest='ver_no', type=int, default=0, help='version release number')

    # 如果是正式环境，无须配置此参数，不论该参数配置是何值，最后内部都会配置成"pro"
    parser.add_argument('--verenv', metavar='ver_env', dest='ver_env', default='test',
                        choices=['test', 'pro'],
                        help='test: test environment;'
                             'pro: production environment;')

    # 上传版本使用的描述信息
    parser.add_argument('--desc', metavar='formal_desc', dest='formal_desc', default='',
                        help='formal version description.')
    parser.add_argument('--test', dest='is_test', action='store_true', default=False,
                        help='indicate just to test config.')

    parser.add_argument('--upload', dest='to_upload', action='store_true', default=False,
                        help='indicate to upload build record to repository.')
    parser.add_argument('--branch', metavar='branch', dest='branch', default='develop', help='code branch name')

    #     parser.print_help()

    return parser.parse_args(src_args)


if __name__ == '__main__':
    test_args = None
    # print(sys.argv)
    args = get_args(test_args)
    utility.measure_time(main, args)
