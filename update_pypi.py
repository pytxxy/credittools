# -*- coding:UTF-8 -*-

'''
Created on 2019年4月15日

@author: caifh
'''

"""
更新PyPI的大体步骤如下：
1.更新当前git库(可选，依赖于是本地直接上传，还是从远程更新上传)；
2.更新版本编号；
3.使用“python setup.py sdist bdist_wheel”命令行执行打包操作；
4.可以使用“twine upload --repository-url https://test.pypi.org/legacy/ dist/bc_dock_util-0.0.9*”先上传到测试环境进行验证(也可以使用“twine upload --repository-url https://test.pypi.org/legacy/ dist/*”对所有打包文件执行上传操作)；
5.上传正式环境使用命令为“twine upload --repository-url https://upload.pypi.org/legacy/ dist/bc_dock_util-0.0.9*”（可以简化为“twine upload dist/bc_dock_util-0.0.9*”）；
6.上传成功，也需要同步更新github相应配置里的版本号，该方式可选；
"""

import argparse
import os
import re
import creditutils.trivial_util as utility
import creditutils.file_util as file_util
import creditutils.git_util as git_util

class Manager:
    
    def __init__(self, args):
        # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)
    
        self.src = os.path.abspath(self.src)
        self.git_root = self.src
        self.module_name = None
        
    def process(self):
        if self.to_update:
            # 先进行代码更新操作
            git_util.revert(self.git_root)
            git_util.update(self.git_root, None, self.branch)

        # 先校验设置的版本格式是否正确
        if not self.is_valid_version(self.ver_no):
            raise Exception('the verion {} is invalid!'.format(self.ver_no))

        self.update_module_name(self.ver_no)

    def is_valid_version(self, version):
        ver_re = '\d+(?:\.\d+){2}'
        result = re.match(ver_re, version)
        if result:
            return True
        else:
            return False

    def update_module_name(self, version):
        setup_name = 'setup.py'
        setup_path = os.path.join(self.git_root, setup_name)
        setup_content = file_util.read_file_content(setup_path)
        self.module_name = self._get_module_name(setup_content)
        if not self.module_name:
            raise Exception('to ge module name failed!')

        self.update_setup_version(setup_path, version)
        
        init_name = '__init__.py'
        init_path = os.path.join(self.git_root, self.module_name, init_name)
        self.update_init_version(init_path, version)

    def _get_module_name(self, data):
        # example: name='creditutils'
        re_ptn = 'name\s*=\s*[\'\"](\w+)[\'\"]'
        result = re.search(re_ptn, data)
        if result:
            return result.group(1)
        else:
            return None

    def update_setup_version(self, file_path, version):
        # example: version='0.0.2'
        re_ptn = '(version\s*=\s*[\'\"])(\d+(?:\.\d+){2})([\'\"])'
        src_data = file_util.read_file_content(file_path)
        new_data = re.sub(re_ptn, '\g<1>{}\g<3>'.format(version), src_data)
        if new_data != src_data:
            file_util.write_to_file(file_path, new_data, 'utf-8')

    def update_init_version(self, file_path, version):
        # example: version_info = (0, 0, 9)
        re_ptn = '(version_info\s*=\s*[\'\"]\())(\d+(?:,\s*\d+){2})(\))'
        src_data = file_util.read_file_content(file_path)
        target_version = ', '.join(re.split('\.\s*', version))
        new_data = re.sub(re_ptn, '\g<1>{}\g<3>'.format(target_version), src_data)
        if new_data != src_data:
            file_util.write_to_file(file_path, new_data, 'utf-8')
    
            
# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='update the module in python package index.')
    
    parser.add_argument('src', metavar='src', help='the source directory to process.')
    parser.add_argument('-u', dest='to_update', action='store_true', default=False,
                        help='indicate to get or update code firstly')
    parser.add_argument('--verno', metavar='ver_no', dest='ver_no', type=int, default=0, help='version release number')
    parser.add_argument('-t', dest='is_test', action='store_true', default=False,
                        help='indicate to upload to test repository')
    parser.add_argument('-c', dest='to_commit', action='store_true', default=False,
                        help='indicate to commit to repository')
    parser.add_argument('--branch', metavar='branch', dest='branch', default='master', help='code branch name')

#     parser.print_help()

    return parser.parse_args(src_args)    

def main(args):
    manager = Manager(args)
    manager.process()

    
if __name__ == '__main__':
#     test_args = 'a b -i -u'.split()
    test_args = None
    args = get_args(test_args)
    utility.measure_time(main, args)
