import os
import time
import argparse
import shutil
import pprint
import git
import creditutils.trivial_util as trivial_util
import creditutils.file_util as file_util
import creditutils.exec_cmd as exec_cmd
import gitlab
import creditutils.git_util as git_util
import sync_git

# 设计思路说明：
# 1.先遍历gitlab库，将所有的库罗列出来；
# 2.依次对所有库所有分支进行如下操作：
# (1)下载下来指定分支并更新；
# (2)中间有任何一个库操作失败，则记录下来，继续对下一个进行操作；
# (3)在更新库的同时，记录到有效列表中；
# (4)遍历本地目录，如果不在有效列表中，则直接删除该目录；


class DataLabel:
    id = 'id'
    name = 'name'
    path = 'path'
    ssh_url_to_repo = 'ssh_url_to_repo'
    path_with_namespace = 'path_with_namespace'


class Manager:
    def __init__(self, args):
        # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)
        #         pprint.pprint(vars(self))

        self.git_root = os.path.abspath(self.git_root)
        self.valid_local_paths = []
        self.invalid_local_paths = []

    def process(self):
        op = gitlab.Gitlab(self.src, private_token=self.token)
        projects = op.projects.list(all=True)
        for item in projects:
            # cnt_butt = 4
            # cnt_index = 0
            
            self.sync_project(item)
            
            # cnt_index += 1
            # if cnt_index >= cnt_butt:
            #     break

        # 清理本地有而服务器端已不存在的库
        self.collect_invalid_repo_recursive(self.git_root)
        for item in self.invalid_local_paths:
            shutil.rmtree(item)
            print(f'removed {item}.')

    def sync_project(self, project):
        path = project.path
        path_with_namespace = project.path_with_namespace
        if not path_with_namespace.endswith(path):
            raise Exception(f'{path_with_namespace} not endswith {path}!')

        if path == path_with_namespace:
            namespace = None
            prj_path = self.git_root
        else:
            namespace = path_with_namespace[0:-len(path)]
            prj_path = file_util.normalpath(os.path.join(self.git_root, namespace))
        
        prj_git_path = file_util.normalpath(os.path.join(self.git_root, path_with_namespace))
        code_url = project.ssh_url_to_repo

        if self.to_reprocess:
            if os.path.isdir(prj_git_path):
                shutil.rmtree(prj_git_path)

        # 将从服务器端checkout的目录添加到有效列表
        self.valid_local_paths.append(prj_git_path)

        print(f'to process {path_with_namespace}.')
        self.checkout(prj_path, path, code_url)
        sync_git.Manager.sync_repo(prj_git_path)
        print(f'processed {path_with_namespace}.')

    def collect_invalid_repo_recursive(self, repo_path):
        file_list = os.listdir(repo_path)
        for filename in file_list:
            temp_file_path = os.path.join(repo_path, filename)
            if os.path.isdir(temp_file_path):
                if git_util.is_repository(temp_file_path):
                    if temp_file_path not in self.valid_local_paths:
                        self.invalid_local_paths.append(temp_file_path)
                else:
                    self.collect_invalid_repo_recursive(temp_file_path)

    def checkout(self, prj_path, path, code_url):
        prj_git_root = os.path.join(prj_path, path)
        if not os.path.isdir(prj_path):
            os.makedirs(prj_path)
        else:
            if os.path.isdir(prj_git_root):
                if git_util.is_repository(prj_git_root):
                    repo = git.Repo(prj_git_root)
                    origin = repo.remote()
                    remote_url = None
                    for item in origin.urls:
                        remote_url = item
                        break

                    if remote_url != code_url:
                        shutil.rmtree(prj_git_root)
                    else:
                        return
                else:
                    shutil.rmtree(prj_git_root)
            
        # git_util.clone(code_url, prj_path, branch=branch)
        try:
            git.Repo.clone_from(code_url, prj_git_root)
        except git.exc.GitCommandError as e:
            print(str(e))


def main(args):
    manager = Manager(args)
    manager.process()


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='check uploaded file consistency')
    parser.add_argument('src', metavar='src', help='source gitlab server')
    parser.add_argument('token', metavar='token', help='source gitlab server token')
    parser.add_argument('git_root', metavar='git_root', help='git root directory')
    parser.add_argument('--reprocess', dest='to_reprocess', action='store_true', default=False, help='indicate to reprocess the existing local project')
    
    # parser.print_help()

    return parser.parse_args(src_args)


if __name__ == '__main__':
    test_args = None
    args = get_args(test_args)
    trivial_util.measure_time(main, args)