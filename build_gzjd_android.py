# -*- coding:UTF-8 -*-
# 20161109 21:30 根据android 新框架进行适当地调整 
import argparse
import os
import pprint
import time

import creditutils.apk_builder_util as apk_builder
import creditutils.build_base_android as build_base
import creditutils.file_util as myfile
import creditutils.str_util as str_utils


# 对整个工程内相关文件进行替换操作
class ProjectBuilder(build_base.ProjectBuilder):
    def __init__(self, prj_path, chan_map, res_path, info):
        self.prj_path = prj_path
        self.chan_map = chan_map
        self.res_path = res_path
        self.info = info

        self.gradle_path = os.path.join(self.prj_path, 'build.gradle')
        self.gradle_path = os.path.normpath(self.gradle_path)

        self.manifest_path = self.prj_path + os.sep + 'src/main/AndroidManifest.xml'
        self.manifest_path = myfile.normalpath(self.manifest_path)

    # 更新通用信息
    def update_info(self):
        version_code = self.info[ProjectBuilder.VER_CODE_FLAG]
        version_name = self.info[ProjectBuilder.VER_NAME_FLAG]
        ver_info_updater = apk_builder.GradleVerInfoUpdater(self.gradle_path)
        ver_info_updater.update_version_config(version_code, version_name)

        config_updater = apk_builder.ManifestConfigInfoUpdater(self.manifest_path)
        config_updater.update_single_meta_data(ProjectBuilder.JPUSH_APPKEY_FLAG,
                                               self.info[ProjectBuilder.JPUSH_APPKEY_FLAG][
                                                   self.info[ProjectBuilder.ENV_MODE_FLAG]])

        env_mode = self.info[ProjectBuilder.ENV_MODE_FLAG]
        env_config = self.info[ProjectBuilder.ENV_FLAG]
        env_path = self.prj_path + os.sep + env_config[ProjectBuilder.FILE_ITEM_FLAG]
        if os.path.exists(env_path):
            env_updater = build_base.EnvironmentUpdater(env_path)
            env_updater.update_config(env_mode)
        else:
            print('not exist {}!'.format(env_path))


class BuildManager(build_base.BuildManager):
    def _get_pro_build_config(self):
        # 指定项目地址
        params = {}

        params[ProjectBuilder.JPUSH_APPKEY_FLAG] = self.ori_build_config[build_base.BuildConfigParser.JPUSH_APPKEY_FLAG]
        params[ProjectBuilder.ENV_MODE_FLAG] = \
            self.ori_build_config[build_base.BuildConfigParser.ENV_FLAG][build_base.BuildConfigParser.MAP_FLAG][
                self.ver_env]

        # 将时间格式化
        curr_time = time.localtime()
        time_str = time.strftime('%Y%m%d_%H%M%S', curr_time)

        output_directory = self.work_path + os.sep + self.ori_build_config[build_base.BuildConfigParser.WORKSPACE_FLAG][
            build_base.BuildConfigParser.TARGET_PATH_FLAG]
        output_directory = myfile.normalpath(output_directory)
        output_directory = output_directory + os.sep + self.ver_env + os.sep + time_str
        params[build_base.ProjectBuilder.OUTPUT_DIRECTORY_FLAG] = output_directory

        self.output_directory = params[build_base.ProjectBuilder.OUTPUT_DIRECTORY_FLAG]

        params[build_base.ProjectBuilder.VER_NAME_FLAG] = self.ver_name
        params[build_base.ProjectBuilder.VER_CODE_FLAG] = self.ver_code
        params[build_base.ProjectBuilder.ENV_FLAG] = self.ori_build_config[build_base.BuildConfigParser.ENV_FLAG]

        # 获取加固配置信息
        params[ProjectBuilder.PROTECT_FLAG] = self.ori_build_config[build_base.BuildConfigParser.PROTECT_FLAG]
        is_need_infos = params[ProjectBuilder.PROTECT_FLAG][ProjectBuilder.IS_NEED_FLAG]
        for k in is_need_infos:
            is_need_infos[k] = str_utils.get_bool(is_need_infos[k])
        params[ProjectBuilder.SIGNER_FLAG] = self.ori_build_config[build_base.BuildConfigParser.SIGNER_FLAG]

        # 指定输出归档文件地址
        date_str = time.strftime('%Y%m%d', curr_time)

        if self.is_debug:
            mode_flag = apk_builder.DEBUG_FLAG

            # 指定输出apk名称
            params[build_base.ProjectBuilder.OUTPUT_NAME_FLAG] = "{}-{}-{}-{}.apk".format(self.ver_name, self.ver_code,
                                                                                          mode_flag, date_str)
        else:
            mode_flag = apk_builder.RELEASE_FLAG

            # 指定输出apk名称
            params[build_base.ProjectBuilder.OUTPUT_NAME_FLAG] = "{}-{}-{}.apk".format(self.ver_name, self.ver_code,
                                                                                       date_str)

        params[build_base.ProjectBuilder.TYPE_FLAG] = mode_flag
        self.apk_output_path = params[build_base.ProjectBuilder.OUTPUT_DIRECTORY_FLAG] + os.sep + params[
            build_base.ProjectBuilder.OUTPUT_NAME_FLAG]

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
    parser.add_argument('--verenv', metavar='ver_env', dest='ver_env', type=str, choices=['dev', 'test', 'pre', 'pro'],
                        help='dev: develop environment; test: test environment; pre: pre-release environment; pro: production environment;')
    parser.add_argument('--branch', metavar='branch', dest='branch', default='master', help='branch name')
    parser.add_argument('--upload', dest='to_upload', action='store_true', default=False,
                        help='indicate to upload build files')

    src_group = parser.add_mutually_exclusive_group()
    src_group.add_argument('-s', dest='channel', default=None, help='indicate the channel to build')
    src_group.add_argument('-m', dest='channel_file', default=None,
                           help='indicate the channel file to build multi-file')

    #     parser.print_help()

    return parser.parse_args(src_args)


if __name__ == '__main__':
    begin = time.time()

    #     test_args = '-b -s huawei D:/version_build/pytxxy/config/dynamic/update_config.xml'.split()
    test_args = None
    args = get_args(test_args)
    main(args)

    end = time.time()
    time_info = str_utils.get_time_info(begin, end)

    # 输出总用时
    print('===Finished. Total time: {}==='.format(time_info))
