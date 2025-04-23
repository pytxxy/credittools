'''
调用远程微服务实现下面功能：
1.从ftp服务器上下载原始主包，生成上传用的安装包文件（在生成渠道包过程中，检查当前磁盘上存在的历史渠道版本，只保留最近三次的。）。
2.将生成的安装包上传到阿里云，使用钉钉及邮件方式通知运营同事上架应用市场；
'''
import sys
import argparse
import json
import time
import requests
import threading

import creditutils.trivial_util as trivial_util


'''
进行Harmony应用发布操作。
'''

class Client:
    def __init__(self, username, password, prefix):
        self.username = username
        self.password = password
        self.prefix = prefix
        self.token = None

    def get_for_body(self, url):
        integral_url = self.prefix + url
        headers = {"Token": self.token}
        result = requests.get(integral_url, headers=headers)
        if result.status_code == 200:
            # print(f'text: {result.text}')
            rtn_body = json.loads(result.text)
            return rtn_body
        else:
            print(f"get failed with code({result.status_code}) msg({result.reason})!")
            return None
        
    def put_for_body(self, url, data):
        integral_url = self.prefix + url
        headers = {"Token": self.token}
        result = requests.put(integral_url, json=data, headers=headers)
        if result.status_code == 200:
            # print(f'text: {result.text}')
            rtn_body = json.loads(result.text)
            return rtn_body
        else:
            print(f"put failed with code({result.status_code}) msg({result.reason})!")
            return None
        
    def delete_for_body(self, url, data=None):
        integral_url = self.prefix + url
        headers = {"Token": self.token}
        result = requests.delete(integral_url, json=data, headers=headers)
        if result.status_code == 200:
            # print(f'text: {result.text}')
            rtn_body = json.loads(result.text)
            return rtn_body
        else:
            print(f"delete failed with code({result.status_code}) msg({result.reason})!")
            return None

    def post_for_body(self, url, data):
        integral_url = self.prefix + url
        target_data = {}
        sn = str(int(time.time()*1000))
        # print(f'sn: {sn}')
        target_data['sn'] = sn
        target_data['data'] = data
        # print(f'whole body: {json.dumps(target_data)}')
        result = requests.post(integral_url, json=target_data)
        if result.status_code == 200 or result.status_code == 201:
            # print(f'text: {result.text}')
            rtn_body = json.loads(result.text)
            return rtn_body
        else:
            print(f"post {integral_url} failed with code({result.status_code}) msg({result.reason})!")
            return None

    @staticmethod
    def new_client(username, password, prefix):
        client = Client(username=username, password=password, prefix=prefix)
        return client
    
    def check_call_release(self, data):
        url = '/harmony/release'
        return self.post_for_body(url, data)

class ReleaseClient:
    def __init__(self, args) -> None:
        self.data = dict()
        for name, value in vars(args).items():
            setattr(self, name, value)
            self.data[name] = value

        self.results = {}
    def process(self):
        app_codes = self.app_codes.split(',')
        ver_names = json.loads(self.ver_names)
        client = Client.new_client(self.req_name, self.req_passwd, self.req_url)
        threads = []
        for code in app_codes:
            app_code = code
            if code in ver_names.keys():
                ver_name = ver_names.get(code)
            print(f'正在处理{app_code} {ver_name}版本发布事宜...')
            data = {}
            data['appCode'] = app_code
            data['appVersion'] = ver_name
            data['toDownload'] = self.to_download
            data['toUpload'] = self.to_upload
            data['toNotify'] = self.to_notify
            data['productDesc'] = self.prd_desc

            thread = threading.Thread(target=self.check_call_release, args=(client,data))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        tag_code = 'code'
        success_code_str = '0'
        is_success = True
        for k in self.results:
            result = self.results[k]
            if result == None:
                is_success = False
                continue

            if tag_code not in result:
                is_success = False
                print(f'call release({k}) failed with {result}')
                continue

            if result[tag_code] == success_code_str:
                print(f'call release({k}) success with {result}')
            else:
                is_success = False
                print(f'call release({k}) failed with {result}')

        return is_success
    def check_call_release(self, client, data):
        result = client.check_call_release(data)
        # print(f'call release got result: {result}')
        data_str = json.dumps(data, ensure_ascii=False)
        self.results[data_str] = result

        return result

def main(args):
    return ReleaseClient(args).process()


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='to release app.')

    parser.add_argument('--req_name', metavar='req_name', dest='req_name', default='test', help='request name')
    parser.add_argument('--req_passwd', metavar='req_passwd', dest='req_passwd', default='Test', help='request password')
    parser.add_argument('--req_url', metavar='req_url', dest='req_url', default='http://192.168.20.118:9008/api/flow', help='request url')


    # 应用和版本信息多选及其配置
    parser.add_argument('--vernames', metavar='ver_names', dest='ver_names', type=str, help='version names')
    parser.add_argument('--appcodes', metavar='app_codes', dest='app_codes', type=str, help='app codes such as txxy,xycx,pyqx,pyzx')
    
    # 产品需求开发功能点描述
    parser.add_argument('--prd_desc', metavar='prd_desc', dest='prd_desc', type=str, default="", help='product requirements development description')

    # 是否进行生成渠道包的操作
    parser.add_argument('-d', dest='to_download', action='store_true', default=False, help='indicate to download app file')

    # 是否上传到阿里云
    parser.add_argument('--upload', dest='to_upload', action='store_true', default=False,
                        help='indicate to upload channel files and zipped files')

    # 是否发邮件通知给相关人员配置升级
    parser.add_argument('--notify', dest='to_notify', action='store_true', default=False,
                        help='indicate to notify relevant personnel to publish app in application market')

    #     parser.print_help()

    return parser.parse_args(src_args)


if __name__ == '__main__':
    test_args = None
    args = get_args(test_args)
    is_success = trivial_util.measure_time(main, args)
    if not is_success:
        sys.exit(1)
