import argparse
import traceback
import rpyc


class Manager:
    HEAD_NAME = 'HEAD'
    def __init__(self, args):
        # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)
        # pprint.pprint(vars(self))

        if not self.host:
            raise Exception(f'host: {self.host} is invalid!')

        if not self.port:
            raise Exception(f'port: {self.port} is invalid!')

    def process(self):
        conn = None
        try:
            conn = rpyc.connect(self.host, self.port)
            code, msg = conn.root.switch_commit(self.name, self.commit, token=self.token)
            print(f'call remote switch_commit with result code: {code}, msg: {msg}.')
        except:
            traceback.print_exc()
            code = 1
        finally:
            if conn:
                conn.close()

        return code


def main(args):
    manager = Manager(args)
    return manager.process()


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='to switch svn service commit status.')
    # 工作目录
    parser.add_argument('name', metavar='name', help='svn repository name')
    parser.add_argument('--host', metavar='host', dest='host', type=str, default=None, help='to specify remote host.')
    parser.add_argument('--port', metavar='port', dest='port', type=int, default=None, help='to specify remote port.')
    parser.add_argument('--token', metavar='token', dest='token', type=str, default=None, help='to specify request token.')
    parser.add_argument('--commit', dest='commit', action='store_true', default=False, help='indicate to enable or disable commit')

    #     parser.print_help()

    return parser.parse_args(src_args)


if __name__ == '__main__':
    test_args = None
    args = get_args(test_args)
    exit(main(args))