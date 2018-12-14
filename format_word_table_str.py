import argparse
import time

import os
import creditutils.str_util as str_utils
import creditutils.file_util as myfile


class ConfigBuildManager:
    def __init__(self, args):
        # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)

        self.src = os.path.abspath(self.src)

    def process(self):
        content = myfile.read_file_content(self.src, encoding_='utf-8')
        # content = open(self.src).read().decode('gb18030', 'ignore')
        # content = myfile.read_file_content(self.src)
        print(content)
        content = content.replace('\t', '|')
        content = content.replace('\r\n', '|\r\n|')
        content = '|' + content + '|'
        myfile.write_to_file(self.src, content, encoding='utf-8')

# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='pack configure file.')
    parser.add_argument('src', metavar='src', help='to process file path')

    return parser.parse_args(src_args)


def main(args):
    manager = ConfigBuildManager(args)
    manager.process()


if __name__ == '__main__':
    begin = time.time()

    #     test_args = 'a b -i -u'.split()
    test_args = None
    args = get_args(test_args)
    main(args)

    end = time.time()
    time_info = str_utils.get_time_info(begin, end)

    # 输出总用时
    print('===Finished. Total time: {}==='.format(time_info))