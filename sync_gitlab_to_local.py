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
# 1.先遍历老的gitlab库，将所有的库罗列出来；
# 2.依次对所有老库所有分支进行如下操作：
# (1)下载下来指定分支并更新(git pull --all)；
# (2)调整remote地址，分别调用“git remote rm origin” 和 “git remote add origin 你的新远程仓库地址"(如 git remote add origin git@192.168.20.202:frontend/pk.git)进行更新；
# (3)将代码同步到新的远程，调用命令为“git push --all origin”；
# (4)中间有任何一个库操作失败，则记录下来，继续对下一个进行操作；
# 3.特别说明，后续将只支持v4版本gitlab的同步，不再支持v3版本；（API V3 was unsupported from GitLab 9.5, released on August 22, 2017. API v3 was removed in GitLab 11.0.）

class ApiLabel:
    v4 = 'v4'

class DataLabel:
    id = 'id'
    name = 'name'
    path = 'path'
    ssh_url_to_repo = 'ssh_url_to_repo'
    path_with_namespace = 'path_with_namespace'

def clean_history(repo_path, project):
    temp_name = 'middle_temp_butt_none'
    master_branch = None
    try:
        # 先取消分支保护
        branches = project.branches.list()
        master_branch = None
        master_tag = 'master'
        for branch in branches:
            if master_tag == branch.name:
                master_branch = branch

            branch.unprotect()

        # 一种获取分支方式
        # master_branch = project.branches.get('master')

        # 先更新git仓库信息
        repo = git.Repo(repo_path)

        # 先获取本地分支信息
        local_branches = repo.branches
        local_map = dict()
        for item in local_branches:
            local_map[item.name] = item

        # 如果本地分支没有相应的远程分支，则创建，如果有则更新覆盖。
        for k in local_map:
            if k != repo.active_branch.name:
                repo.git.checkout(k)

            repo.git.checkout(temp_name, orphan=True)
            repo.git.add(all=True)
            repo.git.commit('Initial commit.', a=True, m=True)
            repo.git.branch(k, d=True)
            repo.git.branch(k, m=True)
            repo.git.push('origin', k, f=True)
    finally:
        # 最后恢复分支保护
        if master_branch:
            master_branch.protect()

class Manager:
    def __init__(self, args):
        # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)
        #         pprint.pprint(vars(self))

        self.git_root = os.path.abspath(self.git_root)

    def process(self):
        self.sync_project()

    def sync_project(self):
        src_items = self.get_projects_sync_item(self.src, self.token)
        other_info = dict()
        # cnt_butt = 4
        # cnt_index = 0
        for k, v in src_items.items():
            path = v.path
            path_with_namespace = v.path_with_namespace
            if not path_with_namespace.endswith(path):
                print(f'{path_with_namespace} not endswith {path}!')
                other_info[k] = v
                continue

            if path == path_with_namespace:
                namespace = None
                prj_path = self.git_root
            else:
                namespace = path_with_namespace[0:-len(path)]
                prj_path = file_util.normalpath(os.path.join(self.git_root, namespace))
            
            prj_git_path = file_util.normalpath(os.path.join(self.git_root, path_with_namespace))
            code_url = v.ssh_url_to_repo

            # 只有本地不存在相关目录才从服务器端同步
            if not os.path.isdir(prj_git_path):
                print(f'to process {path_with_namespace}.')
                if self.to_clean_history:
                    # 先删除远程服务器上的tag信息，本地clone的时候就不会存在该信息
                    if v.tags:
                        tags = v.tags.list()
                        for tag in tags:
                            tag.delete()

                self.checkout(prj_path, path, code_url)
                sync_git.Manager.sync_repo(prj_git_path)
                
                if self.to_clean_history:
                    clean_history(prj_git_path, v)

                print(f'processed {path_with_namespace}.')
            else:
                print(f'{path_with_namespace} already exists.')

            # cnt_index += 1
            # if cnt_index >= cnt_butt:
            #     break

        print('need manual operation items:')
        pprint.pprint(other_info)

    def checkout(self, prj_path, path, code_url, branch=None):
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
                        shutil.rmtree(prj_git_root, ignore_errors=False)
                    else:
                        return
                else:
                    shutil.rmtree(prj_git_root, ignore_errors=False)
            
        # git_util.clone(code_url, prj_path, branch=branch)
        try:
            git.Repo.clone_from(code_url, prj_git_root)
        except git.exc.GitCommandError as e:
            print(str(e))

    def get_projects_sync_item(self, target, token):
        results = dict()
        src_items = self.get_projects_v4(target, token)
        for src_item in src_items:
            results[src_item.id] = src_item
        
        # print(results)
        return results
    
    def get_projects_v4(self, target, token):
        op = gitlab.Gitlab(target, private_token=token)
        projects = op.projects.list(all=True)
        # cnt = 0
        # for project in projects:
        #     print(project)
        #     print(project.ssh_url_to_repo, project.name, project.id)
        #     cnt += 1

        # print(f'count is {cnt}')
        return projects


def main(args):
    manager = Manager(args)
    manager.process()


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='check uploaded file consistency')
    parser.add_argument('src', metavar='src', help='source gitlab server')
    parser.add_argument('token', metavar='token', help='source gitlab server token')
    parser.add_argument('git_root', metavar='git_root', help='git root directory')
    parser.add_argument('--clean-history', dest='to_clean_history', action='store_true', default=False, help='indicate to clean history and synchronise to remote')
    
    # parser.print_help()

    return parser.parse_args(src_args)


if __name__ == '__main__':
    test_args = None
    args = get_args(test_args)
    trivial_util.measure_time(main, args)