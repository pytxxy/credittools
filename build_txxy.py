# -*- coding:UTF-8 -*-
# 20161109 21:30 根据android 新框架进行适当地调整 
import os
import sys
import re
import time
import filecmp
import creditutils.apk_builder_util as apk_builder
import creditutils.file_util as myfile
import creditutils.apk_util as apk
import pprint
import creditutils.svn_util as svn
import subprocess
# import traceback
import xmltodict
import creditutils.str_util as str_utils
import argparse
 
# 对整个工程内相关文件进行替换操作
class ProjectBuilder:
    DEFAULT_CHAN = 'pycredit'
    
    ENC_BIN_PATH_FLAG = 'enc_bin_path'
    NET_CONFIG_PATH_FLAG = 'net_config_path'
    NET_INFO_FLAG = 'net_info'
    DEVELOP_FLAG = 'develop'
    HOST_FLAG = 'host'
    PORT_FLAG = 'port'
    SSLPORT_FLAG = 'sslport'
    
    JPUSH_APPKEY_FLAG = 'jpush_appkey'
    EASEMOB_APPKEY_FLAG = 'easemob_appkey'
    ENV_FLAG = 'env'
    ENV_MODE_FLAG = 'env_mode'
    TYPE_FLAG = 'type'
    ENCRYPT_ITEMS_FLAG = 'encrypt_items'
    FILE_ITEM_FLAG = 'file_item'
    
    OUTPUT_DIRECTORY_FLAG = 'output_directory'
    OUTPUT_NAME_FLAG = 'output_name'
    VER_NAME_FLAG = 'ver_name'
    VER_CODE_FLAG = 'ver_code'
    
    def __init__(self, prj_path, chan_map, res_path, info):
        self.prj_path = prj_path
        self.chan_map = chan_map
        self.res_path = res_path
        self.info = info
        
        self.manifest_path = self.prj_path + os.sep + 'AndroidManifest.xml'
        
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
        config_updater.update_single_meta_data(ProjectBuilder.JPUSH_APPKEY_FLAG, self.info[ProjectBuilder.JPUSH_APPKEY_FLAG][self.info[ProjectBuilder.ENV_MODE_FLAG]])
        config_updater.update_single_meta_data(ProjectBuilder.EASEMOB_APPKEY_FLAG, self.info[ProjectBuilder.EASEMOB_APPKEY_FLAG][self.info[ProjectBuilder.ENV_MODE_FLAG]])
        
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
        res_src_path = self.res_path + os.sep + chan_id
        res_dst_path = self.prj_path
        if os.path.exists(res_src_path):
            self._update_res(res_src_path, res_dst_path)
    
    def _res_process_func(self, src_path, dst_path):
        if not filecmp.cmp(src_path, dst_path):
            myfile.replace_file(src_path, dst_path)
    
    def _update_res(self, src_path, dst_path):
        myfile.process_dir_src_to_dst(src_path, dst_path, self._res_process_func)
    
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
            apk_items = apk.get_apk_info(src_file)
            
            if apk_items['versionName'] != self.info[ProjectBuilder.VER_NAME_FLAG]:
                info = 'set version name is {}, but actual is {}!'.format(self.info[ProjectBuilder.VER_NAME_FLAG], apk_items['versionName'])
                raise Exception(info)
            
            if apk_items['versionCode'] != self.info[ProjectBuilder.VER_CODE_FLAG]:
                info = 'set version code is {}, but actual is {}!'.format(self.info[ProjectBuilder.VER_CODE_FLAG], apk_items['versionCode'])
                raise Exception(info)
            
            dst_file = self.info[ProjectBuilder.OUTPUT_DIRECTORY_FLAG] + os.sep + self.info[ProjectBuilder.OUTPUT_NAME_FLAG]
            myfile.replace_file(src_file, dst_file)
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
        doc = xmltodict.parse(myfile.read_file_content(self.config_path))
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
        self.src_data = myfile.read_file_content(self.src_path)
        self.modify_flag = False
    
    def update_chan_info(self, chan_str):
        self._update_chan_config(chan_str)
        if self.modify_flag:
            myfile.write_to_file(self.src_path, self.src_data, 'utf-8')
    
    def _update_chan_config(self, chan_str):
        #example <meta-data android:name="APP_CHANNEL" android:value="qh360"/>
        pattern = '^(\s*<\s*meta\-data\s+android\s*\:\s*name\s*=\s*"APP_CHANNEL"\s+android\s*\:\s*value\s*=\s*")(\w*)("\s*/>)'
        ptn = re.compile(pattern, flags=(re.I|re.M))
        
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
        
# 对 网络配置进行更新
class NetworkConfigUpdater:
    HOST_FLAG = 'host'
    PORT_FLAG = 'port'
    SSLPORT_FLAG = 'sslport'
    
    def __init__(self, src_path):
        self.src_path = src_path
        self.src_data = myfile.read_file_content(self.src_path)
        self.modify_flag = False
        
    def update_info(self, target_info):
        if target_info:
            self._update_config(target_info)
        
        if self.modify_flag:
            myfile.write_to_file(self.src_path, self.src_data, 'utf-8')
    
    '''使用正则表达式的方式实现，便于后续扩展'''
    def _update_config_with_re(self, mode):
        # example: "url": "http://120.197.113.2:8181",
        pattern = '^(\s*"url"\:\s+"http\://(?:\d+\.){3}\d+\:)\d+'
        dst_port = NetworkConfigUpdater.MODE_MAP[mode]
        ptn = re.compile(pattern, flags=(re.I|re.M))
        re_sep = re.escape('#!#!#')
        re_rep_unit = re_sep + re.escape(dst_port)
        
        modify_flag = False
        print(self.src_data)
        new_data = ptn.sub('\\1'+re_rep_unit, self.src_data)
        if new_data != self.src_data:
            modify_flag = True
            print('-'*80)
            print(new_data)
            self.src_data = new_data.replace(re_sep, '')
            print('-'*80)
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
            ptn = re.compile(ptn_str, flags=(re.I|re.M))
            re_sep = re.escape('#!#!#')
            re_rep_unit = re_sep + re.escape(target_info[key])
            new_data = ptn.sub('\\1'+re_rep_unit+'\\3', self.src_data)
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
        self.config_data = myfile.read_file_content(self.config_path)
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
            myfile.write_to_file(self.config_path, self.config_data, 'utf-8')

class SourceUpdater:
    def __init__(self, prj_root):
        # 获取当前所有子目录
        self.prj_root = prj_root
        self.sub_dir_list = myfile.get_child_dirs(self.prj_root)
    
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
    CONFIG_FLAG = "config"
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
        doc = xmltodict.parse(myfile.read_file_content(self.config_path))
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
            map_info[SourceConfigParser.URL_FLAG] = self.base_urls[item[SourceConfigParser._BASE_FLAG]] + '/' + item[SourceConfigParser.NAME_FLAG]
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
            myfile.replace_file(local_build_file, path + os.sep + build_file_name)

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
                myfile.replace_file(local_build_file, child_dir + os.sep + build_file_name)
                
def checkout_or_update_single_item(prj_root, static_config_path, code_svn_url, revision=None):
    path = prj_root
    
    # 先获取目录列表，然后对单个目录进行处理
    if not os.path.exists(path) or not os.path.isdir(path):
        os.makedirs(path)
        svn.checkout(code_svn_url, path, revision)
    else:
        svn_status = svn.status(path)
        if svn_status:
            svn.revert(path)
            svn.update(path, revision)
        else:
            svn.checkout(code_svn_url, path, revision)
                
    build_file_name = 'local.properties'
    local_build_file = static_config_path + os.sep + build_file_name
    target_build_file = path + os.sep + build_file_name
    myfile.replace_file(local_build_file, target_build_file)

# 更新主工程中的gradle编译配置文件
def update_gradle_setting(prj_path, src_path):
    setting_name = 'settings.gradle'
    local_setting_file = prj_path + os.sep + setting_name
    
    if os.path.exists(src_path) and os.path.isfile(src_path):
        if os.path.exists(local_setting_file):
            if not filecmp.cmp(src_path, local_setting_file, shallow=False):
                myfile.replace_file(src_path, local_setting_file)
        else:
            myfile.replace_file(src_path, local_setting_file)
    else:
        raise Exception('not exists ' + src_path)
 
def build_app(prj_path, chan_path, res_path, info, chan_id=None, mode=apk_builder.RELEASE_MODE):
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
     
class BuildConfigParser:
    ROOT_FLAG = 'config'
    WORKSPACE_FLAG = 'workspace'
    PRJ_PATH_FLAG = 'prj_path'
    MAIN_FLAG = 'main'
    CHANNEL_INFO_FLAG = 'channel_info'
    TARGET_PATH_FLAG = 'target_path'
    
    STATIC_FLAG = 'static'
    CODE_SVN_FLAG = 'code_svn'

    NETWORK_FLAG = 'network'
    RELATIVE_PATH_FLAG = 'relative_path'
    HOST_FLAG = 'host'
    PORT_FLAG = 'port'
    SSLPORT_FLAG = 'sslport'
    
    JPUSH_APPKEY_FLAG = 'jpush_appkey'
    EASEMOB_APPKEY_FLAG = 'easemob_appkey'
    ENCRYPT_FLAG = 'encrypt'
    BIN_NAME_FLAG = 'bin_name'
    FILE_ITEM_FLAG = 'file_item'
    
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
        doc = xmltodict.parse(myfile.read_file_content(self.config_path))
        self.data = doc[BuildConfigParser.ROOT_FLAG]
        
    def get_config(self):
        return self.data

class BuildManager:   
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
        ori_project_path = self.work_path + os.sep + self.ori_build_config[BuildConfigParser.WORKSPACE_FLAG][BuildConfigParser.PRJ_PATH_FLAG]
        self.project_path = myfile.normalpath(ori_project_path)
    
    def _get_pro_build_config(self):
        #指定项目地址
        params = {}

        bin_name = self.ori_build_config[BuildConfigParser.ENCRYPT_FLAG][BuildConfigParser.BIN_NAME_FLAG]
        enc_bin_path = self.work_path + os.sep + bin_name
        enc_bin_path = myfile.normalpath(enc_bin_path)
        params[ProjectBuilder.ENC_BIN_PATH_FLAG] = enc_bin_path
        
        net_config_path = self.project_path + os.sep + self.ori_build_config[BuildConfigParser.NETWORK_FLAG][BuildConfigParser.RELATIVE_PATH_FLAG]
        net_config_path = myfile.normalpath(net_config_path)
        params[ProjectBuilder.NET_CONFIG_PATH_FLAG] = net_config_path
        
        params[ProjectBuilder.NET_INFO_FLAG] = self.ori_build_config[BuildConfigParser.NETWORK_FLAG]
        params[ProjectBuilder.ENV_MODE_FLAG] = self.ori_build_config[BuildConfigParser.ENV_FLAG][BuildConfigParser.MAP_FLAG][self.ver_env]
        params[ProjectBuilder.NET_INFO_FLAG] = self.ori_build_config[BuildConfigParser.NETWORK_FLAG]
        
        params[ProjectBuilder.JPUSH_APPKEY_FLAG] = self.ori_build_config[BuildConfigParser.JPUSH_APPKEY_FLAG]
        params[ProjectBuilder.EASEMOB_APPKEY_FLAG] = self.ori_build_config[BuildConfigParser.EASEMOB_APPKEY_FLAG]
        
        # 将时间格式化
        curr_time = time.localtime()
        time_str = time.strftime('%Y%m%d_%H%M%S', curr_time)
        
        output_directory = self.work_path + os.sep + self.ori_build_config[BuildConfigParser.WORKSPACE_FLAG][BuildConfigParser.TARGET_PATH_FLAG]
        output_directory = myfile.normalpath(output_directory)
        output_directory = output_directory + os.sep + self.ver_env + os.sep + time_str
        params[ProjectBuilder.OUTPUT_DIRECTORY_FLAG] = output_directory
        
        self.output_directory = params[ProjectBuilder.OUTPUT_DIRECTORY_FLAG]
        
        params[ProjectBuilder.VER_NAME_FLAG] = self.ver_name
        params[ProjectBuilder.VER_CODE_FLAG] = self.ver_code
        params[ProjectBuilder.ENV_FLAG] = self.ori_build_config[BuildConfigParser.ENV_FLAG]
        
        #指定输出归档文件地址
        date_str = time.strftime('%Y%m%d', curr_time)
        
        if self.is_debug:
            mode_flag = apk_builder.DEBUG_FLAG
            
            #指定输出apk名称
            params[ProjectBuilder.OUTPUT_NAME_FLAG]="{}-{}-{}-{}.apk".format(self.ver_name, self.ver_code, mode_flag, date_str)
        else:
            mode_flag = apk_builder.RELEASE_FLAG
            
            #指定输出apk名称
            params[ProjectBuilder.OUTPUT_NAME_FLAG]="{}-{}-{}.apk".format(self.ver_name, self.ver_code, date_str)

        params[ProjectBuilder.TYPE_FLAG] = mode_flag
        self.apk_output_path = params[ProjectBuilder.OUTPUT_DIRECTORY_FLAG] + os.sep + params[ProjectBuilder.OUTPUT_NAME_FLAG]
        
        pprint.pprint(params)
        
        return params
    
    def process(self):
        code_svn_url = self.ori_build_config[BuildConfigParser.ROOT_FLAG][BuildConfigParser.CODE_SVN_FLAG]
        
        static_config_path = self.work_path + os.sep + self.ori_build_config[BuildConfigParser.ROOT_FLAG][BuildConfigParser.STATIC_FLAG]
        static_config_path = myfile.normalpath(static_config_path)
        
        main_prj_name = self.ori_build_config[BuildConfigParser.WORKSPACE_FLAG][BuildConfigParser.MAIN_FLAG]
        main_prj_path = self.project_path + os.sep + main_prj_name
        
        # 进行代码更新操作
        if self.to_update:
            # 先checkout svn库上代码，再更新和本地相关的配置文件
            checkout_or_update_single_item(self.project_path, static_config_path, code_svn_url, revision=self.svn_ver)
            
            # 更新gradle编译配置配置，新框架不再需要该步骤(20161110 17:39)
#             gradle_setting_name = 'settings.gradle'
#             gradle_setting_path = static_config_path + os.sep + gradle_setting_name
#             update_gradle_setting(main_prj_path, gradle_setting_path)
            
        # 获取当前svn版本号    
        self.svn_ver_code = svn.get_revision(self.project_path)
        print('svn version code is ' + str(self.svn_ver_code))
    
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
            res_path = self.work_path + os.sep + self.ori_build_config[BuildConfigParser.WORKSPACE_FLAG][BuildConfigParser.CHANNEL_INFO_FLAG]
        
            if self.channel_file:
                if not os.path.exists(self.channel_file):
                    print('not exist {}'.format(self.channel_file))
                    exit(1)
                    
                build_app(main_prj_path, self.channel_file, res_path, self.pro_build_config)
            else:
                if self.channel:
                    chan_id = self.channel
                else:
                    chan_id = ProjectBuilder.DEFAULT_CHAN
                    
                build_app(main_prj_path, None, res_path, self.pro_build_config, chan_id, mode)
            
            if os.path.exists(self.apk_output_path) and os.path.isfile(self.apk_output_path):
                # 将编译信息写文件
                build_info_format = self.ori_build_config[BuildConfigParser.BUILD_INFO_TEMPLET_FLAG]
                build_info = build_info_format.format(ver_name=self.ver_name, svn_ver=self.svn_ver_code, ver_code=self.ver_code)
                build_info_path = self.output_directory + os.sep + 'readme-{}-{}.txt'.format(self.ver_name, self.ver_code)
                myfile.write_to_file(build_info_path, build_info, encoding='utf-8')
                
                str_info = 'Build success, svn code is {}.'.format(self.svn_ver_code)
                print(str_info)
            else:
                str_info = 'Build failed, svn code is {}.'.format(self.svn_ver_code)
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
    
    parser.add_argument('-c', metavar='base_config', dest='base_config', help='base configure file, path relative to work path')
    parser.add_argument('-u', dest='to_update', action='store_true', default=False, help='indicate to get or update code firstly')
    parser.add_argument('-b', dest='to_build', action='store_true', default=False, help='indicate to build')
    parser.add_argument('-v', metavar='svn_ver', dest='svn_ver', action='store', default=None, help='indicate updating to special version')
    parser.add_argument('-d', dest='is_debug', action='store_true', default=False, help='indicate to build debug version')
    
    parser.add_argument('--vername', metavar='ver_name', dest='ver_name', help='version name')
    parser.add_argument('--vercode', metavar='ver_code', dest='ver_code', help='version code')
    parser.add_argument('--verenv', metavar='ver_env', dest='ver_env', type=str, choices=['dev', 'test', 'pre', 'pro'], help='dev: develop environment; test: test environment; pre: pre-release environment; pro: production environment;')
    
    src_group = parser.add_mutually_exclusive_group()
    src_group.add_argument('-s', dest='channel', default=None, help='indicate the channel to build')
    src_group.add_argument('-m', dest='channel_file', default=None, help='indicate the channel file to build multi-file')
    
#     parser.print_help()
    
    return parser.parse_args(src_args)
 
if __name__=='__main__':
    begin = time.time()
    #test_args = '-b -s huawei D:/version_build/pytxxy/config/dynamic/update_config.xml'.split()
    test_args = None
    args = get_args(test_args)
    main(args)
     
    end = time.time()
    time_info = str_utils.get_time_info(begin, end)
     
    #输出总用时
    print('===Finished. Total time: {}==='.format(time_info))
    