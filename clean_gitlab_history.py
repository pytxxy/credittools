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
# (1)清理掉远程仓库的所有tag(如果tag是受保护的，则先解开保护)；
# (2)依次清理各个分支的历史记录(如果分支是受保护的，则先解开保护，处理完之后再恢复)；
# (3)中间有任何一个库操作失败，则记录下来，继续对下一个进行操作；


class DataLabel:
    id = 'id'
    name = 'name'
    path = 'path'
    ssh_url_to_repo = 'ssh_url_to_repo'
    path_with_namespace = 'path_with_namespace'
    archived = 'archived'
    branch = 'branch'
    tag = 'tag'
    count = 'count'
    message = 'message'

class Manager:
    def __init__(self, args):
        # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)
        #         pprint.pprint(vars(self))

        self.git_root = os.path.abspath(self.git_root)
        self.total_count = 0
        self.need_to_process = []

    def process(self):
        op = gitlab.Gitlab(self.src, private_token=self.token)
        if not self.to_statistic:
            if self.prj_ids:
                for prj_id in self.prj_ids:
                    project = op.projects.get(prj_id)
                    self.clean_history(project)
            else:
                projects = op.projects.list(all=True)
                # cnt_butt = 4
                # cnt_index = 0
                for item in projects:
                    self.clean_history(item)
                    
                    # cnt_index += 1
                    # if cnt_index >= cnt_butt:
                    #     break
        else:
            projects = op.projects.list(all=True)
            self.collect_statistics(projects)
            print(f'total count: {self.total_count}')
            print(f'neet to process count: {len(self.need_to_process)}')
            pprint.pprint(self.need_to_process)

    def clean_history(self, project):
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

        # 只有本地不存在相关目录才从服务器端同步
        if not os.path.isdir(prj_git_path):
            print(f'to process {path_with_namespace}.')

            if project.archived:
                print(f'{path_with_namespace} is archived and can not been process.')
                return

            if self.to_clean_tag:
                # 如果要清理tag，先删除远程服务器上的tag信息，本地clone的时候就不会存在该信息
                self.clean_tag(project)

            self.checkout(prj_path, path, code_url)
            sync_git.Manager.sync_repo(prj_git_path)
            
            Manager.clean_branch_history(prj_git_path, project)

            print(f'processed {path_with_namespace}.')
        else:
            print(f'{path_with_namespace} already exists.')

    def collect_statistics(self, projects):
        for item in projects:
            self.total_count += 1
            self.collect_project_statistics(item)

    def collect_project_statistics(self, project):
        # 先统计是否有分支不是新初始化的
        # 统计tag是否超出最大值
        # 确认是否是存档的
        
        result = dict()
        to_append = False
        for branch in project.branches.list():
            if branch.commit.message != self.commit_msg:
                to_append = True

                branch_item_info = dict()
                branch_item_info[DataLabel.name] = branch.name
                branch_item_info[DataLabel.message] = branch.commit.message
                result[DataLabel.branch] = branch_item_info
                break
        
        tag_count = len(project.tags.list())
        if tag_count > self.max_tag_count or project.archived:
            to_append = True

        if to_append:
            result[DataLabel.tag] = tag_count
            result[DataLabel.archived] = project.archived
            self.need_to_process.append(result)

    @staticmethod
    def get_protected_branch_names(project):
        protected_branches = project.protectedbranches.list()
        protected_branch_names = []
        for item in protected_branches:
            protected_branch_names.append(item.name)

        return protected_branch_names

    @staticmethod
    def clean_branch_history(repo_path, project):
        temp_name = 'middle_temp_butt_none_904'
        protected_branch_names = Manager.get_protected_branch_names(project)

        # 先更新git仓库信息
        repo = git.Repo(repo_path)

        # 先获取本地分支信息
        local_branches = repo.branches
        local_map = dict()
        for item in local_branches:
            local_map[item.name] = item

        for k in local_map:
            if k != repo.active_branch.name:
                repo.git.checkout(k)

            repo.git.checkout(temp_name, orphan=True)
            repo.git.add(all=True)
            repo.git.commit('Initial commit.', a=True, m=True)
            repo.git.branch(k, d=True)
            repo.git.branch(k, m=True)
            protected_branch = None
            try:
                if k in protected_branch_names:
                    protected_branch = project.branches.get(k)
                    protected_branch.unprotect()

                repo.git.push('origin', k, f=True)
            finally:
                # 最后恢复分支保护
                if protected_branch:
                    protected_branch.protect()

    def clean_tag(self, project):
        # 先获取受保护的tag列表
        protected_tags = project.protectedtags.list()
        protected_tag_names = []
        for item in protected_tags:
            protected_tag_names.append(item.name)

        # 依次删除tag，如果其受保护，则先解除保护
        tags = project.tags.list()
        for tag in tags:
            if tag.name in protected_tag_names:
                if self.to_reserve_protected_tag:
                    continue

                tag.unprotect()

            tag.delete()

    def checkout(self, prj_path, path, code_url):
        prj_git_root = os.path.join(prj_path, path)
        if not os.path.isdir(prj_path):
            os.makedirs(prj_path)
            
        try:
            git.Repo.clone_from(code_url, prj_git_root)
        except git.exc.GitCommandError as e:
            print(str(e))


def main(args):
    manager = Manager(args)
    manager.process()


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='clean gitlab repository history and synchronise to remote')
    parser.add_argument('src', metavar='src', help='source gitlab server')
    parser.add_argument('token', metavar='token', help='source gitlab server token')
    parser.add_argument('git_root', metavar='git_root', help='git root directory')
    
    process_group = parser.add_mutually_exclusive_group()
    process_group.add_argument('--clean_tag', dest='to_clean_tag', action='store_true', default=False, help='indicate to clean tag')
    process_group.add_argument('--reserve_protected_tag', dest='to_reserve_protected_tag', action='store_true', default=False, help='indicate to reserve protected tag')
    process_group.add_argument('--reprocess', dest='to_reprocess', action='store_true', default=False, help='indicate to reprocess the existing local project')
    process_group.add_argument('--id', dest='prj_ids', action='append', default=None, type=int, help='indicate to clean the project with special id')
    
    statistic_group = parser.add_mutually_exclusive_group()
    statistic_group.add_argument('--statistic', dest='to_statistic', action='store_true', default=False, help='indicate to collect statistics')
    statistic_group.add_argument('--commit_msg', dest='commit_msg', action='store', default='Initial commit.\n', type=str, help='to specify the commit message')
    statistic_group.add_argument('--max_tag_count', dest='max_tag_count', action='store', default=3, type=int, help='to specify the maximum tag count')

    # parser.print_help()

    return parser.parse_args(src_args)


if __name__ == '__main__':
    test_args = None
    args = get_args(test_args)
    trivial_util.measure_time(main, args)