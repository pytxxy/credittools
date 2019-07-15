# -*- coding:UTF-8 -*-

'''
Created on 2019年4月15日

@author: caifh
'''

"""
更新PyPI的大体步骤如下：
前期准备工作：
1.安装twine，具体如下：
  linux: python3 -m pip install --user --upgrade twine
  windows: py -3 -m pip install --upgrade twine
2.版本名称规范：
  PEP 440 -- Version Identification and Dependency Specification(https://www.python.org/dev/peps/pep-0440/)
  [N!]N(.N)*[{a|b|rc}N][.postN][.devN]
  ^((?:\d+!)?\d+(?:\.\d+)*)(?:(?:(?:a)|(?:b)|(?:r?c))\d+)?(?:\.post\d+)?(?:\.dev\d+)?$

具体操作：
1.更新当前git库(可选，依赖于是本地直接上传，还是从远程更新上传)；
2.更新版本编号；
3.使用“python setup.py sdist bdist_wheel”命令行执行打包操作；
4.可以使用“twine upload --repository-url https://test.pypi.org/legacy/ dist/bc_dock_util-0.0.9*”先上传到测试环境进行验证(也可以使用“twine upload --repository-url https://test.pypi.org/legacy/ dist/*”对所有打包文件执行上传操作)；
5.上传正式环境使用命令为“twine upload --repository-url https://upload.pypi.org/legacy/ dist/bc_dock_util-0.0.9*”（可以简化为“twine upload dist/bc_dock_util-0.0.9*”）；
6.上传成功，也需要同步更新github相应配置里的版本号，该方式可选；

官方新建模块帮助文档链接如下：
https://packaging.python.org/tutorials/packaging-projects/

特别说明：
1.当前该脚本可在windows7环境下面可用，且需确保默认python可执行程序是python3版本；

使用样例:
update_pypi.bat -u --vername 0.0.9b1.dev1 -b -t --upload -c --branch master D:\work\bc_dock_util

从测试地址安装模块样例
pip3 install --index-url https://test.pypi.org/simple/ your-package
pip3 install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple your-package
pip3 install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple bc_dock_util
pip3 install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple  -U bc_dock_util
pip3 install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple bc_dock_util==0.0.7
"""

import argparse
import os
import re
import subprocess
import time
import glob

import creditutils.trivial_util as utility
import creditutils.file_util as file_util
import creditutils.git_util as git_util
import creditutils.exec_cmd as exec_cmd

class Manager:
    VER_PTN_STR = '^((?:\d+!)?\d+(?:\.\d+)*)(?:(?:(?:a)|(?:b)|(?:r?c))\d+)?(?:\.post\d+)?(?:\.dev\d+)?$'

    def __init__(self, args):
        # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)
    
        self.src = os.path.abspath(self.src)
        self.git_root = self.src
        self.module_name = None
        self.target_url_formal = 'https://upload.pypi.org/legacy/'
        self.target_url_test = 'https://test.pypi.org/legacy/'

        setup_name = 'setup.py'
        self.setup_path = os.path.join(self.git_root, setup_name)

        self.init_path = None
        self.main_ver = None
        
    def process(self):
        if self.to_update:
            # 先进行代码更新操作
            git_util.revert(self.git_root)
            git_util.update(self.git_root, None, self.branch)

        if not self.ver_name:
            setup_content = file_util.read_file_content(self.setup_path)
            self.ver_name = self._get_version_name(setup_content)

        # 先校验设置的版本格式是否正确
        if not self.is_valid_version(self.ver_name):
            raise Exception(f'the verion {self.ver_name} is invalid!')

        self.main_ver = self.get_main_version(self.ver_name)

        is_updated = self.update_module_version(self.ver_name)
        if is_updated:
            print(f'updated version name with {self.ver_name}.')
        else:
            print(f'remain version name as {self.ver_name}.')

        if self.to_clean:
            self.clean_builds()

        if self.to_build:
            self.build_wheel()

        if self.to_upload:
            self.upload_to_pypi()

        if self.to_commit:
            self.commit_to_repo()

    @staticmethod
    def get_main_version(version):
        re_ptn = Manager.VER_PTN_STR
        result = re.match(re_ptn, version)
        if result:
            return result.group(1)
        else:
            return None

    @staticmethod
    def is_valid_version(version):
        re_ptn = Manager.VER_PTN_STR
        result = re.match(re_ptn, version)
        if result:
            return True
        else:
            return False

    def update_module_version(self, version):
        setup_content = file_util.read_file_content(self.setup_path)
        self.module_name = self._get_module_name(setup_content)
        if not self.module_name:
            raise Exception('to get module name failed!')

        return self.update_setup_version(self.setup_path, version)
        
        # init_name = '__init__.py'
        # self.init_path = os.path.join(self.git_root, self.module_name, init_name)
        # return self.update_init_version(self.init_path, version)

    def _get_module_name(self, data):
        # example: name='creditutils'
        re_ptn = 'name\s*=\s*[\'\"](\w+)[\'\"]'
        result = re.search(re_ptn, data)
        if result:
            return result.group(1)
        else:
            return None

    def _get_version_name(self, data):
        # example: version='0.0.11'
        re_ptn = 'version\s*=\s*[\'\"]([^\'\"]*)[\'\"]'
        result = re.search(re_ptn, data)
        if result:
            return result.group(1)
        else:
            return None

    def update_setup_version(self, file_path, version):
        # example: version='0.0.2'
        re_ptn = '(version\s*=\s*[\'\"])([^\'\"]*)([\'\"])'
        src_data = file_util.read_file_content(file_path)
        new_data = re.sub(re_ptn, '\g<1>{}\g<3>'.format(version), src_data)
        if new_data != src_data:
            file_util.write_to_file(file_path, new_data, 'utf-8')
            return True
        else:
            return False

    def update_init_version(self, file_path, version):
        # example: version_info = (0, 0, 9)
        re_ptn = '(version_info\s*=\s*\()(\d+(?:,\s*\d+){2})(\))'
        src_data = file_util.read_file_content(file_path)
        target_version = ', '.join(re.split('\.\s*', version))
        new_data = re.sub(re_ptn, f'\g<1>{target_version}\g<3>', src_data)
        if new_data != src_data:
            file_util.write_to_file(file_path, new_data, 'utf-8')
            return True
        else:
            return False
    
    @staticmethod
    def list_file(curr_dir, name_ptn):
        for i in glob.glob(os.path.join(curr_dir, name_ptn)):
            yield i

    def clean_builds(self):
        curr_dir = os.path.join(self.git_root, 'dist')
        name_ptn = f'{self.module_name}-{self.ver_name}*'
        for item in self.list_file(curr_dir, name_ptn):
            # print(item)
            os.remove(item)

    def build_wheel(self):
        cmd_str = 'python setup.py sdist bdist_wheel'
        result = exec_cmd.run_cmd_for_code_in_specified_dir(self.git_root, cmd_str)
        if result != 0:
            raise Exception('build wheel failed!')

    def upload_to_pypi(self):
        if self.is_test:
            target_url = self.target_url_test
        else:
            target_url = self.target_url_formal

        time_to_wait = 120
        cmd_str = f'twine upload --repository-url {target_url} dist/{self.module_name}-{self.ver_name}*'
        result = subprocess.run(cmd_str, shell=True, cwd=self.git_root, timeout=time_to_wait)
        if result.returncode != 0:
            raise Exception('upload to pypi failed!')

    def commit_to_repo(self):
        git_root = self.git_root

        # 先判断git目录状态是否正常
        if not git_util.is_repository(git_root):
            raise Exception(f'{git_root} is not a valid git source directory!')

        setup_path = self.setup_path[len(git_root):]
        # init_path = self.init_path[len(git_root):]
        relative_setup_path = self.get_relative_path(setup_path)
        # relative_init_path = self.get_relative_path(init_path)

        paths = []            
        paths.append(relative_setup_path)
        # paths.append(relative_init_path)
        msg = f'updated {self.module_name} version with {self.ver_name}.'
        git_util.push_to_remote(paths, msg, repository=None, refspecs=None, _dir=git_root)

    def get_relative_path(self, ori_path):
        mid_path = file_util.normal_unix_path(ori_path)
        if mid_path.startswith(file_util.unix_sep):
            result = mid_path[len(file_util.unix_sep):]
        else:
            result = mid_path

        return result


def test_upload_to_pypi():
    target_url = 'https://test.pypi.org/legacy/'
    module_name = 'bc_dock_util'
    ver_name = '0.0.10'
    git_root = 'D:\\work\\bc_dock_util'
    cmd_str = f'twine upload --repository-url {target_url} dist/{module_name}-{ver_name}*'
    # result = exec_cmd.run_cmd_for_code_in_specified_dir(git_root, cmd_str)
    # if result != 0:
        # raise Exception('upload to pypi failed!')

    # proc = subprocess.Popen(cmd_str, stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True, universal_newlines=True, cwd=git_root)
    proc = subprocess.Popen(cmd_str.split(), stdin=subprocess.PIPE, cwd=git_root)
    try:
        time.sleep(3)
        # print(proc.stdout.readline())
        proc.stdin.write(b'caifh\n')
        # proc.stdin.write(b'dir\n')
        proc.stdin.flush()
        # print(proc.poll())
        time.sleep(3)
        # print(proc.stdout.readline())
        proc.stdin.write(b'Temp19811205\n')
        # proc.stdin.write(b'cd ..\n')
        proc.stdin.flush()
        # print(proc.stdout.readline())
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        outs, errs = proc.communicate()
        print(f'outs: {outs}, errs: {errs}.')


def test_upload_to_pypi_with_pexpect():
    # 本来想实现自动输入用户名和密码的功能，实际验证发现不可行，当前先使用手动输入用户名和密码方案
    # import pexpect
    # target_url = 'https://test.pypi.org/legacy/'
    # module_name = 'bc_dock_util'
    # ver_name = '0.0.10'
    # cmd_str = f'twine upload --repository-url {target_url} dist/{module_name}-{ver_name}*'

    # child = pexpect.spawn(cmd_str)
    # child.expect('Enter your username:')
    # child.sendline('caifh')
    # child.expect('Enter your password:')
    # child.sendline('Temp19811205')
    pass


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='update the module in python package index.')
    
    parser.add_argument('src', metavar='src', help='the source directory to process.')
    parser.add_argument('-u', dest='to_update', action='store_true', default=False,
                        help='indicate to get or update code firstly')
    parser.add_argument('--vername', metavar='ver_name', dest='ver_name', help='version name')
    parser.add_argument('-b', dest='to_build', action='store_true', default=False, help='indicate to build')
    parser.add_argument('-t', dest='is_test', action='store_true', default=False,
                        help='indicate to upload to test repository')
    parser.add_argument('--clean', dest='to_clean', action='store_true', default=False,
                        help='indicate to clean existing builds')
    parser.add_argument('--upload', dest='to_upload', action='store_true', default=False,
                        help='indicate to upload build files to pypi')
    parser.add_argument('-c', dest='to_commit', action='store_true', default=False,
                        help='indicate to commit to repository')
    parser.add_argument('--branch', metavar='branch', dest='branch', default='master', help='code branch name')

#     parser.print_help()

    return parser.parse_args(src_args)    


def main(args):
    manager = Manager(args)
    manager.process()

    
if __name__ == '__main__':
    # test_args = 'a b -i -u'.split()
    test_args = None
    args = get_args(test_args)
    utility.measure_time(main, args)
