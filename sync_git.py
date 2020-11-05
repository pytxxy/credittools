import argparse
import os
import git
import time

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

class Manager:
    HEAD_NAME = 'HEAD'
    def __init__(self, args):
        # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)
        # pprint.pprint(vars(self))

        self.work_path = os.path.abspath(self.work_path)

    def process(self):
        # 先更新git仓库信息
        repo = git.Repo(self.work_path)
        repo.git.fetch(all=True)

        # 先获取远程分支信息以及本地分支信息
        origin = repo.remote()
        remote_branches = origin.refs
        local_branches = repo.branches
        remote_map = dict()
        for item in remote_branches:
            pure_name = self._get_pure_name(item.name)
            remote_map[pure_name] = item

        local_map = dict()
        for item in local_branches:
            local_map[item.name] = item

        # 除了head分支，如果本地分支没有相应的远程分支，则创建，如果有则更新覆盖。
        for k in remote_map:
            if k != Manager.HEAD_NAME:
                if k in local_map:
                    if k == repo.active_branch.name:
                        repo.git.reset(remote_map[k].name, hard=True)
                        repo.git.pull()
                    else:
                        repo.git.checkout(k)
                        repo.git.reset(remote_map[k].name, hard=True)
                        repo.git.pull()
                else:
                    repo.git.checkout(remote_map[k].name, b=k, f=True)

        # 如果远程没有相应的本地分支，则删除本地分支。
        for item in local_map:
            if item not in remote_map:
                repo.git.branch(item, d=True)

    def _get_pure_name(self, whole_name):
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