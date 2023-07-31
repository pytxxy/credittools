#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: lishijie
# @Date:   2015-08-17 15:37:54
# @Last Modified by:   lishijie
# @Last Modified time: 2015-08-19 10:27:25
import hmac
from hashlib import sha1
import pycurl
import io
import time
import os
import sys
import json
import argparse
import creditutils.str_util as str_utils
import creditutils.trivial_util as util

PROTECTED_SUFFIX = '_sec'
REQUEST_SUCCESS = 0


class Flag:
    api_key = 'api_key'
    sign = 'sign'
    username = 'username'
    policy_id = 'policy_id'
    upload_type = 'upload_type'
    apk_file = 'apk_file'
    channel_file = 'channel_file'
    apkinfo_id = 'apkinfo_id'
    download_type = 'download_type'

    info = 'info'
    code = 'code'
    msg = 'msg'

    id = 'id'
    apk_name = 'apk_name'
    apk_size = 'apk_size'
    package_name = 'package_name'
    src_apk_md5 = 'src_apk_md5'
    status_code = 'status_code'
    version = 'version'


class Status:
    dispatching = 1001
    pending = 9001
    processing = 9002
    failed = 9008
    success = 9009


def hmac_hash(src, key, sha1_func=sha1):
    hash_obj = hmac.new(key.encode(), src.encode(), sha1_func)
    return hash_obj.hexdigest()


class ProtectManager:
    def __init__(self, args):
        # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)

        self.wait_interval = 5

        if not os.path.isfile(self.src_path):
            ex_info = 'The source {} is not a file!'.format(self.src_path)
            raise Exception(ex_info)

        # set default dst_path
        if not self.dst_path:
            self.dst_path = os.path.dirname(self.src_path)

        self.upload_info = None
        self.target_path = None

    def send_post(self, api, params, signature):
        # 创建一个同 libcurl 中的CURL处理器相对应的Curl对象
        c = pycurl.Curl()
        string_io = io.BytesIO()
        c.setopt(pycurl.WRITEFUNCTION, string_io.write)
        c.setopt(pycurl.FOLLOWLOCATION, 1)
        c.setopt(pycurl.MAXREDIRS, 5)
        c.setopt(pycurl.CONNECTTIMEOUT, 60)
        c.setopt(pycurl.TIMEOUT, 300)
        c.setopt(pycurl.POST, 1)
        # 设置要访问的网址
        c.setopt(pycurl.URL, 'http://{}:8000{}'.format(self.ip, api))
        # 设置请求header
        headers = [Flag.api_key + ':' + self.api_key,
                   Flag.sign + ':' + signature
                   ]

        c.setopt(pycurl.HTTPHEADER, headers)
        # 设置post请求，上传文件的字段名，上传的文件
        c.setopt(c.HTTPPOST, params)
        # 执行上述访问网址的操作
        c.perform()
        # Curl对象无操作时，也会自动执行close操作
        c.close()

        # 读取IO返回值
        return string_io.getvalue()

    def process(self):
        id_ = self._upload_file(self.src_path, self.channel_file)
        if id_:
            print('The apk id is {}.'.format(id_))
            is_success = self._find_state(id_)
            if is_success:
                return self.target_path
            else:
                sys.exit(2)
        else:
            raise Exception('Upload file {} failed!'.format(self.src_path))

    def _upload_file(self, file_path, channel_file=None):
        if not os.path.exists(file_path):
            raise Exception('The file does not exist!'.format(file_path))

        filename = os.path.basename(file_path)
        upload_type = '2'
        to_sign = self.api_key + self.policy_id + upload_type + self.user_name
        signature = hmac_hash(to_sign, self.api_secret)

        params = [
            (Flag.username, (pycurl.FORM_CONTENTS, self.user_name)),
            (Flag.policy_id, (pycurl.FORM_CONTENTS, self.policy_id)),
            (Flag.upload_type, (pycurl.FORM_CONTENTS, upload_type)),
            (Flag.apk_file, (pycurl.FORM_FILE, file_path, pycurl.FORM_FILENAME, filename))
        ]

        if channel_file and os.path.isfile(channel_file):
            params.append((Flag.channel_file, (pycurl.FORM_FILE, file_path, pycurl.FORM_FILENAME, channel_file)))

        api_url = '/webbox/v5/protect/upload'

        print('Start uploading file {}.'.format(file_path))
        print('params: {}'.format(str(params)))

        retry_time = 4  # 出错之后重试的次数
        cnt = 0
        while True:
            try:
                response = self.send_post(api_url, params, signature)
                result = json.loads(str_utils.decode_to_unicode(response))
                break
            except json.decoder.JSONDecodeError:
                print(response)
                cnt += 1
                if cnt > retry_time:
                    print('retry {} times to upload file failed!'.format(retry_time))
                    raise

                print('retry to upload file to protect {} time!'.format(cnt))
                time.sleep(self.wait_interval)  # 先等一段时间

        code = result[Flag.code]
        msg = result[Flag.msg]
        if code != REQUEST_SUCCESS:
            print('Upload {} failed! Error: {}'.format(file_path, msg))
            return None

        info = result[Flag.info]
        id_ = info[Flag.id]
        self.upload_info = info
        print('Upload {} success.'.format(file_path))

        return id_

    def _find_state(self, id_):
        id_str = str(id_)
        to_sign = self.api_key + id_str + self.user_name
        signature = hmac_hash(to_sign, self.api_secret)

        params = [
            (Flag.username, (pycurl.FORM_CONTENTS, self.user_name)),
            (Flag.apkinfo_id, (pycurl.FORM_CONTENTS, id_str))
        ]

        api_url = '/webbox/v5/protect/get_state'

        # print('Start protecting file.')

        retry_time = 4
        cnt = 0
        while True:
            response = self.send_post(api_url, params, signature)
            try:
                result = json.loads(str_utils.decode_to_unicode(response))
                # print('info: {}'.format(info))

                code = result[Flag.code]
                msg = result[Flag.msg]
                if code != REQUEST_SUCCESS:
                    print('Get state with id {} failed! Error: {}'.format(self.upload_infos, msg))
                    return False

                info = result[Flag.info]
                status = info[Flag.status_code]
                if status == Status.success:
                    self.target_path = self._download_file(self.dst_path, id_)
                elif status == Status.failed:
                    return False
                elif status == Status.dispatching:
                    print('It is in dispatching ...')
                elif status == Status.pending:
                    print('It is pending ...')
                elif status == Status.processing:
                    print('It is in processing ...')
                else:
                    raise Exception('Unknown status {}!'.format(status))
            except json.decoder.JSONDecodeError:
                print(response)
                cnt += 1
                if cnt > retry_time:
                    print('retry {} times to get download info failed!'.format(retry_time))
                    raise

                print('retry to get download info {} time!'.format(cnt))

            if self.target_path:
                return True

            time.sleep(self.wait_interval)

        return False

    def _download_file(self, dst_path, apkinfo_id, name_pre=None):
        if not os.path.exists(dst_path):
            os.makedirs(dst_path)
            print('Create destination path {} first.'.format(dst_path))

        id_str = str(apkinfo_id)
        download_type = '1'
        to_sign = self.api_key + id_str + download_type
        signature = hmac_hash(to_sign, self.api_secret)

        params = [
            (Flag.apkinfo_id, (pycurl.FORM_CONTENTS, id_str)),
            (Flag.download_type, (pycurl.FORM_CONTENTS, download_type))
        ]

        print('Start downloading file.')

        api_url = '/webbox/v5/protect/download'
        response = self.send_post(api_url, params, signature)
        if not name_pre:
            name_pre = os.path.splitext(os.path.basename(self.src_path))[0]

        dst_filename = name_pre + PROTECTED_SUFFIX + '.apk'
        dst_file_path = os.path.join(dst_path, dst_filename)
        file_obj = open(dst_file_path, 'wb')
        file_obj.write(response)
        file_obj.close()

        print('Download file to {} success!'.format(dst_file_path))

        return dst_file_path


def get_default_protected_path(src_path):
    first_part, ext_part = os.path.splitext(src_path)
    return first_part + PROTECTED_SUFFIX + ext_part


def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='Protect android application.')
    parser.add_argument('-i', '--ip', action='store', dest='ip', help='protect server ip address')
    parser.add_argument('-u', '--username', action='store', dest='user_name', help='user name')
    parser.add_argument('-k', '--api_key', action='store', dest='api_key', help='api key')
    parser.add_argument('-s', '--api_secret', action='store', dest='api_secret', help='api secret')
    parser.add_argument('-p', '--policy_id', action='store', dest='policy_id', default='2', help='policy id')
    parser.add_argument('-d', '--download', action='store', dest='dst_path',
                        help='the path to store the downloading file')
    parser.add_argument('-c', '--channel_file', action='store', dest='channel_file', help='channel file')
    parser.add_argument('src_path', metavar='src_path', help='the source path to protect')
    return parser.parse_args(src_args)


def main(args):
    ip = args.ip
    user_name = args.user_name
    api_key = args.api_key
    api_secret = args.api_secret

    args.src_path = os.path.abspath(args.src_path)

    if args.dst_path:
        args.dst_path = os.path.abspath(args.dst_path)

    if args.channel_file:
        args.channel_file = os.path.abspath(args.channel_file)

    if ip and user_name and api_key and api_secret:
        manager = ProtectManager(args)
        return manager.process()
    else:
        print('Please input -h or --help to read command help.')
        if not ip:
            print('Please specify ip address.')

        if not user_name:
            print('Please specify user name.')

        if not api_key:
            print('Please specify api key.')

        if not api_secret:
            print('Please specify api secret.')

        sys.exit(1)


def protect(ip, user_name, key, secret, file_path, dst_path=None):
    if dst_path:
        dst_path_info = ' -d {} '.format(dst_path)
    else:
        dst_path_info = ''

    src_args = '-i {} -u {} -k {} -s {} {}{}'.format(ip, user_name, key, secret, dst_path_info, file_path)
    print(f'src_args: {src_args}')
    args = get_args(src_args.split())
    return main(args)


if __name__ == '__main__':
    test_args = '-i 192.168.20.171 -u pyzx -k a5070c3c-a22f-4ef3-8867-1577c9936c68 -s c6fbb982-343e-4c6c-8260-93c140b7c620 /data/android/auto_build/app/output/txxy/dev/20230706_095720/6.2.17beta_d_03-1041-20230706.apk'.split()
    # test_args = None
    in_args = get_args(test_args)
    util.measure_time(main, in_args)
