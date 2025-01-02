import threading
import json
import requests
import json
import time
import argparse
import creditutils.trivial_util as trivial_util

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
    
    def check_call_builder(self, data):
        url = '/android/build'
        return self.post_for_body(url, data)


class BuilderLabel:
    DEFAULT_CHAN = 'pycredit'


class AppClient:
    def __init__(self, args) -> None:
        self.data = dict()
        for name, value in vars(args).items():
            setattr(self, name, value)
            self.data[name] = value
    # 处理打包，以环境优先，打各应用包
    def process(self):
        app_codes = self.app_codes.split(',')
        envs = self.ver_envs.split(',')
        ver_nos = json.loads(self.ver_nos)
        ver_names = json.loads(self.ver_names)
        ver_codes = json.loads(self.ver_codes)
        api_vers = None
        if self.api_vers is not None:
            api_vers = json.loads(self.api_vers)

        client = Client.new_client(self.req_name, self.req_passwd, self.req_url)

        # 请求数据样例
        # data = {
        #     'product':'txxy',
        #     'buildMode':'debug',
        #     'env':'pre1',
        #     'appBaseVersion':'6.4.7',
        #     'appReleaseVersion':'01',
        #     'appVersionCode':'1224',
        #     'apiVersion':'42.3',
        #     'channel':'pycredit',
        #     'branch':'develop',
        #     'demoLabel':'normal',
        #     'splashType':'0',
        #     'isForTest':True,
        #     'toAlign':True,
        #     'toUpdateCode':True,
        #     'toNotify':False,
        #     'minifyEnabled':False,
        #     'forGoogle':False,
        #     'toUploadSftp':True,
        #     'toUploadBugly':False,
        #     'releaseDebuggable':False,
        #     'withApiEncrypt':True,
        #     'jobInfo':''
        # }
       
        if self.is_debug:
            buildMode = 'debug'
        else:
            buildMode = 'release'

        for env in envs:
            for app_code in app_codes:
                print(f'正在打{app_code}的{env}环境的包...')
                
                data = {}
                data['product'] = app_code
                data['buildMode'] = buildMode
                data['env'] = env
                
                if app_code in ver_names.keys():
                    data['appBaseVersion'] = ver_names.get(app_code)
                
                if app_code in ver_nos.keys():
                    ver_no = ver_nos.get(app_code)
                    data['appReleaseVersion'] = f'{ver_no:02d}'

                if app_code in ver_codes.keys():
                    data['appVersionCode'] = str(ver_codes.get(app_code))
                
                api_ver = ''
                if api_vers is not None and app_code in api_vers.keys():
                    api_ver = api_vers.get(app_code)
                data['apiVersion'] = api_ver
                data['channel'] = self.channel
                data['branch'] = self.branch
                data['demoLabel'] = self.demo_label
                data['splashType'] = str(self.splash_type)
                data['isForTest'] = self.is_test
                data['toAlign'] = self.to_align
                data['toUpdateCode'] = self.to_update
                data['toNotify'] = self.need_notify
                data['minifyEnabled'] = self.minify_enabled
                data['forGoogle'] = self.for_google
                data['toUploadSftp'] = self.to_upload
                data['toUploadBugly'] = self.to_upload_bugly
                data['releaseDebuggable'] = self.release_debuggable
                data['withApiEncrypt'] = self.with_api_encrypt

                jobInfo = {}
                jobInfo['jobName'] = self.job_name
                jobInfo['jobUrl'] = self.job_url
                jobInfo['jobBuildName'] = self.job_build_name
                jobInfo['jobBuildUrl'] = self.job_build_url
                data['jobInfo'] = json.dumps(jobInfo, ensure_ascii=False)

                thread = threading.Thread(target=self.check_call_builder, args=(client,data))
                thread.start()
    def check_call_builder(self, client, data):
        result = client.check_call_builder(data)
        print(f'call builder got result: {result}')
        return result

def main(args):
    AppClient(args).process()


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='update code if need, build if need.')
    parser.add_argument('-u', dest='to_update', action='store_true', default=False, help='indicate to get or update code firstly')
    parser.add_argument('-d', dest='is_debug', action='store_true', default=False, help='indicate to build debug version')

    # 新增复合参数，用来做遍历
    parser.add_argument('--req_name', metavar='req_name', dest='req_name', default='test', help='request name')
    parser.add_argument('--req_passwd', metavar='req_passwd', dest='req_passwd', default='Test', help='request password')
    parser.add_argument('--req_url', metavar='req_url', dest='req_url', default='http://192.168.20.214:9008/api/flow', help='request url')
    parser.add_argument('--job_name', metavar='job_name', dest='job_name', default='harmony_app', help='job name')
    parser.add_argument('--job_url', metavar='job_url', dest='job_url', default='', help='job url')
    parser.add_argument('--job_build_name', metavar='job_build_name', dest='job_build_name', default='', help='job build display name')
    parser.add_argument('--job_build_url', metavar='job_build_url', dest='job_build_url', default='', help='job build url')
    parser.add_argument('--appcodes', metavar='app_codes', dest='app_codes', type=str, help='app codes such as txxy,xycx,pyqx,pyzx')
    parser.add_argument('--verenvs', metavar='ver_envs', dest='ver_envs', type=str, help='ver envs such as test,dev,pre,pregray,gray,prod')
    parser.add_argument('--vernames', metavar='ver_names', dest='ver_names', type=str, help='version names')
    parser.add_argument('--vercodes', metavar='ver_codes', dest='ver_codes', type=str, help='version codes')
    parser.add_argument('--vernos', metavar='ver_nos', dest='ver_nos', type=str, help='version release number')
    parser.add_argument('--apivers', metavar='api_vers', dest='api_vers', type=str, default=None, help='network api version number')

    parser.add_argument('--test', dest='is_test', action='store_true', default=False, help='indicate just to test config')
    parser.add_argument('--align', dest='to_align', action='store_true', default=True, help='indicate to align apk file after protected')
    parser.add_argument('--upload', dest='to_upload', action='store_true', default=False, help='indicate to upload build files')
    parser.add_argument('--splash_type', dest='splash_type', type=int, default=0, help='indicate to build with splash type')
    parser.add_argument('--google', dest='for_google', action='store_true', default=False, help='indicate to build for google play')
    parser.add_argument('--channel', metavar='channel', dest='channel', type=str, default=BuilderLabel.DEFAULT_CHAN, help='application channel')
    parser.add_argument('--demo', metavar='demo_label', dest='demo_label', type=str, default='normal', choices=['normal', 'bridge', 'hotloan', 'mall'],
                        help='normal: normal entry; bridge: bridge entry; hotloan: hot loan entry;')
    parser.add_argument('--branch', metavar='branch', dest='branch', default='master', help='code branch name')
    parser.add_argument('--minify', dest='minify_enabled', action='store_true', default=False, help='whether to enable code obfuscation or not')
    parser.add_argument('--notify', dest='need_notify', action='store_true', default=False, help='send DingTalk notifiactions')
    parser.add_argument('--upload_bugly', dest='to_upload_bugly', action='store_true', default=True, help='upload bugly symbol files, mapping.txt etc.')
    parser.add_argument('--release_debuggable', dest='release_debuggable', action='store_true', default=False, help='release version can be debuggable or not')
    parser.add_argument('--api_encrypt', dest='with_api_encrypt', action='store_true', default=False, help='api need encrypted or not')

    # parser.print_help()
    return parser.parse_args(src_args)


if __name__ == '__main__':
    test_args = None
    args = get_args(test_args)
    trivial_util.measure_time(main, args)
