# -*- coding:UTF-8 -*-

'''
Created on 2015年11月19日

@author: caifh
'''
import zipfile
import argparse
import os
import tempfile

import creditutils.file_util as myfile
import creditutils.apk_util as apk
import xmltodict

def update_channel(src_apk_path, channel):
    if os.path.exists(src_apk_path):
        zipped = zipfile.ZipFile(src_apk_path, 'a', zipfile.ZIP_DEFLATED) 
        empty_channel_file = "META-INF/pychannel_{channel}".format(channel=channel)
        my_temp_file = tempfile.gettempdir() + os.sep + "channel"
        fd = open(my_temp_file, "w")
        fd.close()
        zipped.write(my_temp_file, empty_channel_file)
        zipped.close()
    else:
        info = '{} not exists'.format(src_apk_path)
        print(info)

def update_upgrade(src_apk_path, upgrade):
    if os.path.exists(src_apk_path):
        zipped = zipfile.ZipFile(src_apk_path, 'a', zipfile.ZIP_DEFLATED) 
        empty_upgrade_file = "META-INF/pyupgrade_{upgrade}".format(upgrade=upgrade)
        my_temp_file = tempfile.gettempdir() + os.sep + "upgrade"
        fd = open(my_temp_file, "w")
        fd.close()
        zipped.write(my_temp_file, empty_upgrade_file)
        zipped.close()
    else:
        info = '{} not exists'.format(src_apk_path)
        print(info)

def batch_update_channel(src_apk_path, dst_apk_dir, config_file, target_name=None):
    if os.path.exists(src_apk_path):
        apk_items = apk.get_apk_info(src_apk_path)
        if os.path.exists(config_file):
            parser = ConfigParser(config_file)
            parser.parse()
            channel_config = parser.get_config()
#             pprint.pprint(channel_config)
#             if not target_name:
#                 target_name = os.path.basename(src_apk_path)
                 
            for item in channel_config:
                if not target_name:
                    name_parts = []
                    name_parts.append(apk_items['label'])
                    name_parts.append(apk_items['versionCode'])
                    name_parts.append(item[ConfigParser.NAME_FLAG])
                    item_target_name = '_'.join(name_parts) + '.apk'
                    
                    # 公众监督打包专用配置
#                     name_parts.append('gzjd')
#                     name_parts.append(apk_items['versionCode'])
#                     name_parts.append(item[ConfigParser.VALUE_FLAG])
#                     item_target_name = '_'.join(name_parts) + '.apk'
                else:
                    item_target_name = target_name
                    
#                 dst_apk_path = dst_apk_dir + os.sep + item[ConfigParser.NAME_FLAG] + os.sep + item_target_name
                # 输出名称直接使用渠道名称
                dst_apk_path = dst_apk_dir + os.sep + item[ConfigParser.VALUE_FLAG] + '.apk'
                myfile.replace_file(src_apk_path, dst_apk_path)
                update_channel(dst_apk_path, item[ConfigParser.VALUE_FLAG])
        else:
            info = '{} not exists'.format(config_file)
            print(info)
    else:
        info = '{} not exists'.format(src_apk_path)
        print(info)

'''负责整体性输入的解析'''
class ConfigParser:
    CHANNEL_FLAG = 'channel'
    ITEM_FLAG = 'item'
    NAME_FLAG = 'name'
    VALUE_FLAG = 'value'
    UPGRADE_FLAG = 'upgrade'

    def __init__(self, config_path):
        self.config_path = config_path
        
    def parse(self):
        doc = xmltodict.parse(myfile.read_file_content(self.config_path))
#         self._data = doc[ConfigParser.CHANNEL_FLAG]
        self._data = doc[ConfigParser.CHANNEL_FLAG][ConfigParser.ITEM_FLAG]
        
    def get_config(self):
        return self._data

# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='update channel info.')
    parser.add_argument('src', metavar='src', help='the source file to be updated channel info')
    parser.add_argument('dst', metavar='dst', help='the destine file to write')
    parser.add_argument('channel', metavar='channel', help='channel info')
    parser.add_argument('-b', dest='is_batch', action='store_true', default=False, help='indicate the channel value is a channel configure file')
    parser.add_argument('-n', dest='name', default=None, help='indicate the target apk name')
    
#     parser.print_help()

    return parser.parse_args(src_args)    

def main(args):
    src = os.path.abspath(args.src)
    dst = os.path.abspath(args.dst)
    if os.path.exists(src):
        if not args.is_batch:
            channel = args.channel
            if not os.path.exists(os.path.abspath(channel)):
                myfile.replace_file(src, dst)
                update_channel(dst, channel)
            else:
                info = '{} is a configure file!'.format(channel)
                print(info)
        else:
            config_file = args.channel
            batch_update_channel(src, dst, config_file, args.name)
    else:
        info = '{} not exists'.format(src)
        print(info)
        
if __name__ == '__main__':
    args = get_args()
    main(args)
    
    print('to the end')