# ! python3

import os
import json
import tempfile
import shutil
import creditutils.file_util as file_util
import creditutils.sftp_util as sftp_util
import config_parser


class ConfigLabel:
    USERNAME_FLAG = 'username'
    PASSWORD_FLAG = 'password'
    HOST_FLAG = 'host'
    PORT_FLAG = 'port'
    SFTP_PATH_FLAG = 'sftp_path'
    ENV_FLAG = 'env'

class DownloadMonitor:
    def __init__(self, remote_path, local_path):
        self.remote_path = remote_path
        self.local_path = local_path

    def feedback(self, transferred, total):
        remote_name = os.path.basename(self.remote_path)
        local_name = os.path.basename(self.local_path)
        print(f'downloading {remote_name} to {local_name}, total {total} bytes, transferred {transferred} bytes.')


class Manager:
    APK_SUFFIX = '.apk'
    def __init__(self, config_path, debug=False):
        self.config_path = config_path
        self.config_data = config_parser.ConfigParser.parse_config(self.config_path)

        self.debug = debug

    def init_path_config(self, ver_name, ver_env='pro', sftp_root_tag='txxy', mobile_os='Android'):
        self.ver_name = ver_name
        self.ver_env = ver_env
        self.sftp_root_tag = sftp_root_tag
        self.mobile_os = mobile_os

    def _download_single_file(self, sftp_cli, remote_file_path, local_file_path, force, as_file, callback=None):
        print(f'remote_file_path: {remote_file_path}')
        print(f'local_file_path: {local_file_path}')
        sftp_handler = sftp_util.sftp_download_file(sftp_cli, remote_file_path, local_file_path, force=force, as_file=as_file, callback=callback)
        print(sftp_handler[1])

    def _download_file(self, sftp_cli, local_dir_path, ver_no, channel, target_file_name, force, as_file):
        env_info = self.config_data[ConfigLabel.ENV_FLAG]
        remote_root_dir = self.config_data[ConfigLabel.SFTP_PATH_FLAG]
        remote_dir = os.path.join(remote_root_dir[self.sftp_root_tag], self.ver_name, env_info[self.ver_env])
        remote_dir = file_util.normal_unix_path(remote_dir)

        # 生产版本不一定有ver_no
        if ver_no:
            remote_dir = file_util.join_unix_path(remote_dir, ver_no, self.mobile_os)
        else:
            remote_dir = file_util.join_unix_path(remote_dir, self.mobile_os)

        if len(channel):
            remote_dir = file_util.join_unix_path(remote_dir, channel)

        sftp_cli.chdir(remote_dir)
        sftp_dir_list = sftp_cli.listdir(remote_dir)
        for filename in sftp_dir_list:
            if filename.endswith(Manager.APK_SUFFIX):
                remote_file_path = file_util.join_unix_path(remote_dir, filename)
                local_file_name = filename
                if len(channel):
                    local_file_name = channel + Manager.APK_SUFFIX
                if target_file_name:
                    local_file_name = target_file_name
                local_file_path = file_util.normalpath(os.path.join(local_dir_path, local_file_name))
                # self._download_single_file(sftp_cli, remote_file_path, local_file_path, force)
                if self.debug:
                    monitor = DownloadMonitor(remote_file_path, local_file_path)
                    callback = monitor.feedback
                else:
                    callback = None
                self._download_single_file(sftp_cli, remote_file_path, local_file_path, force, as_file, callback=callback)

    def download_file(self, local_dir_path, ver_no='', channel='', target_file_name='', force=True, as_file=True):
        """
        :param ver_env: 构建环境
        :param sftp_root_tag 默认txxy
        :param mobile_os: 运行环境
        :param local_dir_path: 待下载文件存放路径
        :param target_file_name: 目标文件名
        :param force: 是否进行覆盖操作
        :return:
        """
        sftp_handler = sftp_util.sftp_connect(self.config_data[ConfigLabel.HOST_FLAG], self.config_data[ConfigLabel.PORT_FLAG],
                                          self.config_data[ConfigLabel.USERNAME_FLAG], self.config_data[ConfigLabel.PASSWORD_FLAG])
        if sftp_handler[0] == 1:
            print(sftp_handler[1])
            sftp_cli = sftp_handler[2]

            self._download_file(sftp_cli, local_dir_path, ver_no, channel, target_file_name, force, as_file)

            sftp_cli.close()
        else:
            print(sftp_handler[1])

    @staticmethod
    def download_sftp_file(sftp_config_path, local_dir_path, ver_name, ver_env='pro', sftp_root_tag='txxy', mobile_os='Android',
                    ver_no='', channel='', target_file_name='', force=True, as_file=True, debug=False):
        """
            :param sftp_config_path: sftp 配置文件路径
            :param local_dir_path: 下载文件存放路径
            :param ver_name: 版本名称: 5.1.8
            :param ver_env: 构建环境
            :param sftp_root_tag 默认txxy
            :param mobile_os: 运行环境
            :param channel: 渠道名称
            :param target_file_name: 目标文件名
            :param force: 是否强制覆盖文件
            :return:
        """
        manager = Manager(sftp_config_path, debug=debug)
        manager.init_path_config(ver_name, ver_env=ver_env, sftp_root_tag=sftp_root_tag, mobile_os=mobile_os)
        manager.download_file(local_dir_path, ver_no=ver_no, channel=channel, target_file_name=target_file_name, force=force, as_file=as_file)
