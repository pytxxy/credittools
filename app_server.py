import threading
from typing import Tuple
from rpyc import Service
from rpyc.utils.server import ThreadedServer
from creditutils.trivial_util import print_t
import os
import time
import re
from enum import IntEnum
import platform
import shutil
import logging
import datetime

import ftp_upload
import creditutils.apk_builder_util as apk_builder
import creditutils.file_util as file_util
import pprint
# import traceback
import creditutils.str_util as str_utils
import creditutils.trivial_util as trivial_util
import creditutils.git_util as git
import argparse
import subprocess
import xmltodict
import protect_android_app as protect_app
import creditutils.zip_util as zip_util
import creditutils.apk_util as apk_util

from central_control import DEFAULT_LISTEN_TIMEOUT

'''
The reason services have names is for the service registry: 
normally, a server will broadcast its details to a nearby registry server for discovery. 
To use service discovery, a make sure you start the bin/rpyc_registry.py. 
This server listens on a broadcast UDP socket, and will answer to queries about which services are running where.

上面是官网原始说明，简单地说，如果要通过服务名称调用服务，则需要调用bin/rpyc_registry.py启动名称服务。实际研究显示，
在一个互通的网络中，启动一个该服务即可。
windows 下面可使用网盘“/develop/python/rpyc/runpy.bat”文件，可简化调用。
'''

_input_args = dict()

class LocalLogger:
    lock = threading.Lock()
    whole_path = None
    instance = None

    @staticmethod
    def get_logger_with_path(target_dir, to_console=True):
        with LocalLogger.lock:
            today = datetime.datetime.now().strftime('%Y%m%d')
            log_path = os.path.join(os.path.abspath(target_dir), f'{today}.log')
            if LocalLogger.whole_path == log_path and not LocalLogger.instance:
                return LocalLogger.instance

            parent = os.path.dirname(log_path)
            if not os.path.isdir(parent):
                os.makedirs(parent)

            logger = logging.getLogger(__name__)
            logger.setLevel(level = logging.INFO)
            handler = logging.FileHandler(log_path)
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s-%(name)s-%(levelname)s: %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)

            if to_console:
                # 设置输出到控制台
                handler_console = logging.StreamHandler() # 输出到控制台的handler
                handler_console.setFormatter(formatter)
                handler_console.setLevel(logging.INFO)  # 也可以不设置，不设置就默认用logger的level
                logger.addHandler(handler_console)

            LocalLogger.whole_path = log_path
            LocalLogger.instance = logger

            return LocalLogger.instance

    @staticmethod
    def reset_handlers():
        # 重置handlers，以免重复输出日志
        logger = LocalLogger.instance
        if logger.hasHandlers():
            logger.handlers.clear()


def get_logger():
    return LocalLogger.get_logger_with_path(_input_args['log_dir'])

def log_info(data):
    get_logger().info(data)
    LocalLogger.reset_handlers()

def log_debug(data):
    get_logger().debug(data)    
    LocalLogger.reset_handlers()

def log_warn(data):
    get_logger().warn(data)
    LocalLogger.reset_handlers()

def log_error(data):
    get_logger().error(data)
    LocalLogger.reset_handlers()

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
    CHANNEL_FLAG = 'channel'

    ENV_FLAG = 'env'
    NET_ENV_FLAG = 'net_env'
    ENV_MODE_FLAG = 'env_mode'
    KEY_FLAG = 'key'
    TYPE_FLAG = 'type'
    FILE_ITEM_FLAG = 'file_item'
    GRADLE_FLAG = 'gradle'
    ARM64_FLAG = 'arm64'
    FOR_GOOGLE_FLAG = 'for_google'

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

    COVERAGE_FLAG = 'coverage'
    COMPILE_FLAG = 'compile'
    OUTPUT_DIRECTORY_FLAG = 'output_directory'
    OUTPUT_NAME_FLAG = 'output_name'
    VER_NAME_FLAG = 'ver_name'
    VER_CODE_FLAG = 'ver_code'
    VER_NO_FLAG = 'ver_no'
    IS_TEST_FLAG = 'is_test'
    APP_NAME_FLAG = 'app_name'
    DEMO_LABEL_FLAG = 'demo_label'
    API_VER_FLAG = 'api_ver'
    APP_CODE_FLAG = 'app_code'

    LABEL_FLAG = 'label'
    BETA_LABEL_FLAG = 'beta_label'
    HTTPDNS_FLAG = 'httpdns'

    CODE_VER_FLAG = 'code_ver'
    JPUSH_APPKEY_FLAG = 'jpush_appkey'


class BuildCmd:
    exec_name = f'gradlew{_system_suffix}'
    pre_cmd = exec_name + ' --configure-on-demand clean'

    basic_map_key = ['action', 'net_env', 'build_type', 'ver_name', 'ver_code', 'ver_no', 'app_code', 'for_publish',
               'coverage_enabled', 'httpdns', 'demo_label', 'is_arm64', 'for_google', 'app_name', 'channel']

    extend_map_key = {'API_VERSION':'api_ver', 'JPUSH_APPKEY':'jpush_appkey'}

    cmd_format = exec_name + ' --no-daemon {action}{app_code}{net_env}{build_type} -PAPP_BASE_VERSION={ver_name} ' \
                      '-PAPP_VERSION_CODE={ver_code} -PAPP_RELEASE_VERSION={ver_no} -PBUILD_INCLUDE_ARM64={is_arm64} ' \
                      '-PBUILD_FOR_GOOGLE_PLAY={for_google} -PFOR_PUBLISH={for_publish} -PTEST_COVERAGE_ENABLED={coverage_enabled} ' \
                      '-PHTTP_DNS_OPEN={httpdns} -PDEMO_LABEL={demo_label} -PCUSTOM_APP_NAME={app_name} -PDEFAULT_CHANNEL={channel}'

    def __init__(self):
        # 先初始化默认值
        self.action = 'assemble'
        self.net_env = 'tst1'
        self.build_type = 'Release'
        self.ver_name = '1.0.0'
        self.ver_code = 0
        self.ver_no = '00'
        self.api_ver = None
        self.app_code = None
        self.for_publish = str(True).lower()
        self.coverage_enabled = str(True).lower()
        self.httpdns = str(False).lower()
        self.channel = BuilderLabel.DEFAULT_CHAN
        self.demo_label = 'normal'
        self.jpush_appkey = None

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
        self.app_code = info[BuilderLabel.APP_CODE_FLAG].capitalize()

        env_mode = info[BuilderLabel.ENV_MODE_FLAG]
        self.coverage_enabled = info[BuilderLabel.COVERAGE_FLAG][BuilderLabel.COMPILE_FLAG][env_mode].lower()
        self.httpdns = info[BuilderLabel.ENV_FLAG][BuilderLabel.HTTPDNS_FLAG][env_mode].lower()
        self.demo_label = info[BuilderLabel.DEMO_LABEL_FLAG]
        self.is_arm64 = str(info[BuilderLabel.ARM64_FLAG]).lower()
        self.for_google = str(info[BuilderLabel.FOR_GOOGLE_FLAG]).lower()
        self.app_name = info[BuilderLabel.APP_NAME_FLAG]
        self.channel = info[BuilderLabel.CHANNEL_FLAG]
        self.jpush_appkey = info[BuilderLabel.JPUSH_APPKEY_FLAG]

    def get_basic_map(self):
        rtn_map = {}
        for item in BuildCmd.basic_map_key:
            value = getattr(self, item)
            if value:
                rtn_map[item] = getattr(self, item)

        return rtn_map

    def get_build_cmd(self, info):
        self.update_value(info)
        params = self.get_basic_map()
        cmd_str = BuildCmd.cmd_format.format(**params)

        extend_map_key = BuildCmd.extend_map_key
        for k in extend_map_key:
            value = getattr(self, extend_map_key[k])
            if value:
                extend_para = f' -P{k}={value}'
                cmd_str = cmd_str + extend_para

        log_info(cmd_str)

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
            log_info(pre_build_cmd)
            subprocess.check_call(pre_build_cmd, shell=True)

        build_cmd = _system_pre + os.path.join(os.path.dirname(work_path), cmd_str)
        log_info(build_cmd)
        subprocess.check_call(build_cmd, shell=True)
        # os.system(build_cmd)
    except subprocess.CalledProcessError:
        raise
    finally:
        if dir_change:
            os.chdir(pre_cwd)


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
        app_code = self.info[BuilderLabel.APP_CODE_FLAG] 
        net_env = self.info[BuilderLabel.ENV_FLAG][BuilderLabel.GRADLE_FLAG][ori_net_env]

        # 配置为Release还是Debug模式
        build_type = self.info[BuilderLabel.TYPE_FLAG]

        relative_path = os.path.join(app_code + net_env.capitalize(), build_type)
        log_info(relative_path)

        return relative_path

    def build(self):
        log_info('building apk begin ...')

        # 获取apk名称
        apk_name = os.path.basename(self.main_prj_path)

        apk_out_path = self.main_prj_path + '/build/outputs/apk/'
        # build_type = self.info[BuilderLabel.TYPE_FLAG]
        # 默认名称形式
        # apk_path = '{}{}-{}.apk'.format(apk_out_path, apk_name, build_type)
        # 自定义名称形式
        apk_path = os.path.join(apk_out_path, self._get_output_relative_path(),
                                self.info[BuilderLabel.OUTPUT_NAME_FLAG])
        apk_path = os.path.normpath(apk_path)

        # 先把现有的apk文件直接删除
        if os.path.exists(apk_path) and os.path.isfile(apk_path):
            os.remove(apk_path)

        cmd_str = self.get_build_cmd()
        make_apk_with_gradle(self.main_prj_path, cmd_str)

        src_file = apk_path
        log_info('source apk path: {}'.format(src_file))

        if os.path.exists(src_file):
            apk_items = apk_util.get_apk_info(src_file)

            actual_ver_name = self.get_main_ver_name(apk_items['versionName'])
            if actual_ver_name != self.info[BuilderLabel.VER_NAME_FLAG]:
                info = 'set version name is {}, but actual is {}!'.format(self.info[BuilderLabel.VER_NAME_FLAG],
                                                                          actual_ver_name)
                log_error(info)
                raise Exception(info)

            if apk_items['versionCode'] != str(self.info[BuilderLabel.VER_CODE_FLAG]):
                info = 'set version code is {}, but actual is {}!'.format(self.info[BuilderLabel.VER_CODE_FLAG],
                                                                          apk_items['versionCode'])
                log_error(info)
                raise Exception(info)

            dst_file = self.info[BuilderLabel.OUTPUT_DIRECTORY_FLAG] + os.sep + self.info[
                BuilderLabel.OUTPUT_NAME_FLAG]
            file_util.replace_file(src_file, dst_file)

            log_info('built the apk {}.'.format(dst_file))
        else:
            log_error('build {} failed!'.format(apk_name))

    def get_main_ver_name(self, whole_name):
        ptn_str = '^(\d+(?:\.\d+)+)(?![.\d])'
        rtn = re.match(ptn_str, whole_name)
        if rtn:
            return rtn.group(1)
        else:
            info = f'{whole_name} is invalid!'
            log_error(info)
            raise Exception(info)


class BuildConfigLabel:
    ROOT_FLAG = 'config'
    WORKSPACE_FLAG = 'workspace'
    PRJ_PATH_FLAG = 'prj_path'
    MAIN_FLAG = 'main'
    TARGET_PATH_FLAG = 'target_path'

    STATIC_FLAG = 'static'
    CODE_URL_FLAG = 'code_url'

    API_VER_FLAG = 'api_ver'
    FILE_ITEM_FLAG = 'file_item'
    KEY_FLAG = 'key'

    PROTECT_FLAG = 'protect'
    IS_NEED_FLAG = 'is_need'

    SIGNER_FLAG = 'signer'

    COVERAGE_FLAG = 'coverage'
    ENV_FLAG = 'env'
    MAP_FLAG = 'map'
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

    __APK_OUTPUT_PATH_PATTERN = '^([\d\.]+(?:(?:beta_\w+_\d+)|(?:_\w+))?)-(\d+)(?:-debug)?-(\d+)\.apk$'

    def __init__(self, args, work_path):
        # 先将输入的控制参数全部存储为成员变量
        # 透传过来的数据类型为“netref class 'rpyc.core.netref.type'”，不支持dict的方法items，需要换成键访问方式
        # for name, value in args.items():
        #     setattr(self, name, value)
        for k in args:
            setattr(self, k, args[k])

        # pprint.pprint(vars(self))

        self.work_path = os.path.abspath(work_path)

        # 解析基础配置文件路径
        base_config_dirs = ['config', 'base', 'update_config.xml']
        base_config = os.sep.join(base_config_dirs)
        self.base_config = os.path.join(self.work_path, base_config)

        # 先解析配置
        configParser = BuildConfigParser(self.base_config)
        configParser.parse()
        self.ori_build_config = configParser.get_config()

        # project目录
        ori_project_path = os.path.join(self.work_path, self.ori_build_config[BuildConfigLabel.WORKSPACE_FLAG][
            BuildConfigLabel.PRJ_PATH_FLAG])
        self.project_path = file_util.normalpath(ori_project_path)

        self.api_ver_config = None
        self.curr_env_output_root = None

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
                relative_path = file_util.normalpath(self.api_ver_config[BuildConfigLabel.FILE_ITEM_FLAG])
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
        params[BuilderLabel.MAIN_FLAG] = self.ori_build_config[BuildConfigLabel.WORKSPACE_FLAG][
            BuildConfigLabel.MAIN_FLAG]

        params[BuilderLabel.CHANNEL_FLAG] = self.channel

        params[BuilderLabel.NET_ENV_FLAG] = self.ver_env
        params[BuilderLabel.ENV_MODE_FLAG] = \
            self.ori_build_config[BuildConfigLabel.ENV_FLAG][BuildConfigLabel.MAP_FLAG][self.ver_env]
        self.env_mode = params[BuilderLabel.ENV_MODE_FLAG]
        params[BuilderLabel.ARM64_FLAG] = self.is_arm64
        params[BuilderLabel.FOR_GOOGLE_FLAG] = self.for_google
        params[BuilderLabel.JPUSH_APPKEY_FLAG] = self.jpush_appkey
        
        # 获取网络api version配置信息
        if BuildConfigLabel.API_VER_FLAG in self.ori_build_config[BuildConfigLabel.ENV_FLAG]:
            self.api_ver_config = self.ori_build_config[BuildConfigLabel.ENV_FLAG][BuildConfigLabel.API_VER_FLAG]

        # 获取加固配置信息
        params[BuilderLabel.PROTECT_FLAG] = self.ori_build_config[BuildConfigLabel.PROTECT_FLAG]
        is_need_infos = params[BuilderLabel.PROTECT_FLAG][BuilderLabel.IS_NEED_FLAG]
        for k in is_need_infos:
            is_need_infos[k] = str_utils.get_bool(is_need_infos[k])

        params[BuilderLabel.SIGNER_FLAG] = self.ori_build_config[BuildConfigLabel.SIGNER_FLAG]
        params[BuilderLabel.COVERAGE_FLAG] = self.ori_build_config[BuildConfigLabel.COVERAGE_FLAG]

        # 将时间格式化
        curr_time = time.localtime()
        time_str = time.strftime('%Y%m%d_%H%M%S', curr_time)

        output_directory = os.path.join(self.work_path, self.ori_build_config[BuildConfigLabel.WORKSPACE_FLAG][
            BuildConfigLabel.TARGET_PATH_FLAG])
        output_directory = file_util.normalpath(output_directory)
        self.curr_env_output_root = os.path.join(output_directory, self.ver_env)
        output_directory = os.path.join(output_directory, self.ver_env, time_str)
        params[BuilderLabel.OUTPUT_DIRECTORY_FLAG] = output_directory

        self.output_directory = params[BuilderLabel.OUTPUT_DIRECTORY_FLAG]

        params[BuilderLabel.VER_NAME_FLAG] = self.ver_name
        params[BuilderLabel.VER_CODE_FLAG] = self.ver_code
        params[BuilderLabel.VER_NO_FLAG] = self.ver_no
        params[BuilderLabel.API_VER_FLAG] = self.api_ver
        params[BuilderLabel.APP_CODE_FLAG] = self.app_code
        params[BuilderLabel.IS_TEST_FLAG] = self.is_test

        params[BuilderLabel.ENV_FLAG] = self.ori_build_config[BuildConfigLabel.ENV_FLAG]

        params[BuilderLabel.APP_NAME_FLAG] = self.app_name
        params[BuilderLabel.DEMO_LABEL_FLAG] = self.demo_label

        # 指定输出归档文件地址
        date_str = time.strftime('%Y%m%d', curr_time)

        label_map = self.ori_build_config[BuildConfigLabel.ENV_FLAG][BuildConfigLabel.LABEL_FLAG]
        beta_label_map = self.ori_build_config[BuildConfigLabel.ENV_FLAG][BuildConfigLabel.BETA_LABEL_FLAG]
        self.whole_ver_name = self._get_whole_ver_name(beta_label_map, label_map)
        if self.is_debug:
            mode_flag = apk_builder.DEBUG_FLAG

            # 指定输出apk名称
            params[BuilderLabel.OUTPUT_NAME_FLAG] = "{}-{}-{}-{}.apk".format(self.whole_ver_name, self.ver_code,
                                                                             mode_flag,
                                                                             date_str)
        else:
            mode_flag = apk_builder.RELEASE_FLAG

            # 指定输出apk名称
            params[BuilderLabel.OUTPUT_NAME_FLAG] = "{}-{}-{}.apk".format(self.whole_ver_name, self.ver_code, date_str)

        params[BuilderLabel.TYPE_FLAG] = mode_flag
        self.apk_output_path = os.path.join(params[BuilderLabel.OUTPUT_DIRECTORY_FLAG],
                                            params[BuilderLabel.OUTPUT_NAME_FLAG])

        pprint.pprint(params)

        return params

    def _clear_output_directory(self, root_dir, to_reserve=2):
        # print(f'_clear_output_directory, root_dir: {root_dir}.')
        if not os.path.isdir(root_dir):
            return

        file_list = os.listdir(root_dir)
        length = len(file_list)
        index = 0
        index_butt = length - to_reserve
        for filename in file_list:
            if index < index_butt:
                index += 1
                sub_dir = os.path.join(root_dir, filename)
                if os.path.isdir(sub_dir):
                    shutil.rmtree(sub_dir)
            else:
                break

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
        log_info('current code version is ' + self.prj_code_ver)

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
                    log_error(info)
                    exit(1)

            # 参数非空判断验证通过开始进行正式业务逻辑
            self.pro_build_config = self._get_pro_build_config()
            # 在进行编译前先进行空间清理操作
            self._clear_output_directory(self.curr_env_output_root)
            self.build_app(self.pro_build_config)

            if os.path.exists(self.apk_output_path) and os.path.isfile(self.apk_output_path):
                # 将编译信息写文件
                self._write_build_info()
                # 生成apk描述信息
                desc_data = self._generate_desc()

                target_name = os.path.basename(self.apk_output_path)
                to_upload_path = os.path.dirname(self.apk_output_path)
                source_name = os.path.basename(self.apk_output_path)

                # 有需要则先加固，再签名
                if BuilderLabel.PROTECT_FLAG in self.pro_build_config and BuilderLabel.SIGNER_FLAG in self.pro_build_config:
                    env_mode = self.pro_build_config[BuilderLabel.ENV_MODE_FLAG]
                    if self.pro_build_config[BuilderLabel.PROTECT_FLAG][BuilderLabel.IS_NEED_FLAG][env_mode]:
                        source_name = self._protect_file(main_prj_path)

                str_info = 'Build success, code version is {}.'.format(self.prj_code_ver)
                log_info(str_info)

                # 进行编译好的版本提交操作
                if hasattr(self, 'to_upload') and self.to_upload:
                    self._upload_file(source_name, target_name, to_upload_path, desc_data=desc_data)
            else:
                str_info = 'Build failed, code version is {}.'.format(self.prj_code_ver)
                log_error(str_info)

    def build_app(self, info):
        prj_builder = ProjectBuilder(info)
        prj_builder.update_info()
        prj_builder.build()

    def _update_local_build_file(self):
        # 更新android sdk本地配置
        local_file_name = 'local.properties'
        static_config_path = os.path.join(self.work_path, self.ori_build_config[BuildConfigLabel.ROOT_FLAG][
            BuildConfigLabel.STATIC_FLAG])
        static_config_path = file_util.normalpath(static_config_path)
        local_build_file = os.path.join(static_config_path, local_file_name)
        target_build_file = os.path.join(self.prj_root, local_file_name)
        file_util.replace_file(local_build_file, target_build_file)

    # 将编译信息写到文件中
    def _write_build_info(self):
        build_info_format = self.ori_build_config[BuildConfigLabel.BUILD_INFO_TEMPLET_FLAG]
        build_info = build_info_format.format(ver_name=self.whole_ver_name, code_ver=self.prj_code_ver,
                                              ver_code=self.ver_code)
        readme_file_name = 'readme-{}-{}.txt'.format(self.whole_ver_name, self.ver_code)
        build_info_path = os.path.join(self.output_directory, readme_file_name)
        file_util.write_to_file(build_info_path, build_info, encoding='utf-8')

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

        keystore = os.path.join(main_prj_path, self.pro_build_config[BuilderLabel.SIGNER_FLAG][
            BuilderLabel.KEYSTORE_FLAG])
        keystore = os.path.abspath(file_util.normalpath(keystore))
        storepass = self.pro_build_config[BuilderLabel.SIGNER_FLAG][BuilderLabel.STOREPASS_FLAG]
        storealias = self.pro_build_config[BuilderLabel.SIGNER_FLAG][BuilderLabel.STOREALIAS_FLAG]
        signed_path = apk_util.get_default_signed_path(protected_path)
        rtn = apk_util.sign_apk(keystore, storepass, storealias, to_sign_path, signed_path)
        if rtn:
            str_info = 'Protect {} and sign success.'.format(self.apk_output_path)
            source_name = os.path.basename(signed_path)
            log_info(str_info)
        else:
            str_info = 'Protect {} and sign failed!'.format(self.apk_output_path)
            log_error(str_info)
            raise Exception(str_info)

        return source_name

    def _upload_file(self, source_name, target_name, to_upload_path, desc_data = None):
        result = re.match(BuildManager.__APK_OUTPUT_PATH_PATTERN, target_name)
        if result:
            ver_name_info = result.group(1)
        else:
            str_info = 'The output file name {} is invalid!'.format(target_name)
            log_error(str_info)
            raise Exception(str_info)

        channel = '' # 调用的接口内部实现默认是空串
        if self.channel != BuilderLabel.DEFAULT_CHAN:
            channel = self.channel

        # ftp_config_path = os.path.join(self.work_path, 'config')
        ftp_config_path = self.work_path
        log_info(f'ver_name_info: {ver_name_info}')
        log_info(f'target_name: {target_name}')
        log_info(f'source_name: {source_name}')
        log_info(f'channel: {channel}')

        ftp_upload.upload_to_sftp(ftp_config_path, ver_name_info, self.ver_env, self.prj_code_ver, self.app_code,
                                  to_upload_path, mobile_os='Android', channel=channel, target_file_name=target_name,
                                  source_file_name=source_name, desc_data=desc_data)


class AppService(Service):
    ALIASES = ['execution_unit']

    def __init__(self) -> None:
        super().__init__()
        log_info(f'{self.get_service_name().lower()} init success.')

    def exposed_compile(self, data) -> Tuple[int, str]:
        '''
        编译完成后输出结果
        :param data: 编译参数
        :return:
        '''
        try:
            log_info(str(data))
            log_info(f'type(data): {type(data)}')
            manager = BuildManager(data, _input_args['work_path'])
            manager.process()
            # time.sleep(150)
            code = 0
            msg = 'success'
        except Exception as e:
            code = 0
            # msg = 'failed'
            msg = str(e)

        return code, msg


def start_server():
    obj = AppService()
    s = ThreadedServer(obj, port=9999, auto_register=True, listener_timeout=DEFAULT_LISTEN_TIMEOUT)
    s.start()


def main(args):
    for name, value in vars(args).items():
        _input_args[name] = value
    start_server()


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='config log dir and work path')
    parser.add_argument('-d', dest='log_dir', help='logs dir', default='/data/log/app_server')
    parser.add_argument('-p', dest='work_path', help='work path', default='/data/android/auto_build/pytxxy')
    return parser.parse_args(src_args)

if __name__ == '__main__':
    test_args = None
    args = get_args(test_args)
    trivial_util.measure_time(main, args)