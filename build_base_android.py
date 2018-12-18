# -*- coding:UTF-8 -*-
# 20161109 21:30 根据android 新框架进行适当地调整 
import os
import re
import time
import filecmp
import creditutils.apk_builder_util as apk_builder
import creditutils.file_util as file_util
import creditutils.apk_util as apk_util
import pprint
import creditutils.svn_util as svn
import creditutils.git_util as git
import subprocess
# import traceback
import xmltodict
import argparse
# import shutil
from creditutils import str_util
import protect_android_app as protect_app
import ftp_upload
import creditutils.zip_util as zip_util


# 对整个工程内相关文件进行替换操作
class ProjectBuilder:
    PRJ_ROOT_FLAG = 'prj_root'
    DEFAULT_CHAN = 'pycredit'

    ENC_BIN_PATH_FLAG = 'enc_bin_path'
    NET_CONFIG_PATH_FLAG = 'net_config_path'
    NET_INFO_FLAG = 'net_info'
    DEV_FLAG = 'dev'
    DEVELOP_FLAG = 'develop'
    HOST_FLAG = 'host'
    PORT_FLAG = 'port'
    SSLPORT_FLAG = 'sslport'

    JPUSH_APPKEY_FLAG = 'jpush_appkey'
    ENV_FLAG = 'env'
    ENV_NET_FLAG = 'env_net'
    ENV_MODE_FLAG = 'env_mode'
    TYPE_FLAG = 'type'
    ENCRYPT_ITEMS_FLAG = 'encrypt_items'
    FILE_ITEM_FLAG = 'file_item'

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

    TINGYUN_APPKEY_FLAG = 'tingyun_appkey'  # 听云在编译配置文件中的键
    MONITOR_APPKEY_FLAG = 'MONITOR_APPKEY'  # 听云license 在工程中对应的键

    OUTPUT_DIRECTORY_FLAG = 'output_directory'
    OUTPUT_NAME_FLAG = 'output_name'
    VER_NAME_FLAG = 'ver_name'
    VER_CODE_FLAG = 'ver_code'

    APP_NAME_FLAG = 'app_name'

    # 应用名称相对路径及id标识
    STR_REL_PATH_FLAG = 'str_rel_path'
    STR_ID_FLAG = 'str_id'

    def __init__(self, prj_path, chan_map, res_path, info):
        self.prj_path = prj_path
        self.chan_map = chan_map
        self.res_path = res_path
        self.info = info

        self.manifest_path = os.path.join(self.prj_path, 'AndroidManifest.xml')

    '''更新通用信息'''

    def update_info(self):
        '''准备好解密文件环境'''
        enc_bin_path = self.info[ProjectBuilder.ENC_BIN_PATH_FLAG]
        preproc = FileEncryptDecrypt(enc_bin_path)

        # 更新网络配置
        net_info = self.info[ProjectBuilder.NET_INFO_FLAG]
        net_config_path = self.info[ProjectBuilder.NET_CONFIG_PATH_FLAG]
        # 先解密文件再进行其它处理
        preproc.decrypt(net_config_path)

        net_config_updater = NetworkConfigUpdater(net_config_path)
        env_mode = self.info[ProjectBuilder.ENV_MODE_FLAG]
        if env_mode in net_info:
            target_net_info = net_info[env_mode]
        else:
            target_net_info = net_info[ProjectBuilder.DEVELOP_FLAG]

        net_config_updater.update_info(target_net_info)

        # 如果是release版本，则进行加密处理 (应用内部对加密和非加密状态都能正常处理，所以在debug模式当前无须进行解决处理)
        mode_flag = self.info[ProjectBuilder.TYPE_FLAG]
        mode = apk_builder.FLAG_MODE_MAP[mode_flag.lower().strip()]
        if mode == apk_builder.RELEASE_MODE:
            if ProjectBuilder.FILE_ITEM_FLAG in self.info:
                file_items = self.info[ProjectBuilder.FILE_ITEM_FLAG]
                to_enc_list = []
                if isinstance(file_items, list):
                    to_enc_list.extend(file_items)
                else:
                    to_enc_list.append(file_items)

                for item in to_enc_list:
                    filepath = self.prj_path + os.sep + item
                    preproc.encrypt(filepath)

        version_code = self.info[ProjectBuilder.VER_CODE_FLAG]
        version_name = self.info[ProjectBuilder.VER_NAME_FLAG]
        ver_info_updater = apk_builder.ManifestVerInfoUpdater(self.manifest_path)
        ver_info_updater.update_version_config(version_code, version_name)

        config_updater = apk_builder.ManifestConfigInfoUpdater(self.manifest_path)
        config_updater.update_single_meta_data(ProjectBuilder.JPUSH_APPKEY_FLAG,
                                               self.info[ProjectBuilder.JPUSH_APPKEY_FLAG][
                                                   self.info[ProjectBuilder.ENV_MODE_FLAG]])

        env_config = self.info[ProjectBuilder.ENV_FLAG]
        env_path = self.prj_path + os.sep + env_config[ProjectBuilder.FILE_ITEM_FLAG]
        if os.path.exists(env_path):
            env_updater = EnvironmentUpdater(env_path)
            env_updater.update_config(env_mode)
        else:
            print('not exist {}!'.format(env_path))

    '''更新渠道相关信息，后续用于一次出多个渠道包'''

    def _update_chan_info(self, chan_id):
        self._update_chan_id(chan_id)
        self._update_chan_res(chan_id)

    def _update_chan_id(self, chan_id):
        '''更新apk渠道信信,编译模式等'''
        manifest_updater = ManifestInfoUpdater(self.manifest_path)
        manifest_updater.update_chan_info(chan_id)

    def _update_chan_res(self, chan_id):
        if self.res_path:
            res_src_path = os.path.join(self.res_path, chan_id)
            res_dst_path = self.prj_path
            if os.path.exists(res_src_path):
                self._update_res(res_src_path, res_dst_path)

    def _res_process_func(self, src_path, dst_path):
        if not filecmp.cmp(src_path, dst_path):
            file_util.replace_file(src_path, dst_path)

    def _update_res(self, src_path, dst_path):
        file_util.process_dir_src_to_dst(src_path, dst_path, self._res_process_func)

    def update_coverage_switch(self, env_mode):
        file_path = os.path.join(self.prj_path, 'build.gradle')
        content = file_util.read_file_content(file_path, 'utf-8')
        coverage_label = 'testCoverageEnabled'
        ptn_str = '({}\s*=\s*)\w+(\s+)'.format(coverage_label)
        ptn = re.compile(ptn_str, flags=(re.I | re.M))
        value = self.info[ProjectBuilder.COVERAGE_FLAG][ProjectBuilder.COMPILE_FLAG][env_mode]
        new_content = ptn.sub('\\1{}\\2'.format(value), content)
        if new_content != content:
            file_util.write_to_file(file_path, new_content, 'utf-8')
            print('update {} with value {}.'.format(coverage_label, value))
        else:
            print('{} remain as {}.'.format(coverage_label, value))

    def build(self, chan_id, mode=apk_builder.RELEASE_MODE):
        self._update_chan_info(chan_id)

        #         update_str = 'updated version info with chan_id "{0}".'.format(chan_id)
        #         print(update_str)

        print('building apk begin ...')

        # 获取apk名称
        apk_name = os.path.basename(self.prj_path)

        apk_out_path = self.prj_path + '/build/outputs/apk/'
        apk_path = '{}{}-{}.apk'.format(apk_out_path, apk_name, apk_builder.MODE_MAP[mode])
        apk_path = os.sep.join(re.split('[\\\/]+', apk_path))

        # 先把现有的apk文件直接删除
        if os.path.exists(apk_path) and os.path.isfile(apk_path):
            os.remove(apk_path)

        apk_builder.make_apk(self.prj_path, mode)

        #         mode_flag = apk_builder.MODE_MAP[mode]
        #         src_file = self.prj_path + os.sep + 'bin' + os.sep + apk_name + '-' + mode_flag + '.apk'
        src_file = apk_path

        if os.path.exists(src_file):
            apk_items = apk_util.get_apk_info(src_file)

            if apk_items['versionName'] != self.info[ProjectBuilder.VER_NAME_FLAG]:
                info = 'set version name is {}, but actual is {}!'.format(self.info[ProjectBuilder.VER_NAME_FLAG],
                                                                          apk_items['versionName'])
                raise Exception(info)

            if apk_items['versionCode'] != self.info[ProjectBuilder.VER_CODE_FLAG]:
                info = 'set version code is {}, but actual is {}!'.format(self.info[ProjectBuilder.VER_CODE_FLAG],
                                                                          apk_items['versionCode'])
                raise Exception(info)

            dst_file = self.info[ProjectBuilder.OUTPUT_DIRECTORY_FLAG] + os.sep + self.info[
                ProjectBuilder.OUTPUT_NAME_FLAG]
            file_util.replace_file(src_file, dst_file)

            # 拷贝编译生成的class文件，便于服务器生成代码覆盖率文件
            if ProjectBuilder.BUILD_CLASS_FLAG in self.info and len(self.info[ProjectBuilder.BUILD_CLASS_FLAG]) >= 2:
                src_class_path = self.prj_path + os.sep + self.info[ProjectBuilder.BUILD_CLASS_FLAG][
                    ProjectBuilder.SRC_PATH_FLAG]
                src_class_path = file_util.normalpath(src_class_path)

                dst_class_relative_path = self.info[ProjectBuilder.BUILD_CLASS_FLAG][ProjectBuilder.DST_PATH_FLAG]
                dst_class_zip_path = self.info[ProjectBuilder.OUTPUT_DIRECTORY_FLAG] + os.sep + 'classes.zip'

                #                 dst_class_path = self.info[ProjectBuilder.OUTPUT_DIRECTORY_FLAG] + os.sep + dst_class_relative_path
                #                 dst_class_path = file_util.normalize_path(dst_class_path)

                #                 if os.path.isdir(dst_class_path):
                #                     shutil.rmtree(dst_class_path)

                if os.path.isdir(src_class_path):
                    #                     shutil.copytree(src_class_path, dst_class_path)
                    rev_index = -len(dst_class_relative_path)
                    zip_src_root = src_class_path[:rev_index]
                    zip_util.zip_dir(src_class_path, dst_class_zip_path, zip_src_root)
                    print('success zip {} to {}.'.format(dst_class_relative_path, dst_class_zip_path))

            print('built the apk {}.'.format(dst_file))
        else:
            print('build {} failed!'.format(apk_name))

    def build_all(self):
        for item in self.chan_map:
            self.build(item)

        # 恢复到 svn 库上默认渠道状态
        self._update_chan_info(ProjectBuilder.DEFAULT_CHAN)


class ChanInfoParser:
    CONFIG_FLAG = "config"
    ITEM_FLAG = 'item'
    NAME_FLAG = 'name'

    def __init__(self, config_path):
        self.config_path = config_path
        self.result = {}

    def parse(self):
        doc = xmltodict.parse(file_util.read_file_content(self.config_path))
        root = doc[ChanInfoParser.CONFIG_FLAG]

        items = root[ChanInfoParser.ITEM_FLAG]

        for item in items:
            self.result[item[ChanInfoParser.NAME_FLAG]] = None

    def get_chan_map(self):
        return self.result


# 对 AndroidManifest.xml 文件内容进行更新
class ManifestInfoUpdater:
    def __init__(self, src_path):
        self.src_path = src_path
        self.src_data = file_util.read_file_content(self.src_path)
        self.modify_flag = False

    def update_chan_info(self, chan_str):
        self._update_chan_config(chan_str)
        if self.modify_flag:
            file_util.write_to_file(self.src_path, self.src_data, 'utf-8')

    def _update_chan_config(self, chan_str):
        # example <meta-data android:name="APP_CHANNEL" android:value="qh360"/>
        pattern = '^(\s*<\s*meta\-data\s+android\s*\:\s*name\s*=\s*"APP_CHANNEL"\s+android\s*\:\s*value\s*=\s*")(\w*)("\s*/>)'
        ptn = re.compile(pattern, flags=(re.I | re.M))

        modify_flag = False
        new_str = None
        match = ptn.search(self.src_data)
        if match:
            ori_chan_str = match.group(2)
            if chan_str != ori_chan_str:
                modify_flag = True
                new_str = match.group(1) + chan_str + match.group(3)

            self.modify_flag = modify_flag
            if modify_flag:
                self.src_data = ptn.sub(new_str, self.src_data)
                print('update chan_str with ' + chan_str + ' success.')
            else:
                print('chan_str remain as ' + chan_str + '.')
        else:
            print('update chan_str with ' + chan_str + ' failed!')


'''使用特定工具对文件进行加解密处理'''


class FileEncryptDecrypt:
    _SUFFIX = '_temp_abchxyz'

    def __init__(self, bin_path):
        self.bin_path = bin_path

    def encrypt(self, filepath):
        src_path = filepath
        dst_path = filepath + FileEncryptDecrypt._SUFFIX
        self._encrypt(src_path, dst_path)
        os.remove(src_path)
        os.rename(dst_path, src_path)

    def decrypt(self, filepath):
        src_path = filepath
        dst_path = filepath + FileEncryptDecrypt._SUFFIX
        self._decrypt(src_path, dst_path)
        os.remove(src_path)
        os.rename(dst_path, src_path)

    def _encrypt(self, src_path, dst_path):
        args = []
        args.append(self.bin_path)
        args.append(src_path)
        args.append(dst_path)
        subprocess.check_call(args)

    def _decrypt(self, src_path, dst_path):
        args = []
        args.append(self.bin_path)
        args.append('-d')
        args.append(src_path)
        args.append(dst_path)
        subprocess.check_call(args)


# 对网络配置进行更新
class NetworkConfigUpdater:
    HOST_FLAG = 'host'
    PORT_FLAG = 'port'
    SSLPORT_FLAG = 'sslport'

    def __init__(self, src_path):
        self.src_path = src_path
        self.src_data = file_util.read_file_content(self.src_path)
        self.modify_flag = False

    def update_info(self, target_info):
        if target_info:
            self._update_config(target_info)

        if self.modify_flag:
            file_util.write_to_file(self.src_path, self.src_data, 'utf-8')

    '''使用正则表达式的方式实现，便于后续扩展'''

    def _update_config_with_re(self, mode):
        # example: "url": "http://120.197.113.2:8181",
        pattern = '^(\s*"url"\:\s+"http\://(?:\d+\.){3}\d+\:)\d+'
        dst_port = NetworkConfigUpdater.MODE_MAP[mode]
        ptn = re.compile(pattern, flags=(re.I | re.M))
        re_sep = re.escape('#!#!#')
        re_rep_unit = re_sep + re.escape(dst_port)

        modify_flag = False
        print(self.src_data)
        new_data = ptn.sub('\\1' + re_rep_unit, self.src_data)
        if new_data != self.src_data:
            modify_flag = True
            print('-' * 80)
            print(new_data)
            self.src_data = new_data.replace(re_sep, '')
            print('-' * 80)
            print(self.src_data)

        if modify_flag:
            self.modify_flag = True
            print('update network port with ' + dst_port + ' success.')
        else:
            print('update network port with ' + dst_port + ' failed!')

    '''使用直接替换的方式实现'''

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


class SourceUpdater:
    def __init__(self, prj_root):
        # 获取当前所有子目录
        self.prj_root = prj_root
        self.sub_dir_list = file_util.get_child_dirs(self.prj_root)

    '''执行更新代码操作'''

    def update(self):
        self.svn_statuses = svn.get_statuses(self.sub_dir_list)

        for item in self.svn_statuses:
            if self.svn_statuses[item]:
                self._update(item)

    def _update(self, _dir):
        # 先撤消更改，再更新代码
        svn.revert(_dir)
        svn.update(_dir)


'''代码配置解析器，获取代码svn配置信息，便于从配置库拉取代码'''


class SourceConfigParser:
    CONFIG_FLAG = 'config'
    NAME_FLAG = 'name'
    VALUE_FLAG = 'value'
    TYPE_FLAG = 'type'
    BASE_URL_FLAG = 'base_url'
    URL_FLAG = 'url'
    PRJ_FLAG = 'prj'
    RES_FLAG = 'res'

    _BASE_FLAG = 'base'
    _RELATIVE_FLAG = 'relative'
    _RELATIVE_URL_FLAG = 'relative_url'

    def __init__(self, config_path):
        self.config_path = config_path

    def parse(self):
        doc = xmltodict.parse(file_util.read_file_content(self.config_path))
        root = doc[SourceConfigParser.CONFIG_FLAG]

        base_url_items = root[SourceConfigParser.BASE_URL_FLAG][SourceConfigParser._BASE_FLAG]

        # 获取基址
        base_urls = {}
        for item in base_url_items:
            base_urls[item[SourceConfigParser.NAME_FLAG]] = item[SourceConfigParser.VALUE_FLAG]
        self.base_urls = base_urls

        # 获取相对地址
        relative_url_items = root[SourceConfigParser._RELATIVE_URL_FLAG][SourceConfigParser._RELATIVE_FLAG]
        url_info = {}
        for item in relative_url_items:
            map_info = {}
            map_info[SourceConfigParser.URL_FLAG] = self.base_urls[item[SourceConfigParser._BASE_FLAG]] + '/' + item[
                SourceConfigParser.NAME_FLAG]
            map_info[SourceConfigParser.TYPE_FLAG] = item[SourceConfigParser.TYPE_FLAG]

            url_info[item[SourceConfigParser.NAME_FLAG]] = map_info

        self.url_info = url_info

    def get_source_url_info(self):
        return self.url_info


def get_svn_url_info(config_file):
    parser = SourceConfigParser(config_file)
    parser.parse()
    return parser.get_source_url_info()


'''先从svn配置库拉取所有代码'''


def get_code(prj_root, static_config_path, code_svn_path, revision=None):
    build_file_name = 'local.properties'
    local_build_file = static_config_path + os.sep + build_file_name

    svn_url_info = get_svn_url_info(code_svn_path)
    for item in svn_url_info:
        path = prj_root + os.sep + item
        if not os.path.exists(path):
            os.makedirs(path)
        svn.checkout(svn_url_info[item][SourceConfigParser.URL_FLAG], path, revision)

        if SourceConfigParser.PRJ_FLAG == svn_url_info[item][SourceConfigParser.TYPE_FLAG]:
            file_util.replace_file(local_build_file, path + os.sep + build_file_name)


'''先从svn配置库拉取所有代码'''


def get_prj_svn_ver(prj_root, code_svn_path):
    svn_url_info = get_svn_url_info(code_svn_path)
    max_svn = 0
    for item in svn_url_info:
        path = prj_root + os.sep + item
        if os.path.exists(path) and os.path.isdir(path):
            if SourceConfigParser.PRJ_FLAG == svn_url_info[item][SourceConfigParser.TYPE_FLAG]:
                svn_ver = svn.get_revision(path)
                if svn_ver > max_svn:
                    max_svn = svn_ver

    return max_svn


def checkout_or_update(prj_root, static_config_path, code_svn_path, revision=None):
    # 先获取目录列表，然后对单个目录进行处理
    if not os.path.exists(prj_root) or not os.path.isdir(prj_root):
        get_code(prj_root, static_config_path, code_svn_path, revision)
    else:
        svn_url_info = get_svn_url_info(code_svn_path)
        #         pprint.pprint(svn_url_info)

        build_file_name = 'local.properties'
        local_build_file = static_config_path + os.sep + build_file_name

        child_dirs = []
        for item in svn_url_info:
            child_dir = prj_root + os.sep + item
            child_dirs.append(child_dir)

            if not os.path.exists(child_dir) or not os.path.isdir(child_dir):
                os.makedirs(child_dir)

                svn.checkout(svn_url_info[item][SourceConfigParser.URL_FLAG], child_dir, revision)
            else:
                child_svn_status = svn.status(child_dir)
                if child_svn_status:
                    svn.revert(child_dir)
                    svn.update(child_dir, revision)
                else:
                    svn.checkout(item, child_dir, revision)

            if SourceConfigParser.PRJ_FLAG == svn_url_info[item][SourceConfigParser.TYPE_FLAG]:
                file_util.replace_file(local_build_file, child_dir + os.sep + build_file_name)


def checkout_or_update_single_item(prj_root, code_svn_url, revision=None):
    path = prj_root

    # 先获取目录列表，然后对单个目录进行处理
    if not os.path.isdir(path):
        os.makedirs(path)
        svn.checkout(code_svn_url, path, revision)
    else:
        svn_status = svn.status(path)
        if svn_status:
            svn.revert(path)
            svn.update(path, revision)
        else:
            svn.checkout(code_svn_url, path, revision)


# 更新主工程中的gradle编译配置文件
def update_gradle_setting(prj_path, src_path):
    setting_name = 'settings.gradle'
    local_setting_file = prj_path + os.sep + setting_name

    if os.path.exists(src_path) and os.path.isfile(src_path):
        if os.path.exists(local_setting_file):
            if not filecmp.cmp(src_path, local_setting_file, shallow=False):
                file_util.replace_file(src_path, local_setting_file)
        else:
            file_util.replace_file(src_path, local_setting_file)
    else:
        raise Exception('not exists ' + src_path)


class BuildConfigParser:
    ROOT_FLAG = 'config'
    WORKSPACE_FLAG = 'workspace'
    PRJ_PATH_FLAG = 'prj_path'
    MAIN_FLAG = 'main'
    CHANNEL_INFO_FLAG = 'channel_info'
    TARGET_PATH_FLAG = 'target_path'

    STATIC_FLAG = 'static'
    CODE_URL_FLAG = 'code_url'

    NETWORK_FLAG = 'network'
    RELATIVE_PATH_FLAG = 'relative_path'
    HOST_FLAG = 'host'
    PORT_FLAG = 'port'
    SSLPORT_FLAG = 'sslport'

    JPUSH_APPKEY_FLAG = 'jpush_appkey'
    ENCRYPT_FLAG = 'encrypt'
    BIN_NAME_FLAG = 'bin_name'
    FILE_ITEM_FLAG = 'file_item'

    PROTECT_FLAG = 'protect'
    IS_NEED_FLAG = 'is_need'

    SIGNER_FLAG = 'signer'

    BUILD_CLASS_FLAG = 'build_class'

    COVERAGE_FLAG = 'coverage'
    TINGYUN_APPKEY_FLAG = 'tingyun_appkey'

    ENV_FLAG = 'env'
    MAP_FLAG = 'map'
    DEV_FLAG = 'dev'
    TEST_FLAG = 'test'
    PRE_FLAG = 'pre'
    PRO_FLAG = 'pro'
    TARGET_FLAG = 'target'
    BUILD_INFO_TEMPLET_FLAG = 'build_info_templet'

    def __init__(self, config_path):
        self.config_path = config_path

    def parse(self):
        doc = xmltodict.parse(file_util.read_file_content(self.config_path))
        self.data = doc[BuildConfigParser.ROOT_FLAG]

    def get_config(self):
        return self.data


# 编译管理，负责整体调度
class BuildManager:
    # 安装包输出名称匹配正则表达式："3.1.0beta_p_01-314-20170515.apk"
    #     __APK_OUTPUT_PATH_INFORMAl_PATTERN = '([\d\.]+)beta_(\w+_\d+)-(\d+)-(\d+)\.apk'
    #     __APK_OUTPUT_PATH_FORMAl_PATTERN = '([\d\.]+)-(\d+)-(\d+)\.apk'

    __APK_OUTPUT_PATH_PATTERN = '^([\d\.]+(?:(?:beta_\w+_\d+)|(?:_\w+))?)-(\d+)-(\d+)\.apk$'

    def __init__(self, args):
        # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)
        #         pprint.pprint(vars(self))

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

        # project目录
        ori_project_path = self.work_path + os.sep + self.ori_build_config[BuildConfigParser.WORKSPACE_FLAG][
            BuildConfigParser.PRJ_PATH_FLAG]
        self.project_path = file_util.normalpath(ori_project_path)

    def _get_pro_build_config(self):
        # 指定项目地址
        params = {}

        bin_name = self.ori_build_config[BuildConfigParser.ENCRYPT_FLAG][BuildConfigParser.BIN_NAME_FLAG]
        enc_bin_path = self.work_path + os.sep + bin_name
        enc_bin_path = file_util.normalpath(enc_bin_path)
        params[ProjectBuilder.ENC_BIN_PATH_FLAG] = enc_bin_path

        net_config_path = self.project_path + os.sep + self.ori_build_config[BuildConfigParser.NETWORK_FLAG][
            BuildConfigParser.RELATIVE_PATH_FLAG]
        net_config_path = file_util.normalpath(net_config_path)
        params[ProjectBuilder.NET_CONFIG_PATH_FLAG] = net_config_path

        params[ProjectBuilder.NET_INFO_FLAG] = self.ori_build_config[BuildConfigParser.NETWORK_FLAG]
        params[ProjectBuilder.ENV_MODE_FLAG] = \
        self.ori_build_config[BuildConfigParser.ENV_FLAG][BuildConfigParser.MAP_FLAG][self.ver_env]

        params[ProjectBuilder.JPUSH_APPKEY_FLAG] = self.ori_build_config[BuildConfigParser.JPUSH_APPKEY_FLAG]

        params[ProjectBuilder.PROTECT_FLAG] = self.ori_build_config[BuildConfigParser.PROTECT_FLAG]
        is_need_infos = params[ProjectBuilder.PROTECT_FLAG][ProjectBuilder.IS_NEED_FLAG]
        for k in is_need_infos:
            is_need_infos[k] = str_util.get_bool(is_need_infos[k])

        params[ProjectBuilder.SIGNER_FLAG] = self.ori_build_config[BuildConfigParser.SIGNER_FLAG]

        # 将时间格式化
        curr_time = time.localtime()
        time_str = time.strftime('%Y%m%d_%H%M%S', curr_time)

        output_directory = self.work_path + os.sep + self.ori_build_config[BuildConfigParser.WORKSPACE_FLAG][
            BuildConfigParser.TARGET_PATH_FLAG]
        output_directory = file_util.normalpath(output_directory)
        output_directory = output_directory + os.sep + self.ver_env + os.sep + time_str
        params[ProjectBuilder.OUTPUT_DIRECTORY_FLAG] = output_directory

        self.output_directory = params[ProjectBuilder.OUTPUT_DIRECTORY_FLAG]

        params[ProjectBuilder.VER_NAME_FLAG] = self.ver_name
        params[ProjectBuilder.VER_CODE_FLAG] = self.ver_code
        params[ProjectBuilder.ENV_FLAG] = self.ori_build_config[BuildConfigParser.ENV_FLAG]

        # 指定输出归档文件地址
        date_str = time.strftime('%Y%m%d', curr_time)

        if self.is_debug:
            mode_flag = apk_builder.DEBUG_FLAG

            # 指定输出apk名称
            params[ProjectBuilder.OUTPUT_NAME_FLAG] = "{}-{}-{}-{}.apk".format(self.ver_name, self.ver_code, mode_flag,
                                                                               date_str)
        else:
            mode_flag = apk_builder.RELEASE_FLAG

            # 指定输出apk名称
            params[ProjectBuilder.OUTPUT_NAME_FLAG] = "{}-{}-{}.apk".format(self.ver_name, self.ver_code, date_str)

        params[ProjectBuilder.TYPE_FLAG] = mode_flag
        self.apk_output_path = params[ProjectBuilder.OUTPUT_DIRECTORY_FLAG] + os.sep + params[
            ProjectBuilder.OUTPUT_NAME_FLAG]

        pprint.pprint(params)

        return params

    def build_app(self, prj_path, chan_path, res_path, info, chan_id=None, mode=apk_builder.RELEASE_MODE):
        if chan_path:
            parser = ChanInfoParser(chan_path)
            parser.parse()
            chan_map = parser.get_chan_map()
        else:
            chan_map = None

        prj_builder = ProjectBuilder(prj_path, chan_map, res_path, info)
        prj_builder.update_info()

        if chan_id:
            prj_builder.build(chan_id, mode)
            pass
        else:
            if chan_map:
                prj_builder.build_all()
                pass
            else:
                print('the chan_map is invalid!')

    def process(self):
        git_flag = 'use_git'
        if not hasattr(self, git_flag):
            self.use_git = False

        code_url = self.ori_build_config[BuildConfigParser.ROOT_FLAG][BuildConfigParser.CODE_URL_FLAG]

        static_config_path = self.work_path + os.sep + self.ori_build_config[BuildConfigParser.ROOT_FLAG][
            BuildConfigParser.STATIC_FLAG]
        static_config_path = file_util.normalpath(static_config_path)

        main_prj_name = self.ori_build_config[BuildConfigParser.WORKSPACE_FLAG][BuildConfigParser.MAIN_FLAG]

        if self.use_git:
            self.project_code_path = os.path.join(self.project_path, self.branch)
        else:
            self.project_code_path = self.project_path

        # 进行代码更新操作
        if self.to_update:
            if self.use_git:
                git.checkout_or_update(self.project_code_path, code_url, self.code_ver, self.branch)
            else:
                # 根据参数配置svn用户名和密码
                username_flag = 'svn_user'
                password_flag = 'svn_pwd'
                if hasattr(self, username_flag) and hasattr(self, password_flag):
                    #                 print('{}: {}'.format(username_flag, self.svn_user))
                    #                 print('{}: {}'.format(password_flag, self.svn_pwd))
                    svn.set_user_info(getattr(self, username_flag), getattr(self, password_flag))

                # 先checkout svn库上代码，再更新和本地相关的配置文件
                checkout_or_update_single_item(self.project_code_path, code_url, revision=self.code_ver)

                # 更新gradle编译配置配置，新框架不再需要该步骤(20161110 17:39)
            #             gradle_setting_name = 'settings.gradle'
            #             gradle_setting_path = static_config_path + os.sep + gradle_setting_name
            #             update_gradle_setting(main_prj_path, gradle_setting_path)

        # 设置配置信息并获取当前代码版本号
        if self.use_git:
            self.prj_root = git.get_git_root(self.project_code_path)
            main_prj_path = os.path.join(self.prj_root, main_prj_name)
            self.code_ver = git.get_revision(self.prj_root)
        else:
            self.prj_root = self.project_code_path
            main_prj_path = os.path.join(self.project_code_path, main_prj_name)
            self.code_ver = svn.get_revision(self.project_code_path)
        print('current code version is ' + str(self.code_ver))

        if self.to_update:
            # 更新android sdk本地配置
            local_file_name = 'local.properties'
            local_build_file = os.path.join(static_config_path, local_file_name)
            target_build_file = os.path.join(self.prj_root, local_file_name)
            file_util.replace_file(local_build_file, target_build_file)

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
            self.pre_build()

            if self.is_debug:
                mode_flag = apk_builder.DEBUG_FLAG
            else:
                mode_flag = apk_builder.RELEASE_FLAG

            mode = apk_builder.FLAG_MODE_MAP[mode_flag]

            workspace_map = self.ori_build_config[BuildConfigParser.WORKSPACE_FLAG]
            if BuildConfigParser.CHANNEL_INFO_FLAG in workspace_map:
                res_path = self.work_path + os.sep + workspace_map[BuildConfigParser.CHANNEL_INFO_FLAG]
            else:
                res_path = None

            if hasattr(self, 'channel_file') and hasattr(self, 'channel'):
                if self.channel_file:
                    if not os.path.exists(self.channel_file):
                        print('not exist {}'.format(self.channel_file))
                        exit(1)

                    self.build_app(main_prj_path, self.channel_file, res_path, self.pro_build_config)
                else:
                    if self.channel:
                        chan_id = self.channel
                    else:
                        chan_id = ProjectBuilder.DEFAULT_CHAN

                    self.build_app(main_prj_path, None, res_path, self.pro_build_config, chan_id, mode)
            else:
                chan_id = ProjectBuilder.DEFAULT_CHAN
                self.build_app(main_prj_path, None, res_path, self.pro_build_config, chan_id, mode)

            if os.path.exists(self.apk_output_path) and os.path.isfile(self.apk_output_path):
                # 将编译信息写文件
                build_info_format = self.ori_build_config[BuildConfigParser.BUILD_INFO_TEMPLET_FLAG]
                build_info = build_info_format.format(ver_name=self.ver_name, code_ver=self.code_ver,
                                                      ver_code=self.ver_code)
                build_info_path = self.output_directory + os.sep + 'readme-{}-{}.txt'.format(self.ver_name,
                                                                                             self.ver_code)
                file_util.write_to_file(build_info_path, build_info, encoding='utf-8')

                target_name = os.path.basename(self.apk_output_path)
                to_upload_path = os.path.dirname(self.apk_output_path)
                source_name = os.path.basename(self.apk_output_path)

                # 有需要则先加固，再签名
                if ProjectBuilder.PROTECT_FLAG in self.pro_build_config and ProjectBuilder.SIGNER_FLAG in self.pro_build_config:
                    env_mode = self.pro_build_config[ProjectBuilder.ENV_MODE_FLAG]
                    if self.pro_build_config[ProjectBuilder.PROTECT_FLAG][ProjectBuilder.IS_NEED_FLAG][env_mode]:
                        ip = self.pro_build_config[ProjectBuilder.PROTECT_FLAG][ProjectBuilder.IP_FLAG]
                        user_name = self.pro_build_config[ProjectBuilder.PROTECT_FLAG][ProjectBuilder.USER_FLAG]
                        api_key = self.pro_build_config[ProjectBuilder.PROTECT_FLAG][ProjectBuilder.API_KEY_FLAG]
                        api_secret = self.pro_build_config[ProjectBuilder.PROTECT_FLAG][ProjectBuilder.API_SECRET_FLAG]
                        protected_path = protect_app.protect(ip, user_name, api_key, api_secret, self.apk_output_path)

                        if hasattr(self, 'to_align') and self.to_align:
                            aligned_path = file_util.get_middle_path(protected_path)
                            apk_util.zipalign(protected_path, aligned_path)
                            to_sign_path = aligned_path
                        else:
                            to_sign_path = protected_path

                        keystore = os.path.join(main_prj_path, self.pro_build_config[ProjectBuilder.SIGNER_FLAG][
                            ProjectBuilder.KEYSTORE_FLAG])
                        storepass = self.pro_build_config[ProjectBuilder.SIGNER_FLAG][ProjectBuilder.STOREPASS_FLAG]
                        storealias = self.pro_build_config[ProjectBuilder.SIGNER_FLAG][ProjectBuilder.STOREALIAS_FLAG]
                        signed_path = apk_util.get_default_signed_path(protected_path)
                        rtn = apk_util.sign_apk(keystore, storepass, storealias, to_sign_path, signed_path)
                        if rtn:
                            str_info = 'Protect {} and sign success.'.format(self.apk_output_path)
                            source_name = os.path.basename(signed_path)
                        else:
                            str_info = 'Protect {} and sign failed!'.format(self.apk_output_path)
                            raise Exception(str_info)

                        print(str_info)

                str_info = 'Build success, code version is {}.'.format(self.code_ver)
                print(str_info)

                # 进行编译好的版本提交操作
                if hasattr(self, 'to_upload') and self.to_upload:
                    result = re.match(BuildManager.__APK_OUTPUT_PATH_PATTERN, target_name)
                    if result:
                        ver_name_info = result.group(1)
                    else:
                        str_info = 'The output file name {} is invalid!'.format(target_name)
                        raise Exception(str_info)

                    #                     ftp_config_path = os.path.join(self.work_path, 'config')
                    ftp_config_path = self.work_path
                    print('ver_name_info:', ver_name_info)
                    print('target_name: ', target_name)
                    print('source_name:', source_name)

                    ftp_upload.upload_to_sftp(ftp_config_path, ver_name_info, self.ver_env, self.code_ver,
                                              to_upload_path, 'Android', target_name, source_name)
            else:
                str_info = 'Build failed, code version is {}.'.format(self.code_ver)
                print(str_info)

    def pre_build(self):
        pass


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
                        help='indicate updating to special version')
    parser.add_argument('-d', dest='is_debug', action='store_true', default=False,
                        help='indicate to build debug version')

    parser.add_argument('--vername', metavar='ver_name', dest='ver_name', help='version name')
    parser.add_argument('--vercode', metavar='ver_code', dest='ver_code', help='version code')
    parser.add_argument('--verenv', metavar='ver_env', dest='ver_env', type=str, choices=['dev', 'test', 'pre', 'pro'],
                        help='dev: develop environment; test: test environment; pre: pre-release environment; pro: production environment;')

    src_group = parser.add_mutually_exclusive_group()
    src_group.add_argument('-s', dest='channel', default=None, help='indicate the channel to build')
    src_group.add_argument('-m', dest='channel_file', default=None,
                           help='indicate the channel file to build multi-file')

    #     parser.print_help()

    return parser.parse_args(src_args)
