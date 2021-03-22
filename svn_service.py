import argparse
import os
from typing import Tuple
from creditutils import file_util
from rpyc import Service
from rpyc.utils.server import ThreadedServer
import threading
import filecmp
import creditutils.trivial_util as trivial_util
from creditutils.trivial_util import print_t
import traceback

CODE_SUCCESS = 0
CODE_FAILED = 1
CODE_INVALID_TOKEN = 2


class SvnService(Service):
    ALIASES = ['svn_service']

    def __init__(self, svn_root, token=None, normal=None, refuse=None, target=None) -> None:
        super().__init__()
        self.svn_root = svn_root
        self.token = token
        self.normal = normal
        self.refuse = refuse
        self.target = target
        self.lock = threading.Lock()

        if not self.normal:
            raise Exception(f'normal: {self.normal} is invalid!')

        if not self.refuse:
            raise Exception(f'refuse: {self.refuse} is invalid!')

        if not self.target:
            raise Exception(f'target: {self.target} is invalid!')
        
        print_t('init success.')

    def exposed_switch_commit(self, name: str, status: bool, token=None) -> Tuple[int, str]:
        '''
        进行指定svn库提交状态切换
        :param name: svn库名称
        :param status: 提交状态，True，放开提交，False，禁止提交。
        :return: int 0, 成功, 1 失败；str 具体信息说明。
        '''
        with self.lock:
            if self.token != token:
                return CODE_INVALID_TOKEN, f'token: {token} is invalid!'

            try:
                self.switch_commit_with_file(name, status)
            except Exception as e:
                traceback.print_exc()
                return CODE_FAILED, f'failed with {str(e)}!'
        
        return CODE_SUCCESS, f'switch with {status} success.'

    def switch_commit_with_file(self, name, status):
        hooks_root = os.path.join(self.svn_root, name, 'hooks')
        normal_path = os.path.join(hooks_root, self.normal)
        refuse_path = os.path.join(hooks_root, self.refuse)
        target_path = os.path.join(hooks_root, self.target)
        
        if status:
            source_path = normal_path
        else:
            source_path = refuse_path

        rtn = filecmp.cmp(source_path, target_path)
        if not rtn:
            file_util.replace_file(source_path, target_path)


class Manager:
    HEAD_NAME = 'HEAD'
    def __init__(self, args):
        # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)
        # pprint.pprint(vars(self))

        self.svn_root = os.path.abspath(self.svn_root)

    def process(self):
        obj = SvnService(self.svn_root, token=self.token, normal=self.normal, refuse=self.refuse, target=self.target)
        s = ThreadedServer(obj, port=self.port, auto_register=False)
        s.start()


def main(args):
    manager = Manager(args)
    manager.process()


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='to start svn service.')
    # 工作目录
    parser.add_argument('svn_root', metavar='svn_root', help='svn root directory')
    parser.add_argument('--port', metavar='port', dest='port', type=int, default=9999, help='to specify local port.')
    parser.add_argument('--token', metavar='token', dest='token', type=str, default=None, help='to specify request token.')
    parser.add_argument('--normal', metavar='normal', dest='normal', type=str, default='pre-commit_normal.cmd', help='to specify normal name.')
    parser.add_argument('--refuse', metavar='refuse', dest='refuse', type=str, default='pre-commit_refuse.cmd', help='to specify refuse name.')
    parser.add_argument('--target', metavar='target', dest='target', type=str, default='pre-commit.cmd', help='to specify target name.')

    #     parser.print_help()

    return parser.parse_args(src_args)


if __name__ == '__main__':
    test_args = None
    args = get_args(test_args)
    trivial_util.measure_time(main, args)
