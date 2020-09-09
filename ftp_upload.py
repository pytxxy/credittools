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


def upload_to_sftp(sftp_config_path, ver_name_code, ver_env, svn_version, sftp_root_tag='txxy',
                   local_dir_path='', mobile_os='', channel='', target_file_name='', source_file_name=''):
    """
        :param sftp_root_tag:
        :param sftp_config_path: sftp 配置文件路径
        :param sftp_root_tag 默认txxy
        :param ver_name_code: 版本号和构建版本 ex: 3.4.6beta_t_01
        :param ver_env: 构建环境
        :param svn_version: svn 版本号 或者 git 版本号
        :param local_dir_path: 待上传文件夹路径
        :param mobile_os: 运行环境
        :param target_file_name: 目标文件名
        :param source_file_name: 原始文件名
        :return:
    """
    local_dir_path = file_util.normalpath(local_dir_path)
    sftp_config = SFTPConfigFile(sftp_config_path)
    sftp_config_data = sftp_config.get_data()

    sftp_handler = sftp_util.sftp_connect(sftp_config_data[_HOST_FLAG], sftp_config_data[_PORT_FLAG],
                                          sftp_config_data[_USERNAME_FLAG], sftp_config_data[_PASSWORD_FLAG])
    if sftp_handler[0] == 1:
        print(sftp_handler[1])
        sftp_cli = sftp_handler[2]
        detail_env = sftp_config_data[SFTPConfigFile.ENV_FLAG]
        remote_dir = ''

        # 分割ver_name 和 ver_code
        if mobile_os.lower() != 'wechat':
            ver_name = ''
            ver_code = ''
            if re.search('beta_', ver_name_code):
                name_code_group = re.split('beta_', ver_name_code)
                ver_name = name_code_group[0]
                ver_code = name_code_group[1]
                if re.search('_ent', name_code_group[1]):
                    ver_code = re.split('_ent', name_code_group[1])[0]

            elif re.search('_g', ver_name_code):
                name_code_group = re.split('_g', ver_name_code)
                ver_name = name_code_group[0]

            else:
                if re.search('_ent', ver_name_code):
                    name_code_group = re.split('_ent', ver_name_code)
                    ver_name = name_code_group[0]
                else:
                    ver_name = ver_name_code
            remote_root_dir = sftp_config_data[_ROOT_SFTP_PATH_FLAG]
            remote_dir = os.path.join(remote_root_dir[sftp_root_tag], ver_name, detail_env[ver_env])
            remote_dir = file_util.normal_unix_path(remote_dir)

            # 生产版本不一定有ver_code
            if ver_code:
                remote_dir = file_util.join_unix_path(remote_dir, ver_code, mobile_os)
            else:
                remote_dir = file_util.join_unix_path(remote_dir, mobile_os)

            if len(channel):
                remote_dir = file_util.join_unix_path(remote_dir, channel)


            # 上传 ipa 包或者 apk 包
            # 判断 sftp 文件夹有没有之前的老包，有的话则需要先删除

            try:
                sftp_cli.chdir(remote_dir)
                sftp_dir_list = sftp_cli.listdir(remote_dir)
                for filename in sftp_dir_list:
                    if os.path.splitext(filename)[1] == '.ipa':
                        if (target_file_name.find('ent') > 0 and filename.find('ent') > 0) or \
                                (target_file_name.find('ent') == -1 and filename.find('ent') == -1):
                            sftp_cli.remove(file_util.join_unix_path(remote_dir, filename))
                            break
                    elif os.path.splitext(filename)[1] == '.apk':
                        sftp_cli.remove(file_util.join_unix_path(remote_dir, filename))
                        break

            except Exception as e:
                print(e)

            local_package_file_path = os.path.join(local_dir_path, source_file_name)


            upload_package_file_result=sftp_util.sftp_upload_file(sftp_cli,remote_dir,local_package_file_path)
            sftp_cli.rename(file_util.join_unix_path(remote_dir, source_file_name),
                            file_util.join_unix_path(remote_dir, target_file_name))
            if upload_package_file_result[0] == 1:
                print(upload_package_file_result[1])
            else:
                print(upload_package_file_result[1])

            # 上传打包记录文件(record.txt)

            sftp_dir_list = sftp_cli.listdir(remote_dir)
            record_text_file_name = 'record.txt'
            record_file_path = file_util.join_unix_path(remote_dir, record_text_file_name)
            local_record_path = file_util.normalpath(os.path.join(local_dir_path, record_text_file_name))
            for filename in sftp_dir_list:
                if record_text_file_name in filename:
                    sftp_util.sftp_download(sftp_cli, record_file_path, local_dir_path)

            record_text_data = {'code_version': svn_version,
                                'target_file_name': target_file_name}
            with open(local_record_path, 'a') as json_file:
                json.dump(record_text_data, json_file, sort_keys=True)
                json_file.write(os.linesep)

            upload_record_result = sftp_util.sftp_upload_file(sftp_cli, remote_dir, local_record_path)
            if upload_record_result[0] == 1:
                print(upload_record_result[1])
                os.remove(local_record_path)
            else:
                print(upload_record_result[1])

            remote_data_path = file_util.join_unix_path(remote_dir, 'data', svn_version)
            upload_data_result = sftp_util.sftp_upload(sftp_cli, remote_data_path, local_dir_path)
            if upload_data_result[0] == 1:
                print(upload_data_result[1])
            else:
                print(upload_data_result[1])
            sftp_cli.close()
        else:
            ver_name = ''
            ver_code = ''
            if re.search('(\d\.\d\.\d)(\w*)', ver_name_code):
                name_code_group = re.search('(\d\.\d\.\d)(\w*)', ver_name_code)
                ver_name = name_code_group.group(1)
                ver_code = name_code_group.group(2)

            # 上传打包记录文件(record.txt)
            local_dir_path = sftp_config_path
            remote_dir = file_util.join_unix_path(sftp_config_data[_ROOT_SFTP_PATH_FLAG], ver_name, detail_env[ver_env])
            remote_dir = file_util.normal_unix_path(remote_dir)
            record_text_file_name = 'record.txt'
            record_file_path = file_util.join_unix_path(remote_dir, record_text_file_name)
            local_record_path = os.path.join(local_dir_path, record_text_file_name)
            try:
                sftp_cli.chdir(remote_dir)
                sftp_dir_list = sftp_cli.listdir(remote_dir)
                for filename in sftp_dir_list:
                    if record_text_file_name in filename:
                        sftp_util.sftp_download(sftp_cli, record_file_path, local_dir_path)
            except Exception as e:
                print(e)
            record_text_data = {'ver_code': ver_code,
                                'code_version': svn_version,
                                'pack_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            with open(local_record_path, 'a') as json_file:
                json.dump(record_text_data, json_file, sort_keys=True)
                json_file.write(os.linesep)

            upload_record_result = sftp_util.sftp_upload_file(sftp_cli, remote_dir, local_record_path)
            if upload_record_result[0] == 1:
                print(upload_record_result[1])
                os.remove(local_record_path)
            else:
                print(upload_record_result[1])

    else:
        print(sftp_handler[1])


if __name__ == '__main__':
    upload_to_sftp(sftp_config_path=r'/Users/apple/Documents/build_script/ios/pytxxy', sftp_root_tag='txxy',ver_name_code='4.0.1beta_t_01',
                   ver_env='test', svn_version='610b85b4d600b266b1c3c2dc6c3c06f789877290', mobile_os='Android',
                   local_dir_path=r'D:\auto_build\pytxxy\output\test\20190424_093723',
                   target_file_name='4.0.1beta_t_01-526-20190424.apk',
                   source_file_name='4.0.1beta_t_01-526-20190424.apk')

    # for s in sys.path:
    #     print(s)
