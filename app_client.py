import os
import sys
import threading
import time
import json
import rpyc
import argparse
import xmltodict
import creditutils.str_util as str_utils
import creditutils.file_util as file_util
import creditutils.trivial_util as trivial_util
import creditutils.dingtalk_util as dingtalk_util
from app_controller import CODE_FAILED, CODE_SUCCESS, DEFAULT_REQUEST_TIMEOUT

class ConfigLabel:
    ROOT_FLAG = 'config'
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

class Notifier:
    def __init__(self, work_path):
        self.work_path = os.path.abspath(work_path)
        self.dingtalk_receiver = None
        self._parse_base_config()

    def _parse_base_config(self):
        # 解析发送给配置升级人员的配置
        config_dirs = ['config/base', 'dingtalk_receiver.xml']
        config_path = os.sep.join(config_dirs)
        dingtalk_receiver_path = os.path.join(self.work_path, config_path)
        self.dingtalk_receiver = ConfigParser.parse_config(dingtalk_receiver_path)

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
            'msgtype': 'markdown', 
            'markdown': info,
            'at': {
                'atMobiles': mobiles,
                'isAtAll': False
            }
        }
        rtn = dingtalk_util.send_map_data(webhook, secret, data)
        print(f'dingtalk: {rtn.text}')

    # 通知测试人员配置升级
    def notify_to_dingtalk(self, info):
        # 发送钉钉群通知
        self.send_dingtalk_message(self.dingtalk_receiver[ConfigLabel.DINGTALK_FLAG], info)
 

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
        codes = self.app_codes.split(',')
        envs = self.ver_envs.split(',')
        nos = json.loads(self.ver_nos)
        names = json.loads(self.ver_names)
        vcodes = json.loads(self.ver_codes)
        api_vers = None
        if self.api_vers is not None:
            api_vers = json.loads(self.api_vers)

        for ev in envs:
            for c in codes:
                dt = dict(self.data)
                dt['ver_env'] = ev                
                print(f'正在打{c}的{ev}环境的包...')
                dt['app_code'] = c
                if c in names.keys():
                    dt['ver_name'] = names.get(c)
                if c in vcodes.keys():
                    dt['ver_code'] = vcodes.get(c)
                if c in nos.keys():
                    dt['ver_no'] = nos.get(c)
                if api_vers is not None and c in api_vers.keys():
                    dt['api_ver'] = api_vers.get(c)
                thread = threading.Thread(target=self.connect_with_name, args=(dt,))
                thread.start()

    # 连接控制中心服务，分派指定打包机来打包
    def connect_with_name(self, dt):
        conn = None
        begin = time.time()
        try:
            conn = rpyc.connect_by_service('central_control', config={'sync_request_timeout': DEFAULT_REQUEST_TIMEOUT})
            print(f'connected {conn.root.get_service_name().lower()} then wait for processing...')
            result = conn.root.process(dt)
        except:
            result = {'code': CODE_FAILED, 'msg': f'errors in app_client: {sys.exc_info()}'}
        print(result)
        
        # 计算打包耗时
        end = time.time()
        cost_time = str_utils.get_time_info(begin, end)

        # 组合通知信息
        notify_info = [
            f'# [{self.job_name}]({self.job_url})',
            f'> 任务: **[{self.job_build_name}]({self.job_build_url})**',
            f'> 应用: **{dt["app_code"]}**',
            f'> 分支: **{self.branch}**',
            f'> 环境: **{dt["ver_env"]}**',
            f'> 版本: **{dt["ver_name"]}({dt["ver_code"]})**',
            f'> 转测: **{dt["ver_no"]}**',
            f'> 渠道: **{self.channel}**',
            f'> 耗时: **{cost_time}**',
        ]
        if result['code'] == CODE_SUCCESS:
            notify_info.append(f'> 状态: **成功**',)
        else:
            notify_info.append(f'> 状态: **失败**',)
            notify_info.append(f'> 原因: **{result["msg"]}**')
        if result['host'] is not None:
            notify_info.append(f'> 来源: **{result["host"]}**',)

        # 组合通知信息并发送
        notifier = Notifier(self.work_path)
        notifier.notify_to_dingtalk({
            'title': f'{self.job_name}',
            'text': '\n\n'.join(notify_info)
        })


def main(args):
    AppClient(args).process()


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='update code if need, build if need.')
    parser.add_argument('-u', dest='to_update', action='store_true', default=False, help='indicate to get or update code firstly')
    parser.add_argument('-b', dest='to_build', action='store_true', default=False, help='indicate to build')
    parser.add_argument('-v', metavar='code_ver', dest='code_ver', action='store', default=None, help='indicate updating to special version')
    parser.add_argument('-d', dest='is_debug', action='store_true', default=False, help='indicate to build debug version')

    # 新增复合参数，用来做遍历
    parser.add_argument('--job_name', metavar='job_name', dest='job_name', default='android_app', help='job name')
    parser.add_argument('--job_url', metavar='job_url', dest='job_url', default='', help='job url')
    parser.add_argument('--job_build_name', metavar='job_build_name', dest='job_build_name', default='', help='job build display name')
    parser.add_argument('--job_build_url', metavar='job_build_url', dest='job_build_url', default='', help='job build url')
    parser.add_argument('--work_path', metavar='work_path', dest='work_path', default='/data/android/auto_build/app', help='working directory')
    parser.add_argument('--appcodes', metavar='app_codes', dest='app_codes', type=str, help='app codes such as txxy,xycx,pyqx,pyzx')
    parser.add_argument('--verenvs', metavar='ver_envs', dest='ver_envs', type=str, help='ver envs such as test,dev,pre,pregray,gray,prod')
    parser.add_argument('--vernames', metavar='ver_names', dest='ver_names', type=str, help='version names')
    parser.add_argument('--vercodes', metavar='ver_codes', dest='ver_codes', type=str, help='version codes')
    parser.add_argument('--vernos', metavar='ver_nos', dest='ver_nos', type=str, help='version release number')
    parser.add_argument('--apivers', metavar='api_vers', dest='api_vers', type=str, help='network api version number')

    parser.add_argument('--vername', metavar='ver_name', dest='ver_name', default='1.0.0', help='version name')
    parser.add_argument('--vercode', metavar='ver_code', dest='ver_code', type=int, default=0, help='version code')
    parser.add_argument('--verno', metavar='ver_no', dest='ver_no', type=int, default=0, help='version release number')
    parser.add_argument('--verenv', metavar='ver_env', dest='ver_env', type=str, default='test', choices=['dev', 'test', 'test2', 'pre', 'pregray', 'gray', 'pro'], 
                        help='dev: develop environment; test: test environment; test2: test2 environment; '
                             'pre: pre-release environment; pregray: pre-gray-release environment; '
                             'gray: gray-release environment;  pro: production environment;')

    parser.add_argument('--apiver', metavar='api_ver', dest='api_ver', type=str, default='', help='network api version number')
    parser.add_argument('--appcode', metavar='app_code', dest='app_code', type=str, default='txxy', choices=['txxy', 'xycx', 'pyqx', 'pyzx', 'ljh'], 
                        help='txxy: tian xia xin yong; xycx: xin yong cha xun; pyqx: peng you qi xin; pyzx: peng yuan zheng xin; ljh: la jiao hong;')
    parser.add_argument('--appname', metavar='app_name', dest='app_name', default='@string/app_name', help='application name')

    parser.add_argument('--test', dest='is_test', action='store_true', default=False, help='indicate just to test config')
    parser.add_argument('--align', dest='to_align', action='store_true', default=True, help='indicate to align apk file after protected')
    parser.add_argument('--upload', dest='to_upload', action='store_true', default=False, help='indicate to upload build files')
    parser.add_argument('--arm64', dest='is_arm64', action='store_true', default=False, help='indicate to build with arm64')
    parser.add_argument('--google', dest='for_google', action='store_true', default=False, help='indicate to build for google play')
    parser.add_argument('--channel', metavar='channel', dest='channel', type=str, default=BuilderLabel.DEFAULT_CHAN, help='application channel')
    parser.add_argument('--demo', metavar='demo_label', dest='demo_label', type=str, default='normal', choices=['normal', 'bridge', 'hotloan', 'mall'], 
                        help='normal: normal entry; bridge: bridge entry; hotloan: hot loan entry;')
    parser.add_argument('--branch', metavar='branch', dest='branch', default='master', help='code branch name')
    parser.add_argument('--jpush', metavar='jpush_appkey', dest='jpush_appkey', default=None, help='jpush app key')

    #     parser.print_help()

    return parser.parse_args(src_args)


if __name__ == '__main__':
    test_args = None
    args = get_args(test_args)
    trivial_util.measure_time(main, args)
