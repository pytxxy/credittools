import creditutils.git_util as git
import creditutils.file_util as file
import creditutils.str_util as str_utils
import os
import re
import argparse
import time
import xmltodict
import ast
import subprocess
import sys


class BuildConfigParser:
    ROOT_FLAG = 'pod'

    def __init__(self, config_path):
        self.config_path = config_path

    def parse(self):
        doc = xmltodict.parse(file.read_file_content(self.config_path))
        self.data = doc[BuildConfigParser.ROOT_FLAG]

    def get_config(self):
        return self.data


class ConfigBuildManager:

    def __init__(self, args):
        # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)

        self.work_path = os.path.abspath(self.work_path)
        commit_config_dirs = ['config', 'base', 'commit_config.xml']
        self.commit_config = os.sep.join(commit_config_dirs)
        self.commit_config = self.work_path + os.sep + self.commit_config
        config_parser = BuildConfigParser(self.commit_config)
        config_parser.parse()
        self.pod_config = config_parser.get_config()
        self.tag_info = {}

    def process(self):
        temp_branch_dict = {}
        temp_tag_dict = {}
        if self.branch_dict:
            temp_branch_dict = ast.literal_eval(self.branch_dict)

        if self.tag_dict:
            temp_tag_dict = ast.literal_eval(self.tag_dict)

        for pod_name in self.pod_name:
            branch_name = 'master'
            if pod_name in temp_branch_dict.keys():
                branch_name = temp_branch_dict[pod_name]

            if pod_name in temp_tag_dict.keys():
                self.tag_info[pod_name] = temp_tag_dict[pod_name]
                break

            source_path = self.work_path + os.sep + pod_name
            source_path = file.normalpath(source_path)
            git.checkout_or_update(source_path, self.get_remote_url(pod_name), branch=branch_name)
            git_root = git.get_git_root(source_path)

            os.chdir(git_root)
            subprocess.call(['git', 'fetch', '--tags'])
            
            new_push_version = git.get_revision(git_root)
            new_tags_info = git.get_newest_tag_revision(git_root)
            new_push_tag = ''

            # 当前仓库有没有打过tag
            if new_tags_info:
                new_push_tag = new_tags_info[1]
                # 最新提交的版本没有打过tag
                print(new_push_version, new_tags_info)
                if new_push_version != new_tags_info[0]:
                    new_tag = new_tags_info[1].split('.')
                    tag_num = int(new_tag[len(new_tag) - 1]) + 1
                    temp_tag = []
                    for i, val in enumerate(new_tag):
                        if i != len(new_tag) - 1:
                            temp_tag.append(val)
                        else:
                            temp_tag.append(format(tag_num))
                    new_tag = '.'.join(temp_tag)
                    new_push_tag = new_tag
                    self.change_podspec_version(new_tag, source_path)

            # 获取远程pod库版本信息
            os.chdir(git_root)
            rtn_str = subprocess.check_output(['pod', 'search', pod_name], universal_newlines=True)
            version_str = re.search(r'\s+-\s+Versions:.+[PYPodSpec repo]]', rtn_str).group()
            is_revision_upload = False
            for detail_ver in version_str.split(','):
                if new_push_tag in detail_ver.strip():
                    is_revision_upload = True
            if not is_revision_upload:
                try:
                    ret_code = subprocess.check_call(['sh', 'push.sh'])
                    print(ret_code)
                except Exception as e:
                    print('return_code:', e.returncode)
                    sys.exit(0)


            self.tag_info[pod_name] = new_push_tag

        if self.podfile_path:
            for pod_name_key in self.tag_info.keys():
                file_data = file.read_file_content(self.podfile_path)
                version_line_arr = re.search(r"(pod\s+\'({}|{}.+)\'\,\s+\'([0-9]|\.)+\')".format(pod_name_key, pod_name_key), file_data)
                if version_line_arr:
                    pod_version_line = version_line_arr.group()
                    new_spec_version_line = re.sub(r'([0-9]\.|[0-9])+', self.tag_info[pod_name_key], pod_version_line)
                    src_dst_list = list(zip([pod_version_line], [new_spec_version_line]))
                    file.replace_string_in_file(self.podfile_path, src_dst_list)
            dir_name = os.path.dirname(os.path.dirname(self.podfile_path))
            git_root = git.get_git_root(dir_name)
            os.chdir(git_root)
            if git.has_change(git_root):
                git.push_to_remote([self.podfile_path], '[other]: Podfile文件更新', repository=None, refspecs=None, _dir=git_root)


    def change_podspec_version(self, tag_version, source_path):
        source_path = git.get_git_root(source_path)
        file_list = file.get_file_list(source_path)
        for file_name in file_list:
            if file_name.endswith('.podspec'):
                spec_file = os.path.join(source_path, file_name)
                file_data = file.read_file_content(spec_file)
                spec_version_line = re.search(r'([a-z]*).version\s+=\s+\W([0-9].+)', file_data).group()
                new_spec_version_line = re.sub(r'([0-9]\.|[0-9])+', tag_version, spec_version_line)
                src_dst_list = list(zip([spec_version_line], [new_spec_version_line]))
                file.replace_string_in_file(spec_file, src_dst_list)
            try:
                git.push_to_remote([spec_file], '[other]: 提交{}版本'.format(tag_version), repository=None, refspecs=None, _dir=source_path)
                git.git_push_tag(source_path, tag_version)
            except Exception as e:
                raise Exception(e)

    def get_remote_url(self, pod_name):
        pod_item = self.pod_config[pod_name]
        if pod_item:
            return pod_item['remote']
        return ''


class BuildManager:
    def __init__(self, build_dict):
        self.__dict__ = build_dict


def push_pod_tag_to_remote(work_path, podfile_path, pod_name, branch_dict=None, tag_dict=None):
    test_args = {'work_path': work_path,
                 'podfile_path': podfile_path,
                 'pod_name': pod_name,
                 'branch_dict': branch_dict,
                 'tag_dict': tag_dict}
    build_manager = BuildManager(test_args)
    print(vars(build_manager))

    main(build_manager)

def main(args):
    manager = ConfigBuildManager(args)
    manager.process()


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='pod tag and push.')
    parser.add_argument('work_path', metavar='work_path', help='working directory')
    parser.add_argument('--podfile', metavar='podfile_path', dest='podfile_path', help='podfile_path_path')
    parser.add_argument('--pod',     metavar='pod_name',  nargs='+',  dest='pod_name', default=[], help='pod name array')
    parser.add_argument('--branch',  metavar='branch_dict',    type=str,  dest='branch_dict',   default=[], help='pod branch name')
    parser.add_argument('--tag',     metavar='tag_dict',  type=str,   dest='tag_dict',   help='tag name dict eg:{pod_name:tag_name}')
    return parser.parse_args(src_args)


if __name__=='__main__':
    begin = time.time()
    test_args = None
    args = get_args(test_args)
    main(args)
    end = time.time()

    time_info = str_utils.get_time_info(begin, end)

    # 输出总用时
    print('===Finished. Total time: {}==='.format(time_info))













