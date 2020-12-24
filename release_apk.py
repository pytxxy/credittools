'''
1.安装阿里云上传工具，并将阿里云上传相关参数配置好，后续直接调用命令行进行操作；
2.将原有生成渠道包步骤简化，把上传专用路径删除，从ftp服务器上下载原始主包，并读取配置文件中需要的渠道包，据此生成最终的渠道包列表。
3.将生成的渠道包列表上传到阿里云，生成需要给运营的渠道包压缩包，并上传到阿里云，使用邮件方式将相应内容信息发送给运营同事；
4.检查当前磁盘上存在的历史渠道版本，只保留最近三次的。
'''
import argparse
import os
import time
import subprocess
import xmltodict
import shutil

import creditutils.file_util as file_util
import creditutils.trivial_util as util
import update_apk_channel as updater
import creditutils.exec_cmd as exec_cmd

from ftp_download import Manager as download_manager
import update_apk_channel
import pack_subdir_file
import creditutils.mail_util as mail_util
import creditutils.dingtalk_util as dingtalk_util


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

    BUCKET_FLAG = 'bucket'
    DOMAIN_FLAG = 'domain'
    OFFICIAL_FLAG = 'official'

    HOST_FLAG = 'host'
    PORT_FLAG = 'port'
    EMAIL_FLAG = 'email'
    NAME_FLAG = 'name'
    PASSWD_FLAG = 'passwd'

    MAIL_FLAG = 'mail'
    RECEIVER_FLAG = 'receiver'
    CC_FLAG = 'cc'

    DINGTALK_FLAG = 'dingtalk'
    WEBHOOK_FLAG = 'webhook'
    SECRET_FLAG = 'secret'
    AT_FLAG = 'at'
    MOBILE_FLAG = 'mobile'


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


# 每次只保留当前App本地最近的三个版本，其他的版本要优先清理掉
# 如果本地已经有相应目录，则先清空
# 生成渠道包
# 生成渠道包压缩包，便于运营同事使用
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
        self.apk_root_parent_path = os.path.join(self.work_path, target_path, self.app_code)
        self.apk_root_path = os.path.join(self.work_path, target_path, self.app_code, self.ver_name)
        self.apk_root_path = file_util.normalpath(self.apk_root_path)
        
        channel_relative = self.common_config[ConfigLabel.RELATIVE_FLAG][ConfigLabel.CHANNEL_FLAG]
        self.apk_channel_path = os.path.join(self.apk_root_path, channel_relative)
        self.apk_channel_path = file_util.normalpath(self.apk_channel_path)

        zip_relative = self.common_config[ConfigLabel.RELATIVE_FLAG][ConfigLabel.ZIP_FLAG]
        self.zip_channel_path = os.path.join(self.apk_root_path, zip_relative)
        self.zip_channel_path = file_util.normalpath(self.zip_channel_path)

        # 先进行清理本地apk文件夹操作
        self._clear_output_directory(self.apk_root_parent_path)

        # 如果已经存在目标文件夹，则先删除
        if os.path.isdir(self.apk_root_path):
            shutil.rmtree(self.apk_root_path)

        # 从sftp服务器下载通用apk文件
        download_manager.download_sftp_file(self.sftp_config_path, self.apk_root_path, self.ver_name, sftp_root_tag=self.app_code, as_file=False)

        # 使用下载的apk文件生成渠道包
        self.generate_channel_apk()

        # 将单独打包的渠道包也下载下来并以渠道名称命名
        self.download_exceptional_apk()

        # 将需要外发的渠道包压缩成zip包
        self.zip_channel_apk()

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
        
        if os.path.isfile(config_path):
            parser = update_apk_channel.ConfigParser(config_path)
            parser.parse()
            channels = parser.get_config()
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
    def __init__(self, work_path, app_code, ver_name):
        self.work_path = os.path.abspath(work_path)
        self.app_code = app_code
        self.ver_name = ver_name
        self.common_config = None
        self.upload_config = None

        self._parse_base_config()

    def _parse_base_config(self):
        # 解析common配置
        config_dirs = ['config', 'common.xml']
        config_path = os.sep.join(config_dirs)
        common_config_path = os.path.join(self.work_path, config_path)
        self.common_config = ConfigParser.parse_config(common_config_path)

        # 解析upload配置
        config_dirs = ['config', 'upload_config.xml']
        config_path = os.sep.join(config_dirs)
        upload_config_path = os.path.join(self.work_path, config_path)
        self.upload_config = ConfigParser.parse_config(upload_config_path)

    def process(self):
        self._upload_dir(ConfigLabel.CHANNEL_FLAG)
        self._upload_dir(ConfigLabel.ZIP_FLAG)
        self.upload_official_file()

    def _get_src_path(self, tag):
        src_relative_path = self.common_config[ConfigLabel.TARGET_PATH_FLAG]
        apk_root_path = os.path.join(self.work_path, src_relative_path, self.app_code, self.ver_name)
        apk_root_path = file_util.normalpath(apk_root_path)
        tag_relative = self.common_config[ConfigLabel.RELATIVE_FLAG][tag]
        apk_tag_path = os.path.join(apk_root_path, tag_relative)
        apk_tag_path = file_util.normalpath(apk_tag_path)
        return apk_tag_path

    def _get_official_file_path(self):
        channel_dir_path = self._get_src_path(ConfigLabel.CHANNEL_FLAG)
        filename = self.upload_config[ConfigLabel.OFFICIAL_FLAG]
        file_path = os.path.join(channel_dir_path, filename)
        return file_path
    
    def _get_official_target_file_name(self):
        src_name = self.upload_config[ConfigLabel.OFFICIAL_FLAG]
        pure_name = src_name
        if src_name.endswith(APK_SUFFIX):
            pure_name = src_name[0:-len(APK_SUFFIX)]

        target_name = f'{pure_name}_{self.app_code}_{self.ver_name}{APK_SUFFIX}'
        return target_name

    def _get_official_bucket_path(self):
        bucket_dir_path = self._get_bucket_path(ConfigLabel.OFFICIAL_FLAG)
        filename = self._get_official_target_file_name()
        bucket_file_path = bucket_dir_path + filename
        return bucket_file_path

    def _get_bucket_path(self, tag):
        bucket = self.upload_config[ConfigLabel.BUCKET_FLAG]
        tag_relative = self.upload_config[ConfigLabel.RELATIVE_FLAG][self.app_code][tag]
        if tag_relative:
            bucket_path = bucket + file_util.unix_sep + tag_relative
        else:
            bucket_path = bucket

        if not bucket_path.endswith(file_util.unix_sep):
            bucket_path = bucket_path + file_util.unix_sep

        return bucket_path

    def _upload_dir(self, tag):
        apk_tag_path = self._get_src_path(tag)
        bucket_path = self._get_bucket_path(tag)
        self.upload_dir(apk_tag_path, bucket_path)

    def upload_dir(self, src_dir, dst_path):
        if not os.path.isdir(src_dir):
            raise Exception(f'{src_dir} directory not exist!')

        file_list = os.listdir(src_dir)
        if len(file_list) <= 0:
            raise Exception(f'{src_dir} directory is empty!')

        # example: ossutil cp F:\apk\pyqx\1.0.6\channel_to_upload oss://txxyapk/pyqx/ -r -f
        # cmd_str = f'ossutil cp {} {} -r -f'
        cmd_str = f'ossutil cp {src_dir} {dst_path} -r -f'
        cp = subprocess.run(cmd_str, check=True, shell=True)
        if cp.returncode != 0:
            raise Exception(f'cmd_str: {cmd_str}. returncode: {cp.returncode}!')
    
    # 单独上传一份官方包，便于配置升级
    def upload_official_file(self):
        apk_file_path = self._get_official_file_path()
        bucket_path = self._get_official_bucket_path()
        self.upload_file(apk_file_path, bucket_path)

    def upload_file(self, src_file, dst_path):
        if not os.path.isfile(src_file):
            raise Exception(f'{src_file} not exist!')

        # example: ossutil cp F:\apk\pyqx\1.0.6\channel_to_upload\pycredit.apk oss://txxyapk/pyqx/ -f
        # cmd_str = f'ossutil cp {} {} -f'
        cmd_str = f'ossutil cp {src_file} {dst_path} -f'
        cp = subprocess.run(cmd_str, check=True, shell=True)
        if cp.returncode != 0:
            raise Exception(f'cmd_str: {cmd_str}. returncode: {cp.returncode}!')

    def get_zip_uploaded_list(self):
        tag = ConfigLabel.ZIP_FLAG
        apk_tag_path = self._get_src_path(tag)
        bucket_path = self._get_bucket_path(tag)
        bucket = self.upload_config[ConfigLabel.BUCKET_FLAG]
        domain = self.upload_config[ConfigLabel.DOMAIN_FLAG]
        domain_path = bucket_path.replace(bucket, domain)
        result = list()
        file_list = os.listdir(apk_tag_path)
        for filename in file_list:
            if filename.endswith('.zip'):
                temp_file_path = os.path.join(apk_tag_path, filename)
                if os.path.isfile(temp_file_path):
                    domain_file_path = domain_path + filename
                    result.append(domain_file_path)

        return result
        
    def get_official_addr(self):
        bucket_path = self._get_official_bucket_path()
        bucket = self.upload_config[ConfigLabel.BUCKET_FLAG]
        domain = self.upload_config[ConfigLabel.DOMAIN_FLAG]
        domain_path = bucket_path.replace(bucket, domain)
        return domain_path


class Notifier:
    def __init__(self, work_path, app_code, ver_name):
        self.work_path = os.path.abspath(work_path)
        self.app_code = app_code
        self.ver_name = ver_name
        self.sender = None
        self.common_config = None
        self.sender_config = None
        self.upgrade_receiver = None
        self.publish_receiver = None

        self._init_config()

    def _parse_base_config(self):
        # 解析common配置
        config_dirs = ['config', 'common.xml']
        config_path = os.sep.join(config_dirs)
        common_config_path = os.path.join(self.work_path, config_path)
        self.common_config = ConfigParser.parse_config(common_config_path)

        # 解析邮件发送者信息的配置
        config_dirs = ['config', 'sender_config.xml']
        config_path = os.sep.join(config_dirs)
        sender_config_path = os.path.join(self.work_path, config_path)
        self.sender_config = ConfigParser.parse_config(sender_config_path)

        # 解析发送给配置升级人员的配置
        config_dirs = ['config', 'upgrade_receiver.xml']
        config_path = os.sep.join(config_dirs)
        upgrade_receiver_path = os.path.join(self.work_path, config_path)
        self.upgrade_receiver = ConfigParser.parse_config(upgrade_receiver_path)

        # 解析发送给运营人员的相关配置
        config_dirs = ['config', 'publish_receiver.xml']
        config_path = os.sep.join(config_dirs)
        publish_receiver_path = os.path.join(self.work_path, config_path)
        self.publish_receiver = ConfigParser.parse_config(publish_receiver_path)

    def _init_sender(self):
        mail_host = self.sender_config[ConfigLabel.HOST_FLAG]
        mail_port = self.sender_config[ConfigLabel.PORT_FLAG]
        mail_sender = self.sender_config[ConfigLabel.EMAIL_FLAG]
        mail_name = self.sender_config[ConfigLabel.NAME_FLAG]
        mail_passwd = self.sender_config[ConfigLabel.PASSWD_FLAG]
        self.sender = mail_util.SenderProcess(mail_host, mail_sender, mail_passwd, port=mail_port, name=mail_name)

    def _init_config(self):
        self._parse_base_config()
        self._init_sender()

    def parse_receiver(self, config_data):
        if not config_data:
            raise Exception('config_data is empty!')

        if ConfigLabel.RECEIVER_FLAG not in config_data:
            raise Exception('receiver not exists in config_data!')

        receivers = list()
        receiver_obj = config_data[ConfigLabel.RECEIVER_FLAG]
        if isinstance(receiver_obj, list):
            receivers.extend(receiver_obj)
        else:
            receivers.append(receiver_obj)

        ccs = list()
        if ConfigLabel.CC_FLAG in config_data:
            cc_obj = config_data[ConfigLabel.CC_FLAG]
            if isinstance(cc_obj, list):
                ccs.extend(cc_obj)
            else:
                ccs.append(cc_obj)

        return receivers, ccs

    def send_dingtalk_message(self, config, info):
        webhook = config[ConfigLabel.WEBHOOK_FLAG]
        secret = config[ConfigLabel.SECRET_FLAG]
        mobile_obj = None
        if ConfigLabel.AT_FLAG in config:
            if ConfigLabel.MOBILE_FLAG in config[ConfigLabel.AT_FLAG]:
                mobile_obj = config[ConfigLabel.AT_FLAG][ConfigLabel.MOBILE_FLAG]

        mobiles = list()
        if mobile_obj:
            if isinstance(mobile_obj, list):
                mobiles.extend(mobile_obj)
            else:
                mobiles.append(mobile_obj)

        data = {
            'msgtype': 'text', 
            'text': {
                'content': info
            }, 
            'at': {
                'atMobiles': mobiles,
                'isAtAll': False
            }
        }
        rtn = dingtalk_util.send_map_data(webhook, secret, data)
        print(rtn.text)


    # 通知测试人员配置升级
    def notify_to_upgrade(self, addr):
        # 发送邮件通知
        app_name = self.common_config[ConfigLabel.NAME_FLAG][self.app_code]
        subject = f'{app_name} {self.ver_name}可以配置升级了'
        content = f'''您好：
          {app_name} {self.ver_name}相关的渠道包已经上传到阿里云，请配置{app_name}的升级，apk包下载链接如下：
        {addr}

        '''
        receivers, ccs = self.parse_receiver(self.upgrade_receiver[ConfigLabel.MAIL_FLAG])
        self.sender.send_mail(subject, content, receivers, ccs=ccs)

        # 发送钉钉群通知
        info = f'{app_name} {self.ver_name}相关的渠道包已经上传到阿里云，请配置{app_name}的升级，apk包下载链接如下：{addr}'
        self.send_dingtalk_message(self.upgrade_receiver[ConfigLabel.DINGTALK_FLAG], info)
    
    # 通知运营人员在各大应用市场发布渠道包
    def notify_to_publish(self, addr_list):
        # 发送邮件通知
        app_name = self.common_config[ConfigLabel.NAME_FLAG][self.app_code]
        # target_list = map(lambda x: ' '*4 + x, addr_list)
        target_str = '\r\n'.join(addr_list)
        subject = f'{app_name} {self.ver_name}可以上传到应用市场了'
        content = f'''您好：
          {app_name} {self.ver_name}相关的渠道包已经上传到阿里云，请在各应用市场上架{app_name}的新版本，apk渠道压缩包下载链接如下：
        {target_str}

        '''
        receivers, ccs = self.parse_receiver(self.publish_receiver[ConfigLabel.MAIL_FLAG])
        self.sender.send_mail(subject, content, receivers, ccs=ccs)

        # 发送钉钉群通知
        info = f'{app_name} {self.ver_name}相关的渠道包已经上传到阿里云，请在各应用市场上架{app_name}的新版本，apk渠道压缩包下载链接如下：{target_str}'
        self.send_dingtalk_message(self.publish_receiver[ConfigLabel.DINGTALK_FLAG], info)


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
            generator = Generator(self.work_path, self.app_code, self.ver_name)
            generator.process()

        # 上传渠道包、渠道压缩包至阿里云
        uploader = Uploader(self.work_path, self.app_code, self.ver_name)
        if self.to_upload:
            uploader.process()

        # 发邮件通知相关人员配置官网升级
        notifier = Notifier(self.work_path, self.app_code, self.ver_name)
        if self.to_update_official:
            addr = uploader.get_official_addr()
            notifier.notify_to_upgrade(addr)

        # 发邮件通知相关人员上架到各应用市场
        if self.to_notify:
            addr_list = uploader.get_zip_uploaded_list()
            notifier.notify_to_publish(addr_list)


def main(args):
    manager = Manager(args)
    manager.process()


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='to release apk.')
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
    
    # 是否进行发送官网升级包的操作
    parser.add_argument('--official', dest='to_update_official', action='store_true', default=False, help='indicate to update official apk')
    
    # 是否发邮件通知给相关人员配置升级
    parser.add_argument('--notify', dest='to_notify', action='store_true', default=False,
                        help='indicate to notify relevant personnel to publish app in application market')

    #     parser.print_help()

    return parser.parse_args(src_args)


if __name__ == '__main__':
    test_args = None
    args = get_args(test_args)
    util.measure_time(main, args)