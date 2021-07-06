import os
import argparse
import subprocess
import creditutils.trivial_util as trivial_util
import creditutils.exec_cmd as exec_cmd
import sync_git


# 设计思路说明：
# 1.依次对本地所有库进行如下操作：
# (1)通过调用“git remote get-url origin”，获取remote地址，进行相应替换获取到目标url地址；
# (2)调整remote地址，分别调用“git remote rm origin” 和 “git remote add origin 你的新远程仓库地址"(如 git remote add origin git@192.168.20.202:frontend/pk.git)进行更新；
# (3)将代码同步到新的远程，调用命令为“git push --all origin”；
# (4)中间有任何一个库操作失败，则记录下来，继续对下一个进行操作；

# 当前手动在目标库上创建的group和project，后续有需要可转换成api创建（20210628 11:40）

class ProcessManager:
    def __init__(self, args):
        # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)
        #         pprint.pprint(vars(self))

        self.git_root = os.path.abspath(self.git_root)

    def process(self):
        if not os.path.isdir(self.git_root):
            raise Exception(f'{self.git_root} is not valid directory!')
            
        if sync_git.is_repository(self.git_root):
            self.upload_project(self.git_root)
        else:
            self.upload_project_recursive(self.git_root)

    # 有待实际验证效果
    def upload_project(self, prj_git_path):
        src_url = self.src_url
        dst_url = self.dst_url
        origin_url = self.get_remote_url(prj_git_path)
        target_url = origin_url.replace(src_url, dst_url)
        rtn = self.update_remote_url(prj_git_path, target_url)
        if not rtn:
            print(f'in {prj_git_path} update with {dst_url} failed!')
            return

        sync_git.Manager.push_to_remote(prj_git_path)

    def upload_project_recursive(self, repo_path):
        file_list = os.listdir(repo_path)
        for filename in file_list:
            temp_file_path = os.path.join(repo_path, filename)
            if os.path.isdir(temp_file_path):
                if sync_git.is_repository(temp_file_path):
                    self.upload_project(temp_file_path)
                else:
                    self.upload_project_recursive(temp_file_path)

    def get_remote_url(self, root_path):
        try:
            rm_cmd_str = 'git remote get-url origin'
            print(f'in {root_path} excute "{rm_cmd_str}"')
            return exec_cmd.run_cmd_for_output_in_specified_dir(root_path, rm_cmd_str)
        except subprocess.CalledProcessError as e:
            print(e)
            return None

    def update_remote_url(self, root_path, dst_url):
        try:
            rm_cmd_str = 'git remote rm origin'
            print(f'in {root_path} excute "{rm_cmd_str}"')
            exec_cmd.run_cmd_for_code_in_specified_dir(root_path, rm_cmd_str)

            add_cmd_str = f'git remote add origin {dst_url}'
            print(f'in {root_path} excute "{add_cmd_str}"')
            exec_cmd.run_cmd_for_code_in_specified_dir(root_path, add_cmd_str)
            return True
        except subprocess.CalledProcessError as e:
            print(e)
            return False


def main(args):
    manager = ProcessManager(args)
    manager.process()


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='check uploaded file consistency')
    parser.add_argument('git_root', metavar='git_root', help='git root directory')
    parser.add_argument('src_url', metavar='src_url', help='source gitlab server url address')
    parser.add_argument('dst_url', metavar='dst_url', help='destination gitlab server url address')

    # parser.print_help()

    return parser.parse_args(src_args)


if __name__ == '__main__':
    test_args = None
    args = get_args(test_args)
    trivial_util.measure_time(main, args)