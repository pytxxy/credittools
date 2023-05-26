# -*- coding:UTF-8 -*-
# 20171101 19:00 最大化地利用好gradle 做编译配置工作，对python 编译脚本相应地进行精简
import os
import time
import re
from enum import IntEnum
import platform
from bugly_upload_symbol import BuglyManager

import ftp_upload
import creditutils.apk_builder_util as apk_builder
import creditutils.file_util as file_util
import pprint
# import traceback
import creditutils.str_util as str_utils
import creditutils.trivial_util as utility
import creditutils.git_util as git
import argparse
import subprocess
import xmltodict
import protect_android_app as protect_app
import creditutils.apk_util as apk
import creditutils.zip_util as zip_util
import creditutils.apk_util as apk_util


BuilderVer = IntEnum('BuilderVer', ('JavaLast', 'Kotlin01'))


_system = platform.system()
if _system == 'Windows':
    _system_pre = ''
    _system_suffix = '.bat'
elif _system == 'Linux':
    _system_pre = 'bash '
    _system_suffix = ''
else:
    _system_pre = 'bash '
    _system_suffix = ''


class BuilderLabel:
    PRJ_ROOT_FLAG = 'prj_root'
    MAIN_FLAG = 'main'

    DEFAULT_CHAN = 'pycredit'

    NET_CONFIG_PATH_FLAG = 'net_config_path'
    DEV_FLAG = 'dev'
    NET_INFO_FLAG = 'net_info'
    HOST_FLAG = 'host'
    PORT_FLAG = 'port'
    SSLPORT_FLAG = 'sslport'

    ENV_FLAG = 'env'
    NET_ENV_FLAG = 'net_env'
    ENV_MODE_FLAG = 'env_mode'
    TYPE_FLAG = 'type'
    ENCRYPT_ITEMS_FLAG = 'encrypt_items'
    FILE_ITEM_FLAG = 'file_item'
    GRADLE_FLAG = 'gradle'

    PROTECT_FLAG = 'protect'
    IP_FLAG = 'ip'
    USER_FLAG = 'user'
    PASSWORD_FLAG = 'password'
    API_KEY_FLAG = 'api_key'
    API_SECRET_FLAG = 'api_secret'

    IS_NEED_FLAG = 'is_need'

    SIGNER_FLAG = 'signer'
    KEYSTORE_FLAG = 'keystore'
    STOREPASS_FLAG = 'storepass'
    STOREALIAS_FLAG = 'storealias'

    BUILD_CLASS_FLAG = 'build_class'
    SRC_PATH_FLAG = 'src_path'
    DST_PATH_FLAG = 'dst_path'

    COVERAGE_FLAG = 'coverage'
    COMPILE_FLAG = 'compile'
    BUILDER_VER_FLAG = 'builder_ver'

    OUTPUT_DIRECTORY_FLAG = 'output_directory'
    OUTPUT_NAME_FLAG = 'output_name'
    VER_NAME_FLAG = 'ver_name'
    VER_CODE_FLAG = 'ver_code'
    VER_NO_FLAG = 'ver_no'
    IS_TEST_FLAG = 'is_test'
    DEMO_LABEL_FLAG = 'demo_label'
    API_VER_FLAG = 'api_ver'
    APP_CODE_FLAG = 'app_code'
    ENTRANCE_FLAG = 'entrance'

    LABEL_FLAG = 'label'
    BETA_LABEL_FLAG = 'beta_label'
    HTTPDNS_FLAG = 'httpdns'

    CODE_VER_FLAG = 'code_ver'
    MINIFY_ENABLED_FLAG = 'minify_enabled'
    UPLOAD_BUGLY_FLAG = 'upload_bugly'


class BuildCmd:
    exec_name = f'gradlew{_system_suffix}'
    pre_cmd = exec_name + ' --configure-on-demand clean'

    map_key = ['action', 'net_env', 'build_type', 'ver_name', 'ver_code', 'ver_no', 'api_ver', 'for_publish',
               'coverage_enabled', 'httpdns', 'demo_label', 'entrance', 'minify_enabled']

    cmd_format = exec_name + ' --configure-on-demand {action}{net_env}{build_type} -PAPP_BASE_VERSION={ver_name} ' \
        '-PAPP_VERSION_CODE={ver_code} -PAPP_RELEASE_VERSION={ver_no} -PAPI_VERSION={api_ver} -PFOR_PUBLISH={for_publish} ' \
        '-PHTTP_DNS_OPEN={httpdns} -PWEB_URL={entrance} -PMINIFY_ENABLED={minify_enabled}'

    cmd_format_without_api_ver = exec_name + ' --configure-on-demand {action}{net_env}{build_type} -PAPP_BASE_VERSION={ver_name} ' \
        '-PAPP_VERSION_CODE={ver_code} -PAPP_RELEASE_VERSION={ver_no} -PFOR_PUBLISH={for_publish}  ' \
        '-PHTTP_DNS_OPEN={httpdns} -PWEB_URL={entrance} -PMINIFY_ENABLED={minify_enabled}'

    def __init__(self):
        # 先初始化默认值
        self.action = 'assemble'
        self.net_env = 'tst'
        self.build_type = 'Release'
        self.ver_name = '1.0.0'
        self.ver_code = 0
        self.ver_no = '00'
        self.api_ver = None
        self.entrance = None
        self.for_publish = str(True).lower()
        self.coverage_enabled = str(True).lower()
        self.httpdns = str(False).lower()
        self.demo_label = 'normal'

    def update_value(self, info):
        # 根据给过来的配置值，更新相应值

        # 配置为正常编译，还是只是验证配置是否正确
        is_test = info[BuilderLabel.IS_TEST_FLAG]
        if is_test:
            self.action = 'preConfig'
        else:
            self.action = 'assemble'

        # 网络环境配置
        ori_net_env = info[BuilderLabel.NET_ENV_FLAG]
        self.net_env = info[BuilderLabel.ENV_FLAG][BuilderLabel.GRADLE_FLAG][ori_net_env].capitalize()

        # 配置为Release还是Debug模式
        self.build_type = info[BuilderLabel.TYPE_FLAG].capitalize()
        self.ver_name = info[BuilderLabel.VER_NAME_FLAG]
        self.ver_code = info[BuilderLabel.VER_CODE_FLAG]
        self.ver_no = '{:02d}'.format(info[BuilderLabel.VER_NO_FLAG])
        self.api_ver = info[BuilderLabel.API_VER_FLAG]
        self.entrance = info[BuilderLabel.ENTRANCE_FLAG]

        env_mode = info[BuilderLabel.ENV_MODE_FLAG]
        self.httpdns = info[BuilderLabel.ENV_FLAG][BuilderLabel.HTTPDNS_FLAG][env_mode].lower()
        self.minify_enabled = str(info[BuilderLabel.MINIFY_ENABLED_FLAG]).lower()
        self.upload_bugly = str(info[BuilderLabel.UPLOAD_BUGLY_FLAG]).lower()

    def get_map(self):
        rtn_map = {}
        for item in BuildCmd.map_key:
            value = getattr(self, item)
            if value:
                rtn_map[item] = getattr(self, item)

        return rtn_map

    def get_build_cmd(self, info):
        self.update_value(info)
        params = self.get_map()
        if BuilderLabel.API_VER_FLAG in params:
            cmd_format = BuildCmd.cmd_format
        else:
            cmd_format = BuildCmd.cmd_format_without_api_ver

        cmd_str = cmd_format.format(**params)
        print(cmd_str)

        return cmd_str


# 到指定目录执行gradle命令生成指定版本apk
def make_apk_with_gradle(work_path, cmd_str, pre_cmd=BuildCmd.pre_cmd):
    dir_change = False
    pre_cwd = os.getcwd()
    if os.path.abspath(pre_cwd) != os.path.abspath(work_path):
        os.chdir(os.path.dirname(work_path))
        dir_change = True

    try:
        if pre_cmd:
            pre_build_cmd = _system_pre + os.path.join(os.path.dirname(work_path), pre_cmd)
            print(pre_build_cmd)
            subprocess.check_call(pre_build_cmd, shell=True)

        build_cmd = _system_pre + os.path.join(os.path.dirname(work_path), cmd_str)
        print(build_cmd)
        subprocess.check_call(build_cmd, shell=True)
        # os.system(build_cmd)
    except subprocess.CalledProcessError:
        raise
    finally:
        if dir_change:
            os.chdir(pre_cwd)


class EnvironmentUpdater:
    # example: "public static final int ENV_CONFIG = DEVELOP_ENV;"
    CONFIG_PATTERN = '^(\s*public\s+static\s+final\s+int\s+ENV_CONFIG\s*=\s*)(\w+)(_ENV;)'

    def __init__(self, config_path):
        self.config_path = config_path
        self.config_data = file_util.read_file_content(self.config_path)
        self.config_modified = False

        env_ptn = re.compile(EnvironmentUpdater.CONFIG_PATTERN, flags=(re.M))
        config_match = env_ptn.search(self.config_data)
        if config_match:
            self.config = config_match.group(2)
        else:
            self.config = ''

    def _update_config(self, config=None):
        if config:
            dest_config = config.upper()
            if dest_config != self.config:
                ptn = re.compile(EnvironmentUpdater.CONFIG_PATTERN, flags=(re.M))

                modify_flag = False
                new_str = None
                match = ptn.search(self.config_data)
                if match:
                    modify_flag = True
                    new_str = match.group(1) + dest_config + match.group(3)

                    info_format = 'replace environment mode "{}" with "{}"!'
                    print(info_format.format(self.config, dest_config))

                    self.config = dest_config

                if modify_flag:
                    self.config_modified = True
                    self.config_data = ptn.sub(new_str, self.config_data)
            else:
                info_format = 'environment mode remain as "{}"!'
                print(info_format.format(self.config))

    def update_config(self, config=None):
        self._update_config(config)

        if self.config_modified:
            file_util.write_to_file(self.config_path, self.config_data, 'utf-8')


# 对整个工程内相关文件进行替换操作
class ProjectBuilder:
    def __init__(self, info):
        self.prj_root = info[BuilderLabel.PRJ_ROOT_FLAG]
        self.main_prj_name = info[BuilderLabel.MAIN_FLAG]
        self.main_prj_path = os.path.join(self.prj_root, self.main_prj_name)
        self.info = info

        self.manifest_path = os.path.join(self.main_prj_path, 'AndroidManifest.xml')

    # 更新通用信息
    def update_info(self):
        pass

    def get_build_cmd(self):
        build_cmd = BuildCmd()
        return build_cmd.get_build_cmd(self.info)

    def _get_output_relative_path(self):
        # 网络环境配置
        ori_net_env = self.info[BuilderLabel.NET_ENV_FLAG]
        net_env = self.info[BuilderLabel.ENV_FLAG][BuilderLabel.GRADLE_FLAG][ori_net_env]

        # 配置为Release还是Debug模式
        build_type = self.info[BuilderLabel.TYPE_FLAG]

        relative_path = os.path.join(net_env, build_type)
        print(relative_path)

        return relative_path

    def build(self):
        print('building apk begin ...')

        # 获取apk名称
        apk_name = os.path.basename(self.main_prj_path)

        apk_out_path = self.main_prj_path + '/build/outputs/apk/'
        # 自定义名称形式
        apk_path = os.path.join(apk_out_path, self._get_output_relative_path(), self.info[BuilderLabel.OUTPUT_NAME_FLAG])
        apk_path = os.path.normpath(apk_path)

        # 先把现有的apk文件直接删除
        if os.path.exists(apk_path) and os.path.isfile(apk_path):
            os.remove(apk_path)

        cmd_str = self.get_build_cmd()
        make_apk_with_gradle(self.main_prj_path, cmd_str)

        src_file = apk_path
        print('source apk path: {}'.format(src_file))

        if os.path.exists(src_file):
            apk_items = apk.get_apk_info(src_file)

            actual_ver_name = self.get_main_ver_name(apk_items['versionName'])
            if actual_ver_name != self.info[BuilderLabel.VER_NAME_FLAG]:
                info = 'set version name is {}, but actual is {}!'.format(self.info[BuilderLabel.VER_NAME_FLAG], actual_ver_name)
                raise Exception(info)

            if apk_items['versionCode'] != str(self.info[BuilderLabel.VER_CODE_FLAG]):
                info = 'set version code is {}, but actual is {}!'.format(self.info[BuilderLabel.VER_CODE_FLAG], apk_items['versionCode'])
                raise Exception(info)

            dst_file = self.info[BuilderLabel.OUTPUT_DIRECTORY_FLAG] + os.sep + self.info[
                BuilderLabel.OUTPUT_NAME_FLAG]
            file_util.replace_file(src_file, dst_file)

            # 拷贝编译生成的class文件，便于服务器生成代码覆盖率文件
            if BuilderLabel.BUILD_CLASS_FLAG in self.info and len(self.info[BuilderLabel.BUILD_CLASS_FLAG]) >= 2:
                src_class_path = self.main_prj_path + os.sep + self.info[BuilderLabel.BUILD_CLASS_FLAG][BuilderLabel.SRC_PATH_FLAG]
                src_class_path = file_util.normalpath(src_class_path)

                dst_class_relative_path = self.info[BuilderLabel.BUILD_CLASS_FLAG][BuilderLabel.DST_PATH_FLAG]
                dst_class_zip_path = self.info[BuilderLabel.OUTPUT_DIRECTORY_FLAG] + os.sep + 'classes.zip'

                if os.path.isdir(src_class_path):
                    # shutil.copytree(src_class_path, dst_class_path)
                    rev_index = -len(dst_class_relative_path)
                    zip_src_root = src_class_path[:rev_index]
                    zip_util.zip_dir(src_class_path, dst_class_zip_path, zip_src_root)
                    print('success zip {} to {}.'.format(dst_class_relative_path, dst_class_zip_path))

            print('built the apk {}.'.format(dst_file))
        else:
            print('build {} failed!'.format(apk_name))

    def get_main_ver_name(self, whole_name):
        ptn_str = '^(\d+(?:\.\d+)+)(?![.\d])'
        rtn = re.match(ptn_str, whole_name)
        if rtn:
            return rtn.group(1)
        else:
            raise Exception('{} is invalid!'.format(whole_name))


class BuildConfigLabel:
    ROOT_FLAG = 'config'
    WORKSPACE_FLAG = 'workspace'
    PRJ_PATH_FLAG = 'prj_path'
    MAIN_FLAG = 'main'
    TARGET_PATH_FLAG = 'target_path'

    STATIC_FLAG = 'static'
    CODE_URL_FLAG = 'code_url'

    API_VER_FLAG = 'api_ver'
    NETWORK_FLAG = 'network'
    RELATIVE_PATH_FLAG = 'relative_path'

    ENCRYPT_FLAG = 'encrypt'
    BIN_NAME_FLAG = 'bin_name'
    FILE_ITEM_FLAG = 'file_item'

    PROTECT_FLAG = 'protect'
    IS_NEED_FLAG = 'is_need'

    SIGNER_FLAG = 'signer'

    BUILD_CLASS_FLAG = 'build_class'

    COVERAGE_FLAG = 'coverage'

    ENV_FLAG = 'env'
    MAP_FLAG = 'map'
    DEV_FLAG = 'dev'
    TEST_FLAG = 'test'
    PRE_FLAG = 'pre'
    PRO_FLAG = 'pro'
    TARGET_FLAG = 'target'
    BUILD_INFO_TEMPLET_FLAG = 'build_info_templet'

    LABEL_FLAG = 'label'
    BETA_LABEL_FLAG = 'beta_label'


class BuildConfigParser:
    def __init__(self, config_path):
        self.config_path = config_path

    def parse(self):
        doc = xmltodict.parse(file_util.read_file_content(self.config_path))
        self.data = doc[BuildConfigLabel.ROOT_FLAG]

    def get_config(self):
        return self.data


class BuildManager:
    # 安装包输出名称匹配正则表达式："3.1.0beta_p_01-314-20170515.apk"
    #     __APK_OUTPUT_PATH_INFORMAl_PATTERN = '([\d\.]+)beta_(\w+_\d+)-(\d+)-(\d+)\.apk'
    #     __APK_OUTPUT_PATH_FORMAl_PATTERN = '([\d\.]+)-(\d+)-(\d+)\.apk'

    __APK_OUTPUT_PATH_PATTERN = '^([\d\.]+(?:(?:beta_\w+_\d+)|(?:_\w+))?)-(\d+)-(\d+)\.apk$'

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
        configParser = BuildConfigParser(self.base_config)
        configParser.parse()
        self.ori_build_config = configParser.get_config()

        # project目录
        ori_project_path = os.path.join(self.work_path, self.ori_build_config[BuildConfigLabel.WORKSPACE_FLAG][BuildConfigLabel.PRJ_PATH_FLAG])
        self.project_path = file_util.normalpath(ori_project_path)

        self.api_ver_config = None

    def _get_whole_ver_name(self, beta_label_map, label_map):
        beta_label = 'beta'
        ver_no_label = ''

        # 确定是否要展示beta标签
        beta_label_switch = str_utils.get_bool(beta_label_map[self.env_mode])
        if not beta_label_switch:
            beta_label = ''
        else:
            ver_no_label = '_{:02d}'.format(self.ver_no)

        # 确定是否要展示标识环境的标签
        net_env_label = ''
        env_label = label_map[self.ver_env]
        if env_label:
            net_env_label = '_{}'.format(env_label)

        whole_ver_name = '{}{}{}{}'.format(self.ver_name, beta_label, net_env_label, ver_no_label)
        return whole_ver_name

    def _get_code_api_ver(self, file_path, target_key):
        file_data = file_util.read_file_content(file_path)
        ptn_str_format = '({}\s*=\s*)([^\s]*)'
        ptn_str = ptn_str_format.format(target_key)
        ptn = re.compile(ptn_str, flags=(re.I | re.M))

        result = ptn.search(file_data)
        if result:
            return result.group(2)
        else:
            return None

    def _generate_desc(self):
        curr_api_ver = None
        if self.api_ver:
            curr_api_ver = self.api_ver
        else:
            if self.api_ver_config:
                file_item_format = self.api_ver_config[BuildConfigLabel.FILE_ITEM_FLAG]
                file_item = file_item_format.format(app_code=self.app_code)
                relative_path = file_util.normalpath(file_item)
                file_path = os.path.join(self.prj_root, relative_path)
                target_key = self.api_ver_config[BuildConfigLabel.KEY_FLAG]
                curr_api_ver = self._get_code_api_ver(file_path, target_key)

        desc_data = dict()
        desc_data[BuilderLabel.VER_NAME_FLAG] = self.whole_ver_name
        desc_data[BuilderLabel.CODE_VER_FLAG] = self.prj_code_ver
        desc_data[BuilderLabel.VER_CODE_FLAG] = self.ver_code
        if curr_api_ver:
            desc_data[BuilderLabel.API_VER_FLAG] = curr_api_ver

        return desc_data

    # 配置每个工程个性化的内容
    def _get_pro_build_config(self):
        # 指定项目地址
        params = dict()

        params[BuilderLabel.PRJ_ROOT_FLAG] = self.prj_root
        params[BuilderLabel.MAIN_FLAG] = self.ori_build_config[BuildConfigLabel.WORKSPACE_FLAG][BuildConfigLabel.MAIN_FLAG]

        params[BuilderLabel.NET_ENV_FLAG] = self.ver_env
        params[BuilderLabel.ENV_MODE_FLAG] = self.ori_build_config[BuildConfigLabel.ENV_FLAG][BuildConfigLabel.MAP_FLAG][self.ver_env]
        self.env_mode = params[BuilderLabel.ENV_MODE_FLAG]
        params[BuilderLabel.MINIFY_ENABLED_FLAG] = self.minify_enabled
        params[BuilderLabel.UPLOAD_BUGLY_FLAG] = self.upload_bugly

        # 获取网络api version配置信息
        if BuildConfigLabel.API_VER_FLAG in self.ori_build_config[BuildConfigLabel.ENV_FLAG]:
            self.api_ver_config = self.ori_build_config[BuildConfigLabel.ENV_FLAG][BuildConfigLabel.API_VER_FLAG]

        # 获取加固配置信息
        params[BuilderLabel.PROTECT_FLAG] = self.ori_build_config[BuildConfigLabel.PROTECT_FLAG]
        is_need_infos = params[BuilderLabel.PROTECT_FLAG][BuilderLabel.IS_NEED_FLAG]
        for k in is_need_infos:
            is_need_infos[k] = str_utils.get_bool(is_need_infos[k])

        params[BuilderLabel.SIGNER_FLAG] = self.ori_build_config[BuildConfigLabel.SIGNER_FLAG]

        # 将时间格式化
        curr_time = time.localtime()
        time_str = time.strftime('%Y%m%d_%H%M%S', curr_time)

        output_directory = os.path.join(self.work_path, self.ori_build_config[BuildConfigLabel.WORKSPACE_FLAG][BuildConfigLabel.TARGET_PATH_FLAG])
        output_directory = file_util.normalpath(output_directory)
        output_directory = os.path.join(output_directory, self.ver_env, time_str)
        params[BuilderLabel.OUTPUT_DIRECTORY_FLAG] = output_directory

        self.output_directory = params[BuilderLabel.OUTPUT_DIRECTORY_FLAG]

        params[BuilderLabel.VER_NAME_FLAG] = self.ver_name
        params[BuilderLabel.VER_CODE_FLAG] = self.ver_code
        params[BuilderLabel.VER_NO_FLAG] = self.ver_no
        params[BuilderLabel.API_VER_FLAG] = self.api_ver
        params[BuilderLabel.IS_TEST_FLAG] = self.is_test
        params[BuilderLabel.ENTRANCE_FLAG] = self.entrance

        params[BuilderLabel.ENV_FLAG] = self.ori_build_config[BuildConfigLabel.ENV_FLAG]

        # 指定输出归档文件地址
        date_str = time.strftime('%Y%m%d', curr_time)

        label_map = self.ori_build_config[BuildConfigLabel.ENV_FLAG][BuildConfigLabel.LABEL_FLAG]
        beta_label_map = self.ori_build_config[BuildConfigLabel.ENV_FLAG][BuildConfigLabel.BETA_LABEL_FLAG]
        self.whole_ver_name = self._get_whole_ver_name(beta_label_map, label_map)
        if self.is_debug:
            mode_flag = apk_builder.DEBUG_FLAG
            # 指定输出apk名称
            params[BuilderLabel.OUTPUT_NAME_FLAG] = "{}-{}-{}-{}.apk".format(self.whole_ver_name, self.ver_code, mode_flag, date_str)
        else:
            mode_flag = apk_builder.RELEASE_FLAG
            # 指定输出apk名称
            params[BuilderLabel.OUTPUT_NAME_FLAG] = "{}-{}-{}.apk".format(self.whole_ver_name, self.ver_code, date_str)

        params[BuilderLabel.TYPE_FLAG] = mode_flag
        self.apk_output_path = os.path.join(params[BuilderLabel.OUTPUT_DIRECTORY_FLAG], params[BuilderLabel.OUTPUT_NAME_FLAG])

        pprint.pprint(params)

        return params

    def process(self):
        main_prj_name = self.ori_build_config[BuildConfigLabel.WORKSPACE_FLAG][BuildConfigLabel.MAIN_FLAG]
        self.project_code_path = os.path.join(self.project_path, self.branch)

        # 进行代码更新操作
        if self.to_update:
            code_url = self.ori_build_config[BuildConfigLabel.ROOT_FLAG][BuildConfigLabel.CODE_URL_FLAG]
            git.checkout_or_update(self.project_code_path, code_url, self.code_ver, self.branch)

        # 设置配置信息并获取当前代码版本号
        self.prj_root = git.get_git_root(self.project_code_path)
        main_prj_path = os.path.join(self.prj_root, main_prj_name)
        self.prj_code_ver = git.get_revision(self.prj_root)
        print('current code version is ' + self.prj_code_ver)

        # 下面这部分代码依赖于前面成员变量的初始化，请不要随意调整执行位置
        if self.to_update:
            self._update_local_build_file()

        # 进行版本编译操作
        if self.to_build:
            to_check_vals = ['ver_name', 'ver_code', 'ver_env']
            for name in to_check_vals:
                value = getattr(self, name)
                if not value:
                    info = 'Please specify the {}.'.format(name)
                    print(info)
                    exit(1)

            # 参数非空判断验证通过开始进行正式业务逻辑
            self.pro_build_config = self._get_pro_build_config()
            self.build_app(self.pro_build_config)

            if os.path.exists(self.apk_output_path) and os.path.isfile(self.apk_output_path):
                # 将编译信息写文件
                self._write_build_info()
                # 生成apk描述信息
                desc_data = self._generate_desc()
                # 打包并上传bugly符号表文件
                self._upload_bugly_symbol_files(main_prj_path)

                target_name = os.path.basename(self.apk_output_path)
                to_upload_path = os.path.dirname(self.apk_output_path)
                source_name = os.path.basename(self.apk_output_path)

                # 有需要则先加固，再签名
                if BuilderLabel.PROTECT_FLAG in self.pro_build_config and BuilderLabel.SIGNER_FLAG in self.pro_build_config:
                    env_mode = self.pro_build_config[BuilderLabel.ENV_MODE_FLAG]
                    if self.pro_build_config[BuilderLabel.PROTECT_FLAG][BuilderLabel.IS_NEED_FLAG][env_mode]:
                        source_name = self._protect_file(main_prj_path)

                str_info = 'Build success, code version is {}.'.format(self.prj_code_ver)
                print(str_info)

                # 进行编译好的版本提交操作
                if hasattr(self, 'to_upload') and self.to_upload:
                    self._upload_file(source_name, target_name, to_upload_path, desc_data=desc_data)
            else:
                str_info = 'Build failed, code version is {}.'.format(self.prj_code_ver)
                print(str_info)

    def build_app(self, info):
        prj_builder = ProjectBuilder(info)
        prj_builder.update_info()
        prj_builder.build()

    def _update_local_build_file(self):
        # 更新android sdk本地配置
        local_file_name = 'local.properties'
        static_config_path = os.path.join(self.work_path, self.ori_build_config[BuildConfigLabel.ROOT_FLAG][BuildConfigLabel.STATIC_FLAG])
        static_config_path = file_util.normalpath(static_config_path)
        local_build_file = os.path.join(static_config_path, local_file_name)
        target_build_file = os.path.join(self.prj_root, local_file_name)
        file_util.replace_file(local_build_file, target_build_file)

    # 将编译信息写到文件中
    def _write_build_info(self):
        build_info_format = self.ori_build_config[BuildConfigLabel.BUILD_INFO_TEMPLET_FLAG]
        build_info = build_info_format.format(ver_name=self.whole_ver_name, code_ver=self.prj_code_ver, ver_code=self.ver_code)
        readme_file_name = 'readme-{}-{}.txt'.format(self.whole_ver_name, self.ver_code)
        build_info_path = os.path.join(self.output_directory, readme_file_name)
        file_util.write_to_file(build_info_path, build_info, encoding='utf-8')

    # 打包并上传符号表文件到bugly，前提是启用了代码混淆并且开启了上传到bugly的开关
    def _upload_bugly_symbol_files(self, main_prj_path):
        if self.minify_enabled and self.upload_bugly:
            try:
                build_type = self.pro_build_config[BuilderLabel.TYPE_FLAG].title()
                app_code = self.pro_build_config[BuilderLabel.APP_CODE_FLAG]
                ori_net_env = self.pro_build_config[BuilderLabel.NET_ENV_FLAG]
                net_env = self.pro_build_config[BuilderLabel.ENV_FLAG][BuilderLabel.GRADLE_FLAG][ori_net_env]
                mapping_out_path = main_prj_path + f'/build/outputs/mapping/{net_env}{build_type}/'
                mapping_file_name = os.path.join(mapping_out_path, 'mapping.txt')
                mapping_zip_name = 'mapping-{}-{}.zip'.format(self.whole_ver_name, self.ver_code)
                mapping_info_path = os.path.join(self.output_directory, mapping_zip_name)
                file_items = file_util.get_child_files(mapping_out_path)
                print('zip mapping files into {}.'.format(mapping_info_path))
                zip_util.zip_files(file_items, mapping_info_path, mapping_out_path, True)
                print('upload bugly symbol ... ver_env:{}, app_code:{}, app_version:{}, mapping_file:{}'.format(net_env.lower(), app_code, self.whole_ver_name, mapping_file_name))
                BuglyManager(self.work_path).uploadSymbol(net_env.lower(), app_code, self.whole_ver_name, mapping_file_name)
            except Exception:
                print('upload bugly symbol files error.')

    def _protect_file(self, main_prj_path):
        ip = self.pro_build_config[BuilderLabel.PROTECT_FLAG][BuilderLabel.IP_FLAG]
        user_name = self.pro_build_config[BuilderLabel.PROTECT_FLAG][BuilderLabel.USER_FLAG]
        api_key = self.pro_build_config[BuilderLabel.PROTECT_FLAG][BuilderLabel.API_KEY_FLAG]
        api_secret = self.pro_build_config[BuilderLabel.PROTECT_FLAG][BuilderLabel.API_SECRET_FLAG]
        protected_path = protect_app.protect(ip, user_name, api_key, api_secret, self.apk_output_path)
        if self.to_align:
            aligned_path = file_util.get_middle_path(protected_path)
            apk_util.zipalign(protected_path, aligned_path)
            to_sign_path = aligned_path
        else:
            to_sign_path = protected_path

        keystore = os.path.join(main_prj_path, self.pro_build_config[BuilderLabel.SIGNER_FLAG][BuilderLabel.KEYSTORE_FLAG])
        storepass = self.pro_build_config[BuilderLabel.SIGNER_FLAG][BuilderLabel.STOREPASS_FLAG]
        storealias = self.pro_build_config[BuilderLabel.SIGNER_FLAG][BuilderLabel.STOREALIAS_FLAG]
        signed_path = apk.get_default_signed_path(protected_path)
        rtn = apk.sign_apk(keystore, storepass, storealias, to_sign_path, signed_path)
        if rtn:
            str_info = 'Protect {} and sign success.'.format(self.apk_output_path)
            source_name = os.path.basename(signed_path)
        else:
            str_info = 'Protect {} and sign failed!'.format(self.apk_output_path)
            raise Exception(str_info)

        print(str_info)

        return source_name

    def _upload_file(self, source_name, target_name, to_upload_path, desc_data=None):
        result = re.match(BuildManager.__APK_OUTPUT_PATH_PATTERN, target_name)
        if result:
            ver_name_info = result.group(1)
        else:
            str_info = 'The output file name {} is invalid!'.format(target_name)
            print(str_info)
            raise Exception(str_info)

        # ftp_config_path = os.path.join(self.work_path, 'config')
        ftp_config_path = self.work_path
        print('ver_name_info:', ver_name_info)
        print('target_name: ', target_name)
        print('source_name:', source_name)

        ftp_upload.upload_to_sftp(ftp_config_path, ver_name_info, self.ver_env, self.prj_code_ver, 'gzjd', to_upload_path, mobile_os='Android', target_file_name=target_name, source_file_name=source_name, desc_data=desc_data)


def main(args):
    manager = BuildManager(args)
    manager.process()


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='update code if need, build if need.')
    parser.add_argument('work_path', metavar='work_path', help='working directory')

    parser.add_argument('-c', metavar='base_config', dest='base_config', help='base configure file, path relative to work path')
    parser.add_argument('-u', dest='to_update', action='store_true', default=False, help='indicate to get or update code firstly')
    parser.add_argument('-b', dest='to_build', action='store_true', default=False, help='indicate to build')
    parser.add_argument('-v', metavar='code_ver', dest='code_ver', action='store', default=None, help='indicate updating to special version')
    parser.add_argument('-d', dest='is_debug', action='store_true', default=False, help='indicate to build debug version')

    parser.add_argument('--vername', metavar='ver_name', dest='ver_name', help='version name')
    parser.add_argument('--vercode', metavar='ver_code', dest='ver_code', type=int, help='version code')
    parser.add_argument('--verno', metavar='ver_no', dest='ver_no', type=int, default=0, help='version release number')
    parser.add_argument('--verenv', metavar='ver_env', dest='ver_env', type=str, default='test', choices=['dev', 'test', 'pre', 'pro'],
                        help='dev: develop environment; test: test environment; pre: pre-release environment; pro: production environment; ')

    parser.add_argument('--apiver', metavar='api_ver', dest='api_ver', type=str, help='network api version number')

    parser.add_argument('--test', dest='is_test', action='store_true', default=False, help='indicate just to test config')
    parser.add_argument('--align', dest='to_align', action='store_true', default=True, help='indicate to align apk file after protected')
    parser.add_argument('--upload', dest='to_upload', action='store_true', default=False, help='indicate to upload build files')
    parser.add_argument('--branch', metavar='branch', dest='branch', default='master', help='code branch name')
    parser.add_argument('--entrance', metavar='entrance', dest='entrance', default='https://www.gongzhongjiandu.org/', help='web entrance')
    parser.add_argument('--minify', dest='minify_enabled', action='store_true', default=False, help='whether to enable code obfuscation or not')
    parser.add_argument('--upload_bugly', dest='upload_bugly', action='store_true', default=True, help='upload bugly symbol files, mapping.txt etc.')

    #     parser.print_help()

    return parser.parse_args(src_args)


if __name__ == '__main__':
    test_args = None
    args = get_args(test_args)
    utility.measure_time(main, args)
