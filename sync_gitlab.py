import os
import time
import argparse
import requests
import shutil
import subprocess
import pprint
import git
import creditutils.trivial_util as trivial_util
import creditutils.file_util as file_util
import creditutils.exec_cmd as exec_cmd
import gitlab
import creditutils.git_util as git_util
import sync_git
import traceback

# 安装依赖：
# GitPython          3.1.30(3.1.31版本会报错)
# python-gitlab      3.15.0

# 设计思路说明：
# 1.先遍历老的gitlab库，将所有的库罗列出来；
# 2.依次对所有老库所有分支进行如下操作：
# (1)下载下来指定分支并更新(git pull --all)；
# (2)调整remote地址，分别调用“git remote rm origin” 和 “git remote add origin 你的新远程仓库地址"(如 git remote add origin git@192.168.20.202:frontend/pk.git)进行更新；
# (3)将代码同步到新的远程，调用命令为“git push --all origin”；
# (4)中间有任何一个库操作失败，则记录下来，继续对下一个进行操作；
# 3.特别说明，后续将只支持v4版本gitlab的同步，不再支持v3版本；（API V3 was unsupported from GitLab 9.5, released on August 22, 2017. API v3 was removed in GitLab 11.0.）

class ApiLabel:
    v3 = 'v3'
    v4 = 'v4'

class DataLabel:
    id = 'id'
    name = 'name'
    path = 'path'
    ssh_url_to_repo = 'ssh_url_to_repo'
    path_with_namespace = 'path_with_namespace'

class ProcessManager:
    def __init__(self, args):
        # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)
        #         pprint.pprint(vars(self))

        self.git_root = os.path.abspath(self.git_root)

    def process(self):
        if self.backup_only:
            self.backup_project()
        else:
            self.sync_project()

    def backup_project(self):
        # self.sync_single_project()
        # return
        src_items = self.get_projects_sync_item(self.src, self.src_token)
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

            # branches = v.branches.list()
            # for branch in branches:
            #     branch_id = branch.get_id()
            #     relative_path = os.path.join(path_with_namespace, branch_id)
            #     prj_path = file_util.normalpath(os.path.join(self.git_root, relative_path))
            #     code_url = v.ssh_url_to_repo
            #     self.checkout(prj_path, path, code_url, branch=branch_id)

            if path == path_with_namespace:
                namespace = None
                prj_path = self.git_root
            else:
                namespace = path_with_namespace[0:-len(path)]
                prj_path = file_util.normalpath(os.path.join(self.git_root, namespace))
            
            prj_git_path = file_util.normalpath(os.path.join(self.git_root, path_with_namespace))
            code_url = v.ssh_url_to_repo
            self.checkout(prj_path, path, code_url)
            sync_git.Manager.sync_repo(prj_git_path)
            # print(f'prj_path: {prj_path}, code_url: {code_url}')

            # cnt_index += 1
            # if cnt_index >= cnt_butt:
            #     break

        print('need manual operation items:')
        pprint.pprint(other_info)

    # 有待实际验证效果
    def sync_project(self):
        src_items = self.get_projects_sync_item(self.src, self.src_token)
        dst_items = self.get_projects_sync_item(self.dst, self.dst_token)
        other_info = dict()
        for k, v in src_items.items():
            if k in dst_items:
                path = v.path
                path_with_namespace = v.path_with_namespace
                if not path_with_namespace.endswith(path):
                    print(f'{path_with_namespace} not endswith {path}!')
                    other_info[k] = v
                    continue

                # branches = v.branches.list()
                # for branch in branches:
                #     branch_id = branch.get_id()
                #     relative_path = os.path.join(path_with_namespace, branch_id)
                #     prj_path = file_util.normalpath(os.path.join(self.git_root, relative_path))
                #     root_path = file_util.normalpath(os.path.join(prj_path, path))
                #     code_url = v.ssh_url_to_repo
                #     self.checkout(prj_path, path, code_url, branch=branch_id)

                #     dst_item = dst_items[k]
                #     rtn = self.pull_all(root_path)
                #     if not rtn:
                #         other_info[k] = v
                #         continue

                #     dst_url = dst_item.ssh_url_to_repo
                #     rtn = self.update_remote_url(root_path, dst_url)
                #     if not rtn:
                #         other_info[k] = v
                #         continue

                #     self.push_all_to_remote(root_path)

                if path == path_with_namespace:
                    namespace = None
                    prj_path = self.git_root
                else:
                    namespace = path_with_namespace[0:-len(path)]
                    prj_path = file_util.normalpath(os.path.join(self.git_root, namespace))

                try:
                    prj_git_path = file_util.normalpath(os.path.join(self.git_root, path_with_namespace))
                    code_url = v.ssh_url_to_repo
                    self.checkout(prj_path, path, code_url)
                    sync_git.Manager.sync_repo(prj_git_path)

                    dst_item = dst_items[k]
                    dst_url = dst_item.ssh_url_to_repo
                    rtn = self.update_remote_url(prj_git_path, dst_url)
                    if not rtn:
                        other_info[k] = v
                        continue

                    sync_git.Manager.push_to_remote(prj_git_path)
                except:
                    print(f'sync_project {dst_url} failed with {traceback.format_exc()}')
            else:
                other_info[k] = v

        for k, v in dst_items.items():
            if k not in src_items:
                other_info[k] = v

        print('need manual operation items:')
        pprint.pprint(other_info)

    def backup_project_support_v3(self):
        src_items = self.get_projects_sync_item_support_v3(self.src, self.src_token, self.src_api)
        other_info = dict()
        for k, v in src_items.items():
            path = v[DataLabel.path]
            path_with_namespace = v[DataLabel.path_with_namespace]
            if not path_with_namespace.endswith(path):
                print(f'{path_with_namespace} not endswith {path}!')
                other_info[k] = v
                continue

            relative_path = path_with_namespace[:-len(path)]
            prj_path = file_util.normalpath(os.path.join(self.git_root, relative_path))
            code_url = v[DataLabel.ssh_url_to_repo]
            self.checkout(prj_path, path, code_url)

        print('need manual operation items:')
        pprint.pprint(other_info)

    def sync_project_support_v3(self):
        src_items = self.get_projects_sync_item_support_v3(self.src, self.src_token, self.src_api)
        dst_items = self.get_projects_sync_item_support_v3(self.dst, self.dst_token, self.dst_api)
        other_info = dict()
        for k, v in src_items.items():
            if k in dst_items:
                path = v[DataLabel.path]
                path_with_namespace = v[DataLabel.path_with_namespace]
                if not path_with_namespace.endswith(path):
                    print(f'{path_with_namespace} not endswith {path}!')
                    other_info[k] = v
                    continue

                relative_path = path_with_namespace[:-len(path)]
                prj_path = file_util.normalpath(os.path.join(self.git_root, relative_path))
                root_path = file_util.normalpath(os.path.join(prj_path, path))
                code_url = v[DataLabel.ssh_url_to_repo]
                self.checkout(prj_path, path, code_url)

                dst_item = dst_items[k]
                rtn = self.pull_all(root_path)
                if not rtn:
                    other_info[k] = v
                    continue

                dst_url = dst_item[DataLabel.ssh_url_to_repo]
                rtn = self.update_remote_url(root_path, dst_url)
                if not rtn:
                    other_info[k] = v
                    continue

                self.push_all_to_remote(root_path)
            else:
                other_info[k] = v

        for k, v in dst_items.items():
            if k not in src_items:
                other_info[k] = v

        print('need manual operation items:')
        pprint.pprint(other_info)

    def checkout(self, prj_path, path, code_url, branch=None):
        prj_git_root = os.path.join(prj_path, path)
        if not os.path.isdir(prj_path):
            os.makedirs(prj_path)
        else:
            if os.path.isdir(prj_git_root):
                shutil.rmtree(prj_git_root, ignore_errors=False)
            
        # git_util.clone(code_url, prj_path, branch=branch)
        try:
            git.Repo.clone_from(code_url, prj_git_root)
        except git.exc.GitCommandError as e:
            print(str(e))

    def pull_all(self, root_path):
        try:
            cmd_str = 'git pull --all'
            print(f'in {root_path} excute "{cmd_str}"')
            exec_cmd.run_cmd_for_code_in_specified_dir(root_path, cmd_str)
            return True
        except subprocess.CalledProcessError as e:
            print(e)
            return False

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

    def push_all_to_remote(self, root_path):
        try:
            cmd_str = f'git push --all origin'
            print(f'in {root_path} excute "{cmd_str}"')
            exec_cmd.run_cmd_for_code_in_specified_dir(root_path, cmd_str)
            return True
        except subprocess.CalledProcessError as e:
            print(e)
            return False

    def get_projects_sync_item(self, target, token):
        results = dict()
        src_items = self.get_projects_v4(target, token)
        for src_item in src_items:
            results[src_item.id] = src_item
        
        # print(results)
        return results

    def get_projects_sync_item_support_v3(self, target, token, api_ver=ApiLabel.v4):
        results = dict()
        if api_ver == ApiLabel.v3:
            src_items = self.get_projects_v3(target, token)
            for src_item in src_items:
                item = dict()
                item[DataLabel.id] = src_item[DataLabel.id]
                item[DataLabel.name] = src_item[DataLabel.name]
                item[DataLabel.path] = src_item[DataLabel.path]
                item[DataLabel.ssh_url_to_repo] = src_item[DataLabel.ssh_url_to_repo]
                item[DataLabel.path_with_namespace] = src_item[DataLabel.path_with_namespace]
                results[src_item[DataLabel.id]] = item
        elif api_ver == ApiLabel.v4:
            src_items = self.get_projects_v4(target, token)
            for src_item in src_items:
                item = dict()
                item[DataLabel.id] = src_item.id
                item[DataLabel.name] = src_item.name
                item[DataLabel.path] = src_item.path
                item[DataLabel.ssh_url_to_repo] = src_item.ssh_url_to_repo
                item[DataLabel.path_with_namespace] = src_item.path_with_namespace
                results[src_item.id] = item

        # print(results)
        return results

    def get_projects_v3(self, target, token):
        api_url = f'{target}/api/{ApiLabel.v3}/projects/all?private_token={token}&per_page=200'
        # print(api_url)
        result = requests.get(api_url)
        data_list = result.json()
        # cnt = 0
        # for item in data_list:
        #     # if cnt == 0:
        #     #     print(item)
        #     #     prj_id = item['id']
        #     #     self.get_commits(target, token, prj_id, api_ver)
            
        #     print(item)
        #     print(item['name'], item['id'])
        #     cnt += 1

        # print(f'count is {cnt}')
        return data_list
    
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

    def get_commits(self, target, token, prj_id, api_ver=ApiLabel.v4):
        api_url = f'{target}/api/{api_ver}/projects/{prj_id}/repository/commits?private_token={token}&since=2019-08-08T00:00:00Z'
        # api_url = f'{target}/api/{api_ver}/projects/{prj_id}/repository/commits?private_token={token}&since=2019-08-08T00:00:00+08:00'
        print(api_url)
        result = requests.get(api_url)
        print(result.json())

    def sync_single_project(self):
        to_sync_array = [
            {
                'path': 'risk-decision-local.git', 
                'namespace':'riskdecision',
                'code_url':'git@gitlab.pycredit.cn',
                'dst_url': 'git@gitlab.hnfhm.com'
            },
            {
                'path': 'risk-admin.git', 
                'namespace':'riskdecision',
                'code_url':'git@gitlab.pycredit.cn',
                'dst_url': 'git@gitlab.hnfhm.com'
            },
            {
                'path': 'risk-decision-modules.git', 
                'namespace':'riskdecision',
                'code_url':'git@gitlab.pycredit.cn',
                'dst_url': 'git@gitlab.hnfhm.com'
            },
            {
                'path': 'pycredit-boot.git', 
                'namespace':'riskdecision',
                'code_url':'git@gitlab.pycredit.cn',
                'dst_url': 'git@gitlab.hnfhm.com'
            },
        ]
        
        for item in to_sync_array:
            path = item['path']
            namespace = item['namespace']
            path_with_namespace = namespace + '/' + path
            prj_path = file_util.normalpath(os.path.join(self.git_root, namespace))
            prj_git_path = file_util.normalpath(os.path.join(self.git_root, path_with_namespace))
            code_url = item['code_url'] + ':' + path_with_namespace
            self.checkout(prj_path, path, code_url)
            sync_git.Manager.sync_repo(prj_git_path)

            dst_url = item['dst_url'] + ':' + path_with_namespace
            # print(f' path: {path}\n namespace: {namespace}\n path_with_namespace: {path_with_namespace}\n code_url: {code_url}\n dst_url: {dst_url}\n')
            rtn = self.update_remote_url(prj_git_path, dst_url)
            if not rtn:
                print(f'update_remote_url({prj_git_path}, {dst_url}) failed!')

            sync_git.Manager.push_to_remote(prj_git_path)

def main(args):
    manager = ProcessManager(args)
    manager.process()


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='check uploaded file consistency')
    parser.add_argument('src', metavar='src', help='source gitlab server')
    parser.add_argument('src_token', metavar='src_token', help='source gitlab server token')
    parser.add_argument('dst', metavar='dst', help='destination gitlab server')
    parser.add_argument('dst_token', metavar='dst_token', help='destination gitlab server token')
    parser.add_argument('git_root', metavar='git_root', help='git root directory')
    parser.add_argument('--srcapi', metavar='src_api', dest='src_api', type=str, default=ApiLabel.v4,
                        choices=[ApiLabel.v3, ApiLabel.v4],
                        help=f'{ApiLabel.v3}: gitlab API V3; {ApiLabel.v4}: gitlab API V4;')
    parser.add_argument('--dstapi', metavar='dst_api', dest='dst_api', type=str, default=ApiLabel.v4,
                        choices=[ApiLabel.v3, ApiLabel.v4],
                        help=f'{ApiLabel.v3}: gitlab API V3; {ApiLabel.v4}: gitlab API V4;')
    parser.add_argument('--backup', dest='backup_only', action='store_true', default=False,
                        help='indicate just backup only')

    # parser.print_help()

    return parser.parse_args(src_args)


if __name__ == '__main__':
    test_args = None
    args = get_args(test_args)
    trivial_util.measure_time(main, args)