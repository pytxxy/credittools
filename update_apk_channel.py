# -*- coding:UTF-8 -*-

"""
Created on 2015年11月19日

@author: caifh
"""

import argparse
import os
import subprocess

import creditutils.file_util as file_util


def update_channel(src_file, dst_file, channel):
    _CMD_FORMAT = 'walle.bat put -c {} {} {}'
    if os.path.isfile(src_file):
        if os.path.isfile(dst_file):
            os.remove(dst_file)

        to_run_cmd = _CMD_FORMAT.format(channel, src_file, dst_file)
        subprocess.run(to_run_cmd, shell=True, check=True, universal_newlines=True)
    else:
        info = f'{src_file} not exists!'
        raise Exception(info)


def batch_update_channel(src_path, dst_dir, config_file):
    if os.path.isfile(src_path):
        # apk_items = apk_util.get_apk_info(src_path)
        if os.path.isfile(config_file):
            # 先进行批量处理
            _CMD_FORMAT = 'walle.bat batch -f {} {} {}'
            to_run_cmd = _CMD_FORMAT.format(config_file, src_path, dst_dir)
            subprocess.run(to_run_cmd, shell=True, check=True, universal_newlines=True)

            # 读取全部渠道信息
            parser = ConfigParser(config_file)
            parser.parse()
            channels = parser.get_config()

            # 进行重命名操作
            src_name = os.path.basename(src_path)
            for item in channels:
                src_item_path = os.path.join(dst_dir, get_middle_name(src_name, '_' + item))
                # 输出名称直接使用渠道名称
                dst_item_path = os.path.join(dst_dir, item + '.apk')
                if os.path.isfile(dst_item_path):
                    os.remove(dst_item_path)

                os.rename(src_item_path, dst_item_path)
        else:
            info = f'{config_file} not exists!'
            raise Exception(info)
    else:
        info = f'{src_path} not exists!'
        raise Exception(info)


# 负责渠道列表的解析
class ConfigParser:
    COMMENT_FLAG = '#'

    def __init__(self, config_path):
        self.config_path = config_path
        self._data = list()

    def parse(self):
        data_list = file_util.read_file_lines(self.config_path)
        for item in data_list:
            if item:
                value = item.strip()
                if value and not value.startswith(ConfigParser.COMMENT_FLAG):
                    self._data.append(value)

    def get_config(self):
        return self._data


def get_middle_name(src_name, suffix=None):
    if not suffix:
        suffix = '_middle4temp'

    filename, extension = os.path.splitext(src_name)
    return filename + suffix + extension


def get_middle_path(src_path, suffix=None):
    file_path, filename = os.path.split(src_path)
    return os.path.join(file_path, get_middle_name(filename, suffix))


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='update channel info.')
    parser.add_argument('src', metavar='src', help='the source file to be updated channel info')
    parser.add_argument('dst', metavar='dst', help='the destine file to write')
    parser.add_argument('channel', metavar='channel', help='channel info')
    parser.add_argument('-b', dest='is_batch', action='store_true', default=False,
                        help='indicate the channel value is a channel configure file')

    #     parser.print_help()

    return parser.parse_args(src_args)


def main(args):
    src = os.path.abspath(args.src)
    dst = os.path.abspath(args.dst)
    if os.path.exists(src):
        if not args.is_batch:
            channel = args.channel
            if not os.path.isfile(channel):
                update_channel(src, dst, channel)
            else:
                info = f'{channel} is a configure file, not a channel flag!'
                raise Exception(info)
        else:
            config_file = args.channel
            batch_update_channel(src, dst, config_file)
    else:
        info = f'{src} not exists!'
        raise Exception(info)


if __name__ == '__main__':
    in_args = get_args()
    main(in_args)

    print('to the end')
