'''
1.安装阿里云上传工具，并将阿里云上传相关参数配置好，后续直接调用命令行进行操作；
2.将原有生成渠道包步骤简化，把上传专用路径删除，从ftp服务器上下载原始主包，并读取配置文件中需要的渠道包，据此生成最终的渠道包列表。
3.将生成的渠道包列表上传到阿里云，生成需要给运营的渠道包压缩包，并上传到阿里云，使用邮件方式将相应内容信息发送给运营同事；
4.检查当前磁盘上存在的历史渠道版本，只保留最近三次的。
'''
import argparse
import os
import git
import time
import subprocess
import xmltodict

import creditutils.file_util as file_util
import creditutils.trivial_util as util
import update_apk_channel as updater
import creditutils.exec_cmd as exec_cmd

from ftp_download import Manager as download_manager
import update_apk_channel
import pack_subdir_file


'''
进行Android应用发布操作。
'''

APK_SUFFIX = '.apk'

class ConfigLabel:
    ROOT_FLAG = 'config'
    TARGET_PATH_FLAG = 'target_path'
    RELATIVE_FLAG = 'relative'
    CHANNEL_FLAG = 'channel'
    ZIP_FLAG = 'zip'


class ConfigParser:
    def __init__(self, config_path):
        self.config_path = config_path

    def parse(self):
        doc = xmltodict.parse(file_util.read_file_content(self.config_path))
        self.data = doc[ConfigLabel.ROOT_FLAG]

    def get_config(self):
        return self.data

    @staticmethod
    def parse_config(config_path):
        parser = ConfigParser(config_path)
        parser.parse()

        return parser.get_config()


class Generator:
    def __init__(self, work_path, app_code, ver_name):
        self.work_path = os.path.abspath(work_path)
        self.app_code = app_code
        self.ver_name = ver_name
        self.common_config = None
        self.apk_root_path = None

    def _parse_base_config(self):
        # 解析sftp配置
        config_dirs = ['config', 'sftp_config.xml']
        config_path = os.sep.join(config_dirs)
        self.sftp_config_path = os.path.join(self.work_path, config_path)

        # 解析common配置
        config_dirs = ['config', 'common.xml']
        config_path = os.sep.join(config_dirs)
        common_config_path = os.path.join(self.work_path, config_path)
        self.common_config = ConfigParser.parse_config(common_config_path)

    def process(self):
        # 先解析配置文件获取基本配置信息
        self._parse_base_config()

        target_path = self.common_config[ConfigLabel.TARGET_PATH_FLAG]
        self.apk_root_path = os.path.join(self.work_path, target_path, self.app_code, self.ver_name)
        self.apk_root_path = file_util.normalpath(self.apk_root_path)
        
        channel_relative = self.common_config[ConfigLabel.RELATIVE_FLAG][ConfigLabel.CHANNEL_FLAG]
        self.apk_channel_path = os.path.join(self.apk_root_path, channel_relative)
        self.apk_channel_path = file_util.normalpath(self.apk_channel_path)

        zip_relative = self.common_config[ConfigLabel.RELATIVE_FLAG][ConfigLabel.ZIP_FLAG]
        self.zip_channel_path = os.path.join(self.apk_root_path, zip_relative)
        self.zip_channel_path = file_util.normalpath(self.zip_channel_path)

        # 从sftp服务器下载通用apk文件
        download_manager.download_sftp_file(self.sftp_config_path, self.apk_root_path, self.ver_name, sftp_root_tag=self.app_code, as_file=False)

        # 使用下载的apk文件生成渠道包
        self.generate_channel_apk()

        # 将单独打包的渠道包也下载下来并以渠道名称命名
        self.download_exceptional_apk()

        # 将需要外发的渠道包压缩成zip包
        self.zip_channel_apk()

    def _get_source_apk(self):
        src_apk_path = None
        result_list = os.listdir(self.apk_root_path)
        for filename in result_list:
            if filename.endswith(APK_SUFFIX):
                temp_file_path = os.path.join(self.apk_root_path, filename)
                if os.path.isfile(temp_file_path):
                    src_apk_path = temp_file_path
                    break

        return src_apk_path
    
    def generate_channel_apk(self):
        src_apk_path = self._get_source_apk()
        if not src_apk_path:
            raise Exception('not get the source apk!')

        config_path_array = ['config', 'channel', self.app_code, 'target.txt']
        config_relative_path = os.sep.join(config_path_array)
        config_path = os.path.join(self.work_path, config_relative_path)
        update_apk_channel.batch_update_channel(src_apk_path, self.apk_channel_path, config_path)

    def _download_single_exceptional_apk(self, channel):
        download_manager.download_sftp_file(self.sftp_config_path, self.apk_channel_path, self.ver_name, sftp_root_tag=self.app_code, channel=channel, as_file=False)
    
    def download_exceptional_apk(self):
        config_path_array = ['config', 'channel', self.app_code, 'exception.txt']
        config_relative_path = os.sep.join(config_path_array)
        config_path = os.path.join(self.work_path, config_relative_path)
        
        # 读取全部渠道信息
        parser = update_apk_channel.ConfigParser(config_path)
        parser.parse()
        channels = parser.get_config()
        if os.path.isfile(config_path):
            for channel in channels:
                self._download_single_exceptional_apk(channel)

    def _get_zip_pre_name(self):
        app_version_digits = self.ver_name.replace('.', '')
        name_pre = f'{self.app_code}{app_version_digits}apk'
        return name_pre


    def zip_channel_apk(self):
        para_dict = dict()
        para_dict['src'] = self.apk_channel_path
        para_dict['dst'] = self.zip_channel_path
        para_dict['name_pre'] = self._get_zip_pre_name()

        config_path_array = ['config', 'channel', self.app_code, 'to_pack.txt']
        config_relative_path = os.sep.join(config_path_array)
        config_path = os.path.join(self.work_path, config_relative_path)
        para_dict['config'] = config_path
        para_dict['max_size'] = '200M'  # 控制在200M以内
        para_dict['max_num'] = None
        para_obj = util.get_dict_obj(para_dict)
        pack_subdir_file.main(para_obj)


class Uploader:
    def __init__(self, args):
        pass
    def process(self):
        # example: ossutil cp F:\apk\pyqx\1.0.6\channel_to_upload oss://txxyapk/pyqx/ -r -f
        # cmd_str = f'ossutil cp {} {} -r -f'
        cmd_str = ''
        cp = subprocess.run(cmd_str, check=True, shell=True)
        if cp.returncode != 0:
            raise Exception(f'returncode: {cp.returncode}')

class Notifier:
    def __init__(self, args):
        pass
    def process(self):
        pass

class Manager:
    HEAD_NAME = 'HEAD'
    def __init__(self, args):
        # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)
        # pprint.pprint(vars(self))

        self.work_path = os.path.abspath(self.work_path)

    def process(self):
        # 生成渠道包
        if self.to_generate:
            # 如果本地已经有相应目录，则先清空
            # 生成渠道包
            # 生成渠道包压缩包，便于运营同事使用
            pass

        # 上传渠道包、渠道压缩包至阿里云
        if self.to_upload:
            pass

        # 发邮件通知相关人员
        if self.to_notify:
            pass


def main(args):
    manager = Manager(args)
    manager.process()


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='synchronize git repository with remote if need.')
    # 版本名称，如5.1.2
    parser.add_argument('ver_name', metavar='ver_name', help='version name')
    # 工作目录
    parser.add_argument('work_path', metavar='work_path', help='working directory')

    parser.add_argument('--appcode', metavar='app_code', dest='app_code', type=str, default='txxy',
                        choices=['txxy', 'xycx', 'pyqx', 'pyzx'],
                        help='txxy: tian xia xin yong; xycx: xin yong cha xun; pyqx: peng you qi xin; pyzx: peng yuan zheng xin;')
    # 是否进行生成渠道包的操作
    parser.add_argument('-g', dest='to_generate', action='store_true', default=False, help='indicate to generate channel apk')

    # 是否进行发送官网升级包的操作
    parser.add_argument('--official', dest='to_update_official', action='store_true', default=False, help='indicate to update official apk')

    # 是否上传到阿里云
    parser.add_argument('--upload', dest='to_upload', action='store_true', default=False,
                        help='indicate to upload channel files and zipped files')
    # 是否发邮件通知给相关人员
    parser.add_argument('--notify', dest='to_notify', action='store_true', default=False,
                        help='indicate to notify relevant personnel')

    #     parser.print_help()

    return parser.parse_args(src_args)


if __name__ == '__main__':
    test_args = None
    args = get_args(test_args)
    util.measure_time(main, args)