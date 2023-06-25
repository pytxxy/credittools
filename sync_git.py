import argparse
import os
import git
import time
import creditutils.exec_cmd as exec_cmd

'''
同步远程仓库代码到本地git仓库，包括所有分支信息。
'''

# 获取以秒为单位的两个时间点之间的差值，返回以XXmXXs的时间格式字符串
def get_time_info(begin, end):
    elapsed = end - begin
    sec_per_min = 60
    m = elapsed // sec_per_min
    s = elapsed % sec_per_min
    time_info = '{}m{}s'.format(round(m), round(s))
    return time_info

def measure_time(func, *args, **dicts):
    begin = time.time()

    func(*args, **dicts)

    end = time.time()
    time_info = get_time_info(begin, end)

    # 输出总用时
    print('===Finished. Total time: {}==='.format(time_info))

def is_repository(_dir='.'):
    try:
        _dir = os.path.abspath(_dir)
        _ = git.Repo(_dir).git_dir
        return True
    except git.exc.InvalidGitRepositoryError:
        return False


class Manager:
    HEAD_NAME = 'HEAD'
    def __init__(self, args):
        # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)
        # pprint.pprint(vars(self))

        self.work_path = os.path.abspath(self.work_path)

    def process(self):
        if not os.path.isdir(self.work_path):
            raise Exception(f'{self.work_path} is not a directory!')

        if is_repository(self.work_path):
            Manager.sync_repo(self.work_path)
        else:
            Manager.sync_repo_recursive(self.work_path)

    @staticmethod
    def sync_repo_recursive(repo_path):
        file_list = os.listdir(repo_path)
        for filename in file_list:
            temp_file_path = os.path.join(repo_path, filename)
            if os.path.isdir(temp_file_path):
                if is_repository(temp_file_path):
                    Manager.sync_repo(temp_file_path)
                else:
                    Manager.sync_repo_recursive(temp_file_path)
    
    @staticmethod
    def _get_other_branch_name(git_map, curr_name):
        other = None
        for item in git_map:
            if item != curr_name:
                other = item
                break

        return other
    
    @staticmethod
    def sync_repo(repo_path):
        # 先更新git仓库信息
        repo = git.Repo(repo_path)
        print(f'to synchronize {repo_path}.')
        repo.git.fetch(all=True)

        # 先获取远程分支信息以及本地分支信息
        origin = repo.remote()
        remote_branches = origin.refs
        local_branches = repo.branches
        remote_map = dict()
        for item in remote_branches:
            pure_name = Manager._get_pure_name(item.name)
            remote_map[pure_name] = item

        local_map = dict()
        for item in local_branches:
            local_map[item.name] = item

        # 除了head分支，如果本地分支没有相应的远程分支，则创建，如果有则更新覆盖。
        for k in remote_map:
            if k != Manager.HEAD_NAME:
                if k in local_map:
                    try:
                        repo.git.reset(Manager.HEAD_NAME, hard=True)
                        if k == repo.active_branch.name:
                            repo.git.pull()
                        else:
                            repo.git.checkout(k)
                            repo.git.pull()
                    except git.exc.GitCommandError as e:
                        # 在pull同步出错的条件下，先将当前工作区切换到其他分支，再删除当前分支，然后重新从服务器拉取该分支
                        other = Manager._get_other_branch_name(local_map, k)
                        if other:
                            repo.git.checkout(other)
                            repo.git.branch(k, D=True)
                            repo.git.checkout(remote_map[k].name, b=k, f=True)
                        else:
                            raise e
                    finally:
                        pass
                else:
                    repo.git.checkout(remote_map[k].name, b=k, f=True)

        # 如果远程没有相应的本地分支，则删除本地分支。
        for item in local_map:
            if item not in remote_map:
                repo.git.branch(item, D=True)

        # 展示当前存在多少条tag
        # i = 0
        # for tag in repo.tags:
        #     print(f'index({i}): {tag.name}')
        #     i += 1
    
    @staticmethod
    def push_to_remote(repo_path):
        # 先更新git仓库信息
        repo = git.Repo(repo_path)

        # 先获取本地分支信息
        # local_branches = repo.branches
        # local_map = dict()
        # for item in local_branches:
        #     local_map[item.name] = item

        # 将本地分支推送到远端。
        # for k in local_map:
        #     if k == repo.active_branch.name:
        #         repo.git.push()
        #     else:
        #         repo.git.checkout(k)
        #         repo.git.push()
        
        repo.git.push(all=True)
        
        # 同步本地tag到远端
        exec_cmd.run_cmd_with_system_in_specified_dir(repo_path, 'git push origin --tags', True)

    @staticmethod
    def _get_pure_name(whole_name):
        if whole_name:
            str_array = whole_name.split('/')
            return str_array[-1]
        else:
            return None

def main(args):
    manager = Manager(args)
    manager.process()


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='synchronize git repository with remote if need.')
    parser.add_argument('work_path', metavar='work_path', help='working directory')

    #     parser.print_help()

    return parser.parse_args(src_args)


if __name__ == '__main__':
    test_args = None
    args = get_args(test_args)
    measure_time(main, args)