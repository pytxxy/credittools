"""
Android Client - Android应用构建客户端

用法：
    # 正常构建模式：使用命令行参数
    python android_client.py --appcodes tchk --verenvs po -u --upload ...

    # 调试测试模式：使用预配置的测试参数
    python android_client.py --test-mode

    # 在Python代码中导入使用
    from android_client import AppClient, TEST_DEBUG_CONFIG
    class Args:
        def __init__(self, args_dict):
            for key, value in args_dict.items():
                setattr(self, key, value)
    app_client = AppClient(Args(TEST_DEBUG_CONFIG))
    result = app_client.test_debug()
"""
import sys
import threading
import json
import requests
import time
import argparse
import creditutils.trivial_util as trivial_util

class Client:
    """
    API客户端类：用于与构建服务器进行HTTP通信
    支持GET、POST、PUT、DELETE等HTTP方法
    """

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


# 测试调试配置：用于开发和调试的默认测试参数
#
# 说明：修改此配置以适应不同的测试场景：
#   - req_url: 构建服务器API地址
#   - app_codes: 要构建的应用代码（逗号分隔）
#   - ver_envs: 构建环境（test, dev, pre, gray, prod等）
#   - branch: 代码分支
#   - 其他构建标志：根据需要开启/关闭
#
# 注意：修改配置后，直接使用 `python android_client.py --test-mode` 即可测试
TEST_DEBUG_CONFIG = {
    'to_update': True,
    'is_debug': False,
    'req_name': 'test',
    'req_passwd': 'Test',
    'req_url': 'http://10.192.2.90:9008/api/flow',
    'job_name': 'android_app',
    'job_url': 'http://jenkins.txxy.com/job/android_app/',
    'job_build_name': '#712',
    'job_build_url': 'http://jenkins.txxy.com/job/android_app/712/',
    'app_codes': 'tchk',
    'ver_envs': 'qa',
    'ver_names': '{"txxy":"7.0.1","xycx":"2.2.19","grbg":"1.1.0","zssfzs":"1.1.0","fxgj":"1.0.5","txys":"1.0.6","txxyzxxxcx":"1.1.0","tiance":"1.4.1","tianxun":"1.2.6","tchk":"1.0.0"}',
    'ver_codes': '{"txxy":1336,"xycx":355,"grbg":34,"zssfzs":26,"fxgj":21,"txys":26,"txxyzxxxcx":22,"tiance":163,"tianxun":100,"tchk":1}',
    'ver_nos': '{"txxy":3,"xycx":1,"grbg":1,"zssfzs":1,"fxgj":1,"txys":1,"txxyzxxxcx":1,"tiance":1,"tianxun":3,"tchk":1}',
    'api_vers': None,
    'is_test': False,
    'to_align': True,
    'to_upload': True,
    'splash_type': 3,
    'with_bundle_format': False,
    'channel': 'tc_hk_gw',
    'demo_label': 'normal',
    'branch': 'develop',
    'minify_enabled': True,
    'need_notify': True,
    'to_upload_bugly': True,
    'release_debuggable': False,
    'with_api_encrypt': True
}


class AppClient:
    """
    Android应用构建客户端：管理应用构建请求和任务调度
    支持多线程并行构建多个应用的不同环境版本
    """

    def __init__(self, args) -> None:
        self.data = dict()
        for name, value in vars(args).items():
            setattr(self, name, value)
            self.data[name] = value

        self.results = {}
        
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

        if self.is_debug:
            buildMode = 'debug'
        else:
            buildMode = 'release'

        threads = []
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
                data['withBundleFormat'] = self.with_bundle_format
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
                print(f'call builder({k}) failed with {result}')
                continue

            if result[tag_code] == success_code_str:
                print(f'call builder({k}) success with {result}')
            else:
                is_success = False
                print(f'call builder({k}) failed with {result}')

        return is_success
            
    def check_call_builder(self, client, data):
        """
        调用构建服务器API并记录结果

        参数:
            client: API客户端实例
            data: 构建请求数据

        返回:
            构建服务器的响应结果
        """
        result = client.check_call_builder(data)
        data_str = json.dumps(data, ensure_ascii=False)
        self.results[data_str] = result

        return result

    def test_debug(self):
        """
        开发和调试测试方法：发送单个构建请求到构建服务器

        该方法使用预配置的测试参数，向构建服务器发送一个完整的构建请求，
        用于验证API调用和参数配置是否正确。

        返回:
            dict: 构建服务器的响应结果
        """
        print("=== 开始android_client调试测试 ===")

        # 创建客户端连接
        client = Client.new_client(TEST_DEBUG_CONFIG['req_name'],
                                   TEST_DEBUG_CONFIG['req_passwd'],
                                   TEST_DEBUG_CONFIG['req_url'])

        print("\n=== 测试构建请求 ===")
        # 构建请求参数
        data = {
            'product': 'tchk',
            'buildMode': 'release' if not TEST_DEBUG_CONFIG['is_debug'] else 'debug',
            'env': 'qa',
            'appBaseVersion': '1.0.0',
            'appReleaseVersion': '01',
            'appVersionCode': '1',
            'apiVersion': '',
            'channel': TEST_DEBUG_CONFIG['channel'],
            'branch': TEST_DEBUG_CONFIG['branch'],
            'demoLabel': TEST_DEBUG_CONFIG['demo_label'],
            'splashType': str(TEST_DEBUG_CONFIG['splash_type']),
            'isForTest': TEST_DEBUG_CONFIG['is_test'],
            'toAlign': TEST_DEBUG_CONFIG['to_align'],
            'toUpdateCode': TEST_DEBUG_CONFIG['to_update'],
            'toNotify': TEST_DEBUG_CONFIG['need_notify'],
            'minifyEnabled': TEST_DEBUG_CONFIG['minify_enabled'],
            'withBundleFormat': TEST_DEBUG_CONFIG['with_bundle_format'],
            'toUploadSftp': TEST_DEBUG_CONFIG['to_upload'],
            'toUploadBugly': TEST_DEBUG_CONFIG['to_upload_bugly'],
            'releaseDebuggable': TEST_DEBUG_CONFIG['release_debuggable'],
            'withApiEncrypt': TEST_DEBUG_CONFIG['with_api_encrypt'],
            'jobInfo': json.dumps({
                'jobName': TEST_DEBUG_CONFIG['job_name'],
                'jobUrl': TEST_DEBUG_CONFIG['job_url'],
                'jobBuildName': TEST_DEBUG_CONFIG['job_build_name'],
                'jobBuildUrl': TEST_DEBUG_CONFIG['job_build_url']
            }, ensure_ascii=False)
        }

        print(f"请求URL: {client.prefix}/android/build")
        print(f"请求数据: {json.dumps(data, ensure_ascii=False, indent=2)}")

        # 发送API调用
        result = client.check_call_builder(data)
        print(f"响应结果: {result}")

        return result

def main(args):
    """
    主函数入口：执行构建流程

    参数:
        args: 命令行参数

    返回:
        bool: 构建是否成功
    """
    return AppClient(args).process()


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    """
    解析命令行参数

    参数:
        src_args: 可选的参数列表（用于测试）

    返回:
        解析后的参数命名空间
    """
    parser = argparse.ArgumentParser(description='update code if need, build if need.')
    parser.add_argument('-u', dest='to_update', action='store_true', default=False, help='indicate to get or update code firstly')
    parser.add_argument('-d', dest='is_debug', action='store_true', default=False, help='indicate to build debug version')

    # 新增复合参数，用来做遍历
    parser.add_argument('--req_name', metavar='req_name', dest='req_name', default='test', help='request name')
    parser.add_argument('--req_passwd', metavar='req_passwd', dest='req_passwd', default='Test', help='request password')
    parser.add_argument('--req_url', metavar='req_url', dest='req_url', default='http://192.168.20.118:9008/api/flow', help='request url')
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
    parser.add_argument('--bundle', dest='with_bundle_format', action='store_true', default=False, help='indicate to build for android app bundle format')
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


# ==================== 程序入口 ====================
if __name__ == '__main__':
    # 检查是否启动测试模式：使用默认测试参数
    if len(sys.argv) > 1 and sys.argv[1] == '--test-mode':
        print("运行测试模式，使用默认调试参数...")

        # 从配置字典创建Args对象
        class Args:
            def __init__(self, args_dict):
                for key, value in args_dict.items():
                    setattr(self, key, value)

        app_client = AppClient(Args(TEST_DEBUG_CONFIG))
        result = app_client.test_debug()
        print(f"\n测试完成。结果: {result}")
    else:
        # 正常模式：使用命令行参数
        args = get_args()
        is_success = trivial_util.measure_time(main, args)
        if not is_success:
            sys.exit(1)
