# -*- coding:UTF-8 -*-
import os
import argparse
import creditutils.apk_util as apk_util
import creditutils.trivial_util as utility


class ProcessManager:
    def __init__(self, args):
        # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)

        self.src = os.path.abspath(self.src)

        if not self.keystore:
            raise Exception('please specify keystore')
        
        if not self.storepass:
            raise Exception('please specify storepass')
        
        if not self.storealias:
            raise Exception('please specify storealias')

        self.keystore = os.path.abspath(self.keystore)
        self.src = os.path.abspath(self.src)
        if self.dst:
            self.dst = os.path.abspath(self.dst)
        else:
            self.dst = self._get_signed_path(self.src)

    def process(self):
        parent_dir = os.path.dirname(self.dst)
        if not os.path.isdir(parent_dir):
            os.makedirs(parent_dir)

        rtn = apk_util.sign_apk(self.keystore, self.storepass, self.storealias, self.src, self.dst)
        if rtn:
            print(f'Sign {self.src} success and the result is {self.dst}.')
        else:
            print(f'Sign {self.src} failed!')

    def _get_signed_path(self, src):
        suffix = '_signed'
        result_array = os.path.splitext(src)
        result = result_array[0] + suffix + result_array[1]
        # print(result)
        return result

def main(args):
    manager = ProcessManager(args)
    manager.process()


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='update code if need, build if need.')
    parser.add_argument('src', metavar='src', help='source file path')
    parser.add_argument('-d', metavar='dst', dest='dst',
                        help='target file path')

    parser.add_argument('--keystore', metavar='keystore', dest='keystore', 
                        help='with this keystore to sign')
    parser.add_argument('--storepass', metavar='storepass', dest='storepass',
                        help='with this storepass to sign')
    parser.add_argument('--storealias', metavar='storealias', dest='storealias',
                        help='with this storealias to sign')
    # parser.print_help()

    return parser.parse_args(src_args)


if __name__ == '__main__':
    # test_args = "--keystore D:\\auto_build\\pytxxy\\project\\develop\\TxxyAndroid\\app\\pycreditKeystore --storepass pycreditapkkey --storealias pycreditKeystoreAlias F:\\temp\\apk\\5.0.9-684-20200724_sec.apk".split()

    test_args = None
    args = get_args(test_args)
    utility.measure_time(main, args)
