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

import creditutils.utility_util as util
import update_apk_channel as updater
import creditutils.exec_cmd as exec_cmd

'''
进行Android应用发布操作。
'''

class ConfigLabel:
    ROOT_FLAG = 'config'
    TARGET_PATH_FLAG = 'target_path'
    RELATIVE_FLAG = 'relative'


class ConfigParser:
    def __init__(self, config_path):
        self.config_path = config_path

    def parse(self):
        doc = xmltodict.parse(file_util.read_file_content(self.config_path))
        self.data = doc[BuildConfigLabel.ROOT_FLAG]

    def get_config(self):
        return self.data

    @staticmethod
    def parse_config(config_path):
        parser = ConfigParser(config_path)
        return parser.parse()


class Generator:
    def __init__(self, work_path, app_code, ver_name):
        self.work_path = os.path.abspath(self.work_path)
        self.app_code = app_code
        self.ver_name = ver_name
        self.sftp_config = None
        self.common_config = None

    def _parse_base_config(self):
        # 解析sftp配置
        config_dirs = ['config', 'sftp_config.xml']
        config_path = os.sep.join(config_dirs)
        sftp_config_path = os.path.join(self.work_path, config_path)
        self.sftp_config = ConfigParser.parse_config(sftp_config_path)

        # 解析common配置
        config_dirs = ['config', 'common.xml']
        config_path = os.sep.join(config_dirs)
        common_config_path = os.path.join(self.work_path, config_path)
        self.common_config = ConfigParser.parse_config(common_config_path)

    def process(self):
        # 先解析配置文件获取基本配置信息
        self._parse_base_config()

        # 从sftp服务器下载apk文件
        # 使用下载的apk文件生成渠道包
        # 将单独打包的渠道包也下载下来并以渠道名称命名
        # 将需要外发的渠道包压缩成zip包
        src = os.path.abspath(args.src)
        dst = os.path.abspath(args.dst)
        if os.path.exists(src):
            config_file = args.channel
            updater.batch_update_channel(src, dst, config_file)

class Uploader:
    def __init__(self, args):
        pass
    def process(self):
        # example: ossutil cp F:\apk\pyqx\1.0.6\channel_to_upload oss://txxyapk/pyqx/ -r -f
        cmd_str = f'ossutil cp {} {} -r -f'
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