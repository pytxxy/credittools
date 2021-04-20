import argparse
import rpyc
import creditutils.trivial_util as trivial_util


def connect_with_name(data):
    conn = rpyc.connect_by_service('central_control')
    result = conn.root.process(data)
    print(f'result: {result}')
    conn.close()


def main(args):
    params = dict()
    for name, value in vars(args).items():
        params[name] = value
    
    connect_with_name(params)


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='update code if need, build if need.')
    parser.add_argument('-u', dest='to_update', action='store_true', default=False,
                        help='indicate to get or update code firstly')
    parser.add_argument('-b', dest='to_build', action='store_true', default=False, help='indicate to build')
    parser.add_argument('-v', metavar='code_ver', dest='code_ver', action='store', default=None,
                        help='indicate updating to special version')
    parser.add_argument('-d', dest='is_debug', action='store_true', default=False,
                        help='indicate to build debug version')

    parser.add_argument('--vername', metavar='ver_name', dest='ver_name', help='version name')
    parser.add_argument('--vercode', metavar='ver_code', dest='ver_code', type=int, help='version code')
    parser.add_argument('--verno', metavar='ver_no', dest='ver_no', type=int, default=0, help='version release number')
    parser.add_argument('--verenv', metavar='ver_env', dest='ver_env', type=str, default='test',
                        choices=['dev', 'test', 'test2', 'pre', 'pregray', 'gray', 'pro'],
                        help='dev: develop environment; test: test environment; test2: test2 environment; '
                             'pre: pre-release environment; pregray: pre-gray-release environment; '
                             'gray: gray-release environment;  pro: production environment;')

    parser.add_argument('--apiver', metavar='api_ver', dest='api_ver', type=str, help='network api version number')
    parser.add_argument('--appcode', metavar='app_code', dest='app_code', type=str, default='txxy',
                        choices=['txxy', 'xycx', 'pyqx', 'pyzx', 'ljh'],
                        help='txxy: tian xia xin yong; xycx: xin yong cha xun; pyqx: peng you qi xin; pyzx: peng yuan zheng xin; ljh: la jiao hong;')
    parser.add_argument('--appname', metavar='app_name', dest='app_name', default='@string/app_name', help='application name')

    parser.add_argument('--test', dest='is_test', action='store_true', default=False,
                        help='indicate just to test config')
    parser.add_argument('--align', dest='to_align', action='store_true', default=True,
                        help='indicate to align apk file after protected')
    parser.add_argument('--upload', dest='to_upload', action='store_true', default=False,
                        help='indicate to upload build files')
    parser.add_argument('--arm64', dest='is_arm64', action='store_true', default=False,
                        help='indicate to build with arm64')
    parser.add_argument('--google', dest='for_google', action='store_true', default=False,
                        help='indicate to build for google play')
    parser.add_argument('--channel', metavar='channel', dest='channel', type=str, default=BuilderLabel.DEFAULT_CHAN, help='application channel')
    parser.add_argument('--demo', metavar='demo_label', dest='demo_label', type=str, default='normal',
                        choices=['normal', 'bridge', 'hotloan', 'mall'],
                        help='normal: normal entry; bridge: bridge entry; hotloan: hot loan entry;')
    parser.add_argument('--branch', metavar='branch', dest='branch', default='master', help='code branch name')
    parser.add_argument('--jpush', metavar='jpush_appkey', dest='jpush_appkey', default=None, help='jpush app key')

    #     parser.print_help()

    return parser.parse_args(src_args)


if __name__ == '__main__':
    test_args = None
    args = get_args(test_args)
    trivial_util.measure_time(main, args)