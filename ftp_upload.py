# ! python3

import os
import xmltodict
import creditutils.file_util as file_util
import re
import creditutils.sftp_util as sftp_util
import json
import datetime
import sys

_USERNAME_FLAG = 'username'
_PASSWORD_FLAG = 'password'
_HOST_FLAG = 'host'
_PORT_FLAG = 'port'
_ROOT_SFTP_PATH_FLAG = 'sftp_path'


class SFTPConfigFile:
    CONFIG_FLAG = 'config'
    ENV_FLAG = 'env'

    def __init__(self, src_root):
        self.work_path = os.path.abspath(src_root)
        sftp_config_path = ['config', 'base', 'sftp_config.xml']
        sftp_config_path = os.sep.join(sftp_config_path)
        self.sftp_config_path = self.work_path + os.sep + sftp_config_path
        # 解析配置
        doc = xmltodict.parse(file_util.read_file_content(self.sftp_config_path))
        self.data = doc[SFTPConfigFile.CONFIG_FLAG]

    def get_data(self):
        return self.data


class UploadManager:
    def __init__(self, config_path):
        self.config_path = config_path
        
        sftp_config = SFTPConfigFile(config_path)
        self.config_data = sftp_config.get_data()

    def init_path_config(self, ver_name_code, ver_env, code_version, sftp_root_tag='txxy', local_dir_path='', mobile_os='', channel=''):
        self.ver_name_code = ver_name_code
        self.ver_env = ver_env
        self.code_version = code_version
        self.sftp_root_tag = sftp_root_tag
        self.local_dir_path = file_util.normalpath(local_dir_path)
        self.mobile_os = mobile_os
        self.channel = channel

    # 上传 ipa 包或者 apk 包
    def _upload_setup_file(self, sftp_cli, remote_dir, source_file_name, target_file_name):
    # 判断 sftp 文件夹有没有之前的老包，有的话则需要先删除
        sftp_cli.chdir(remote_dir)
        sftp_dir_list = sftp_cli.listdir(remote_dir)
        for filename in sftp_dir_list:
            if os.path.splitext(filename)[1] == '.ipa':
                if (target_file_name.find('ent') > 0 and filename.find('ent') > 0) or \
                        (target_file_name.find('ent') == -1 and filename.find('ent') == -1):
                    try:
                        print('开始删除')
                        print(file_util.join_unix_path(remote_dir, filename))
                        sftp_cli.remove(file_util.join_unix_path(remote_dir, filename))
                        break
                    except Exception as e:
                        print(e)

            elif os.path.splitext(filename)[1] == '.apk':
                sftp_cli.remove(file_util.join_unix_path(remote_dir, filename))
                break

        local_file_path = os.path.join(self.local_dir_path, source_file_name)

        result = sftp_util.sftp_upload_file(sftp_cli, remote_dir, local_file_path)
        if self.mobile_os.lower() == 'android':
            sftp_cli.rename(file_util.join_unix_path(remote_dir, source_file_name),
                            file_util.join_unix_path(remote_dir, target_file_name))
        print(result[1])

    def _upload_record_file(self, sftp_cli, remote_dir, data, file_name='record.txt'):
        sftp_cli.chdir(remote_dir)
        sftp_dir_list = sftp_cli.listdir(remote_dir)
        remote_file_path = file_util.join_unix_path(remote_dir, file_name)
        local_file_path = file_util.normalpath(os.path.join(self.local_dir_path, file_name))
        for filename in sftp_dir_list:
            if file_name in filename:
                sftp_util.sftp_download(sftp_cli, remote_file_path, self.local_dir_path)
        
        with open(local_file_path, 'a') as json_file:
            json.dump(data, json_file, sort_keys=True)
            json_file.write(os.linesep)

        result = sftp_util.sftp_upload_file(sftp_cli, remote_dir, local_file_path)
        print(result[1])
        if result[0] == 1:
            os.remove(local_file_path)

    def _upload_desc_file(self, sftp_cli, remote_dir, data, file_name='description.txt'):
        sftp_cli.chdir(remote_dir)
        local_file_path = file_util.normalpath(os.path.join(self.local_dir_path, file_name))
        
        with open(local_file_path, 'w') as json_file:
            json.dump(data, json_file, sort_keys=True)

        result = sftp_util.sftp_upload_file(sftp_cli, remote_dir, local_file_path)
        print(result[1])
        if result[0] == 1:
            os.remove(local_file_path)

    def _upload_whole_data(self, sftp_cli, remote_dir):
        remote_path = file_util.join_unix_path(remote_dir, 'data', self.code_version)
        result = sftp_util.sftp_upload(sftp_cli, remote_path, self.local_dir_path)
        print(result[1])

    def _upload_app(self, sftp_cli, source_file_name, target_file_name, desc_data):
        detail_env = self.config_data[SFTPConfigFile.ENV_FLAG]
        remote_dir = ''
        ver_name = ''
        ver_code = ''
        if re.search('beta_', self.ver_name_code):
            name_code_group = re.split('beta_', self.ver_name_code)
            ver_name = name_code_group[0]
            ver_code = name_code_group[1]
            if re.search('_ent', name_code_group[1]):
                ver_code = re.split('_ent', name_code_group[1])[0]

        elif re.search('_g', self.ver_name_code):
            name_code_group = re.split('_g', self.ver_name_code)
            ver_name = name_code_group[0]
        else:
            if re.search('_ent', self.ver_name_code):
                name_code_group = re.split('_ent', self.ver_name_code)
                ver_name = name_code_group[0]
            else:
                ver_name = self.ver_name_code
        remote_root_dir = self.config_data[_ROOT_SFTP_PATH_FLAG]
        remote_dir = os.path.join(remote_root_dir[self.sftp_root_tag], ver_name, detail_env[self.ver_env])
        remote_dir = file_util.normal_unix_path(remote_dir)

        # 生产版本不一定有ver_code
        if ver_code:
            remote_dir = file_util.join_unix_path(remote_dir, ver_code, self.mobile_os)
        else:
            remote_dir = file_util.join_unix_path(remote_dir, self.mobile_os)

        if len(self.channel):
            remote_dir = file_util.join_unix_path(remote_dir, self.channel)

        # 上传 ipa 包或者 apk 包
        self._upload_setup_file(sftp_cli, remote_dir, source_file_name, target_file_name)

        # 上传打包记录文件(record.txt)
        record_text_data = {'code_version': self.code_version,
                            'target_file_name': target_file_name}
        self._upload_record_file(sftp_cli, remote_dir, record_text_data)

        if desc_data:
            self._upload_desc_file(sftp_cli, remote_dir, desc_data)

        # 上传目录所有文件，进行整体备份
        self._upload_whole_data(sftp_cli, remote_dir)

    def _upload_wechat(self, sftp_cli):
        detail_env = self.config_data[SFTPConfigFile.ENV_FLAG]
        ver_name = ''
        ver_code = ''
        if re.search('(\d\.\d\.\d)(\w*)', self.ver_name_code):
            name_code_group = re.search('(\d\.\d\.\d)(\w*)', self.ver_name_code)
            ver_name = name_code_group.group(1)
            ver_code = name_code_group.group(2)

        # 上传打包记录文件(record.txt)
        self.local_dir_path = self.config_path
        remote_dir = file_util.join_unix_path(self.config_data[_ROOT_SFTP_PATH_FLAG], ver_name, detail_env[self.ver_env])
        remote_dir = file_util.normal_unix_path(remote_dir)
        record_text_data = {'ver_code': ver_code,
                            'code_version': self.code_version,
                            'pack_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        self._upload_record_file(sftp_cli, remote_dir, record_text_data)

    def upload_to_sftp(self, target_file_name='', source_file_name='', desc_data=None):
        sftp_handler = sftp_util.sftp_connect(self.config_data[_HOST_FLAG], self.config_data[_PORT_FLAG],
                                          self.config_data[_USERNAME_FLAG], self.config_data[_PASSWORD_FLAG])
        if sftp_handler[0] == 1:
            print(sftp_handler[1])
            sftp_cli = sftp_handler[2]

            # 分割ver_name 和 ver_code
            if self.mobile_os.lower() != 'wechat':
                self._upload_app(sftp_cli, source_file_name, target_file_name, desc_data)
            else:
                self._upload_wechat(sftp_cli)

            sftp_cli.close()
        else:
            raise Exception(sftp_handler[1])
            print(sftp_handler[1])


def upload_to_sftp(sftp_config_path, ver_name_code, ver_env, code_version, sftp_root_tag='txxy',
                   local_dir_path='', mobile_os='', channel='', target_file_name='', source_file_name='', desc_data=None):
    """
        :param sftp_root_tag:
        :param sftp_config_path: sftp 配置文件路径
        :param sftp_root_tag 默认txxy
        :param ver_name_code: 版本号和构建版本 ex: 3.4.6beta_t_01
        :param ver_env: 构建环境
        :param code_version: svn 版本号 或者 git 版本号
        :param local_dir_path: 待上传文件夹路径
        :param mobile_os: 运行环境
        :param target_file_name: 目标文件名
        :param source_file_name: 原始文件名
        :return:
    """

    manager = UploadManager(sftp_config_path)
    manager.init_path_config(ver_name_code, ver_env, code_version, sftp_root_tag=sftp_root_tag, local_dir_path=local_dir_path, mobile_os=mobile_os, channel=channel)
    manager.upload_to_sftp(target_file_name=target_file_name, source_file_name=source_file_name, desc_data=desc_data)


if __name__ == '__main__':
    try:
        upload_to_sftp(sftp_config_path=r'/Users/apple/Documents/BuildScript/ios/pytxxy', sftp_root_tag='test', ver_name_code='4.0.1beta_t_01',
                    ver_env='test', code_version='610b85b4d600b266b1c3c2dc6c3c06f789877290', mobile_os='Android',
                    local_dir_path=r'D:\auto_build\pytxxy\output\test\20190424_093723',
                    target_file_name='4.0.1beta_t_01-526-20190424.apk',
                    source_file_name='4.0.1beta_t_01-526-20190424.apk')
    except Exception as e:
        raise Exception('upload to ftp Error')

    # for s in sys.path:
    #     print(s)
