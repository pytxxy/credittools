# -*- coding:UTF-8 -*-
# 20161109 21:30 根据android 新框架进行适当地调整 
import os
import time
import creditutils.apk_builder_util as apk_builder
import creditutils.file_util as myfile
import pprint
# import traceback
import creditutils.str_util as str_utils
import creditutils.trivial_util as utility
import argparse
import creditutils.build_base_android as build_base


# 对整个工程内相关文件进行替换操作
class ProjectBuilder(build_base.ProjectBuilder):
    EASEMOB_APPKEY_FLAG = 'easemob_appkey'
    MOXIE_APPKEY_FLAG = 'moxie_appkey'

    MANIFEST_REL_PATH_FLAG = 'manifest_rel_path'

    CA_AUTH_CODE_FLAG = 'ca_auth_code'
    CODE_META_DATA_FLAG = 'code_meta_data'
    ITEM_FLAG = 'item'
    NAME_FLAG = 'name'
    CODE_FLAG = 'code'

    CODE_VER_FLAG = 'code_ver'
    CODE_REVISION_FLAG = 'CODE_REVISION'
    DEMO_LABEL_FLAG = 'demo_label'
    THIRD_PARTY_TEST_FLAG = 'THIRD_PARTY_TEST'

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
        preproc = build_base.FileEncryptDecrypt(enc_bin_path)

        # 更新网络配置
        net_info = self.info[ProjectBuilder.NET_INFO_FLAG]
        net_config_path = self.info[ProjectBuilder.NET_CONFIG_PATH_FLAG]
        # 先解密文件再进行其它处理
        preproc.decrypt(net_config_path)

        net_config_updater = build_base.NetworkConfigUpdater(net_config_path)
        env_net = self.info[ProjectBuilder.ENV_NET_FLAG]
        if env_net in net_info:
            target_net_info = net_info[env_net]
        else:
            target_net_info = net_info[ProjectBuilder.DEV_FLAG]

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
        env_mode = self.info[ProjectBuilder.ENV_MODE_FLAG]

        # 更新代码配置库信息
        config_updater.update_single_meta_data(ProjectBuilder.CODE_REVISION_FLAG,
                                               self.info[ProjectBuilder.CODE_VER_FLAG])
        # 更新demo标识
        config_updater.update_single_meta_data(ProjectBuilder.THIRD_PARTY_TEST_FLAG,
                                               self.info[ProjectBuilder.DEMO_LABEL_FLAG].lower())
        # 更新听云license 文件
        config_updater.update_single_meta_data(ProjectBuilder.MONITOR_APPKEY_FLAG,
                                               self.info[ProjectBuilder.TINGYUN_APPKEY_FLAG][env_mode])

        # 分别更新极光推送授权码、环信授权码以及魔蝎授权码
        meta_map = {
            ProjectBuilder.JPUSH_APPKEY_FLAG: ProjectBuilder.JPUSH_APPKEY_FLAG,
            ProjectBuilder.EASEMOB_APPKEY_FLAG: ProjectBuilder.EASEMOB_APPKEY_FLAG,
            ProjectBuilder.MOXIE_APPKEY_FLAG: ProjectBuilder.MOXIE_APPKEY_FLAG
        }
        self._update_multi_meta_data(meta_map)

        # 更新代码覆盖率统计开关
        self.update_coverage_switch(env_mode)

        # 如果设定了app名称，则更新App应用名称及对应的CA签章授权码
        app_name = self.info[ProjectBuilder.APP_NAME_FLAG]
        if app_name:
            string_path = self.prj_path + os.sep + myfile.normalpath(
                self.info[ProjectBuilder.CA_AUTH_CODE_FLAG][ProjectBuilder.STR_REL_PATH_FLAG])
            app_name_flag = self.info[ProjectBuilder.CA_AUTH_CODE_FLAG][ProjectBuilder.STR_ID_FLAG]
            string_updater = apk_builder.StringItemUpdater(string_path)
            ori_app_name = string_updater.get_single_item_value(app_name_flag)
            if app_name != ori_app_name:
                string_updater.update_single_item(app_name_flag, app_name)
                code_info_array = self.info[ProjectBuilder.CA_AUTH_CODE_FLAG][ProjectBuilder.ITEM_FLAG]
                code = None
                for item in code_info_array:
                    if app_name == item[ProjectBuilder.NAME_FLAG]:
                        code = item[ProjectBuilder.CODE_FLAG]
                        break
                if code:
                    code_meta_data = self.info[ProjectBuilder.CA_AUTH_CODE_FLAG][ProjectBuilder.CODE_META_DATA_FLAG]
                    config_updater.update_single_meta_data(code_meta_data, code)
                else:
                    raise Exception('Not found corresponding code!')
            else:
                info = 'app_name remain as "{}".'.format(app_name)
                print(info)

        env_config = self.info[ProjectBuilder.ENV_FLAG]
        prj_root = self.info[ProjectBuilder.PRJ_ROOT_FLAG]
        env_path = prj_root + os.sep + env_config[ProjectBuilder.FILE_ITEM_FLAG]
        env_path = myfile.normalpath(env_path)
        if os.path.exists(env_path):
            env_updater = build_base.EnvironmentUpdater(env_path)
            env_updater.update_config(env_mode)
        else:
            print('not exist {}!'.format(env_path))

    def _update_single_meta_data(self, rel_path, name, value):
        prj_root = self.info[ProjectBuilder.PRJ_ROOT_FLAG]
        manifest_path = prj_root + os.sep + rel_path
        manifest_path = myfile.normalpath(manifest_path)
        updater = apk_builder.ManifestConfigInfoUpdater(manifest_path)
        updater.update_single_meta_data(name, value)

    def _update_multi_meta_data(self, item_map):
        for k in item_map:
            rel_path = self.info[ProjectBuilder.MANIFEST_REL_PATH_FLAG][k]
            name = item_map[k]
            env_mode = self.info[ProjectBuilder.ENV_MODE_FLAG]
            value = self.info[k][env_mode]
            self._update_single_meta_data(rel_path, name, value)


class BuildConfigParser(build_base.BuildConfigParser):
    EASEMOB_APPKEY_FLAG = 'easemob_appkey'
    MOXIE_APPKEY_FLAG = 'moxie_appkey'
    CA_AUTH_CODE_FLAG = 'ca_auth_code'
    MANIFEST_REL_PATH_FLAG = 'manifest_rel_path'


class BuildManager(build_base.BuildManager):
    # 配置每个工程个性化的内容   
    def _get_pro_build_config(self):
        # 指定项目地址
        params = {}

        params[ProjectBuilder.PRJ_ROOT_FLAG] = self.prj_root

        bin_name = self.ori_build_config[BuildConfigParser.ENCRYPT_FLAG][BuildConfigParser.BIN_NAME_FLAG]
        enc_bin_path = self.work_path + os.sep + bin_name
        enc_bin_path = myfile.normalpath(enc_bin_path)
        params[ProjectBuilder.ENC_BIN_PATH_FLAG] = enc_bin_path

        net_config_path = self.prj_root + os.sep + self.ori_build_config[BuildConfigParser.NETWORK_FLAG][
            BuildConfigParser.RELATIVE_PATH_FLAG]
        net_config_path = myfile.normalpath(net_config_path)
        params[ProjectBuilder.NET_CONFIG_PATH_FLAG] = net_config_path

        params[ProjectBuilder.NET_INFO_FLAG] = self.ori_build_config[BuildConfigParser.NETWORK_FLAG]
        params[ProjectBuilder.ENV_NET_FLAG] = self.ver_env
        params[ProjectBuilder.ENV_MODE_FLAG] = \
        self.ori_build_config[BuildConfigParser.ENV_FLAG][BuildConfigParser.MAP_FLAG][self.ver_env]

        params[ProjectBuilder.JPUSH_APPKEY_FLAG] = self.ori_build_config[BuildConfigParser.JPUSH_APPKEY_FLAG]
        params[ProjectBuilder.EASEMOB_APPKEY_FLAG] = self.ori_build_config[BuildConfigParser.EASEMOB_APPKEY_FLAG]
        params[ProjectBuilder.MOXIE_APPKEY_FLAG] = self.ori_build_config[BuildConfigParser.MOXIE_APPKEY_FLAG]
        params[ProjectBuilder.CA_AUTH_CODE_FLAG] = self.ori_build_config[BuildConfigParser.CA_AUTH_CODE_FLAG]

        params[ProjectBuilder.MANIFEST_REL_PATH_FLAG] = self.ori_build_config[BuildConfigParser.MANIFEST_REL_PATH_FLAG]

        # 获取加固配置信息
        params[ProjectBuilder.PROTECT_FLAG] = self.ori_build_config[BuildConfigParser.PROTECT_FLAG]
        is_need_infos = params[ProjectBuilder.PROTECT_FLAG][ProjectBuilder.IS_NEED_FLAG]
        for k in is_need_infos:
            is_need_infos[k] = str_utils.get_bool(is_need_infos[k])

        params[ProjectBuilder.SIGNER_FLAG] = self.ori_build_config[BuildConfigParser.SIGNER_FLAG]

        params[ProjectBuilder.BUILD_CLASS_FLAG] = self.ori_build_config[BuildConfigParser.BUILD_CLASS_FLAG]

        params[ProjectBuilder.COVERAGE_FLAG] = self.ori_build_config[BuildConfigParser.COVERAGE_FLAG]

        params[ProjectBuilder.TINGYUN_APPKEY_FLAG] = self.ori_build_config[BuildConfigParser.TINGYUN_APPKEY_FLAG]

        # 将时间格式化
        curr_time = time.localtime()
        time_str = time.strftime('%Y%m%d_%H%M%S', curr_time)

        output_directory = self.work_path + os.sep + self.ori_build_config[BuildConfigParser.WORKSPACE_FLAG][
            BuildConfigParser.TARGET_PATH_FLAG]
        output_directory = myfile.normalpath(output_directory)
        output_directory = output_directory + os.sep + self.ver_env + os.sep + time_str
        params[ProjectBuilder.OUTPUT_DIRECTORY_FLAG] = output_directory

        self.output_directory = params[ProjectBuilder.OUTPUT_DIRECTORY_FLAG]

        params[ProjectBuilder.VER_NAME_FLAG] = self.ver_name
        params[ProjectBuilder.VER_CODE_FLAG] = self.ver_code
        params[ProjectBuilder.ENV_FLAG] = self.ori_build_config[BuildConfigParser.ENV_FLAG]

        params[ProjectBuilder.APP_NAME_FLAG] = self.app_name
        params[ProjectBuilder.DEMO_LABEL_FLAG] = self.demo_label

        if self.use_git:
            code_ver_label = 'git_'
        else:
            code_ver_label = 'svn_'

        params[ProjectBuilder.CODE_VER_FLAG] = code_ver_label + self.code_ver

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
            parser = build_base.ChanInfoParser(chan_path)
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
    parser.add_argument('--git', dest='use_git', action='store_true', default=False,
                        help='indicate to use git update code')

    parser.add_argument('--vername', metavar='ver_name', dest='ver_name', help='version name')
    parser.add_argument('--vercode', metavar='ver_code', dest='ver_code', help='version code')
    parser.add_argument('--verenv', metavar='ver_env', dest='ver_env', type=str,
                        choices=['dev', 'test', 'test2', 'pre', 'pregray', 'gray', 'pro'],
                        help='dev: develop environment; test: test environment; test2: test2 environment; '
                             'pre: pre-release environment; pregray: pre-gray-release environment; '
                             'gray: gray-release environment;  pro: production environment;')

    parser.add_argument('--appname', metavar='app_name', dest='app_name', help='application name')
    parser.add_argument('--svnuser', metavar='svn_user', dest='svn_user', help='subversion username')
    parser.add_argument('--svnpwd', metavar='svn_pwd', dest='svn_pwd', help='subversion password')

    parser.add_argument('--upload', dest='to_upload', action='store_true', default=False,
                        help='indicate to upload build files')
    parser.add_argument('--demo', metavar='demo_label', dest='demo_label', type=str, default='normal',
                        choices=['normal', 'bridge', 'hotloan'],
                        help='normal: normal entry; bridge: bridge entry; hotloan: hot loan entry;')
    parser.add_argument('--branch', metavar='branch', dest='branch', default='master', help='branch name')

    src_group = parser.add_mutually_exclusive_group()
    src_group.add_argument('-s', dest='channel', default=None, help='indicate the channel to build')
    src_group.add_argument('-m', dest='channel_file', default=None,
                           help='indicate the channel file to build multi-file')

    #     parser.print_help()

    return parser.parse_args(src_args)


if __name__ == '__main__':
    #     test_args = '-b -s huawei D:/version_build/pytxxy/config/dynamic/update_config.xml'.split()

    # 转换输出编码，确保打印正常
    #     sys.stdout = io.TextIOWrapper(sys.stdout.buffer, sys.stdin.encoding)

    test_args = None
    args = get_args(test_args)
    utility.measure_time(main, args)
