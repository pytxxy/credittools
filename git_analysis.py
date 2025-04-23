import os
import argparse
import creditutils.trivial_util as trivial_util

class Manager:
    def __init__(self, args):
        # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)
        #         pprint.pprint(vars(self))

        self.git_root = os.path.abspath(self.git_root)

    def process(self):
        """列出指定路径下的所有一级子目录。"""
        root_path = self.git_root
        size_map = {}
        directories = [d for d in os.listdir(root_path) if os.path.isdir(os.path.join(root_path, d))]
        for item in directories:
            whole_path = os.path.join(root_path, item)
            total_size = get_directory_size(whole_path)
            size_map[item] = total_size
            

def get_directory_size(src_path):
    """计算指定路径下所有文件的总大小。"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(src_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # 跳过如果它是符号链接
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)

    return total_size

def one_file_entry():
    repo_path = '/path/to/your/repo'  # 替换为您的本地仓库路径
    size = get_directory_size(repo_path)
    print(f"仓库大小: {size / (1024 * 1024):.2f} MB")


def main(args):
    manager = Manager(args)
    manager.process()


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='analyse git repository size')
    parser.add_argument('git_root', metavar='git_root', help='git root directory')
    
    # parser.print_help()

    return parser.parse_args(src_args)


if __name__ == '__main__':
    test_args = None
    args = get_args(test_args)
    trivial_util.measure_time(main, args)