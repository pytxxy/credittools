'''
Created on 2015年7月8日

@author: caifh
'''
import argparse
import os
import re
import creditutils.file_util as file_util
import tempfile
import creditutils.zip_util as zip_util
import shutil
import creditutils.svn_util as svn
import creditutils.git_util as git
# import filecmp
import xmltodict
import creditutils.trivial_util as utility

# 标识打包类型，是单独打包，还是一次性完成所有打包
_PACK_TYPE_ALL = 0
_PACK_TYPE_SERVER = 1
_PACK_TYPE_ANDROID = 2
_PACK_TYPE_IOS = 3

_PACK_SUB_DIRS = {
    _PACK_TYPE_SERVER: 'server',
    _PACK_TYPE_ANDROID: 'android',
    _PACK_TYPE_IOS: 'ios'
}

_PACK_FLAGS = {
    _PACK_TYPE_SERVER: '',
    _PACK_TYPE_ANDROID: 'android',
    _PACK_TYPE_IOS: 'ios'
}

_PACK_VER_BASE_FILE = 'ver_base.txt'

_PACK_FILTER_OUT = [
    _PACK_VER_BASE_FILE,
    '.svn'
]

_PACK_VER_FILE = 'version.txt'

_PACK_TARGET_ROOT_NAME = 'config_file'
_PACK_TARGET_FILE = _PACK_TARGET_ROOT_NAME + '.zip'
_SVN_UPDATE_MSG = '[Other]:update config'

_UPLOAD_TYPE_NONE = 0
_UPLOAD_TYPE_ALL = 1
_UPLOAD_TYPE_ANDROID = 2
_UPLOAD_TYPE_IOS = 3
_UPLOAD_SUB_DIRS = {
    _UPLOAD_TYPE_ANDROID: 'android',
    _UPLOAD_TYPE_IOS: 'ios'
}


class FileMap:
    _src_ptn_fmt = '^[\.\w\-]+({})?(\.\w+)?({}[\.\w\-]+({})?(\.\w+)?)*$'

    def __init__(self, flag, src_root, dst_root):
        self.flag = flag
        self.src_root = src_root
        self.dst_root = dst_root

        self.flag_at = '@'
        self.flag_with_pre = self.flag_at + self.flag
        self.esc_flag_with_pre = re.escape(self.flag_with_pre)
        self.esc_sep = re.escape(os.sep)
        self.ptn = re.compile(FileMap._src_ptn_fmt.format(self.esc_flag_with_pre, self.esc_sep, self.esc_flag_with_pre))

    def __call__(self, src_path):
        ref_path = src_path
        if src_path:
            if src_path.startswith(self.src_root):
                ref_path = src_path[len(self.src_root) + 1:]

            if self.flag:
                if self.flag_at in ref_path:
                    match = self.ptn.match(ref_path)
                    if match:
                        return self.dst_root + os.sep + ref_path.replace(self.flag_with_pre, '')
                    else:
                        to_filter = False
                        for pack_type in _PACK_FLAGS:
                            flag_item = _PACK_FLAGS[pack_type]
                            if not flag_item:
                                continue
                            else:
                                if flag_item == self.flag:
                                    continue
                                else:
                                    flag_item_with_pre = self.flag_at + flag_item
                                    if flag_item_with_pre in ref_path:
                                        to_filter = True
                                        break

                        if to_filter:
                            return None
                        else:
                            return self.dst_root + os.sep + ref_path
                else:
                    return self.dst_root + os.sep + ref_path
            else:
                return self.dst_root + os.sep + ref_path
        else:
            return None


class FileCopy:
    def __init__(self, map_func):
        self.map_func = map_func

    def __call__(self, filepath):
        dst_path = self.map_func(filepath)
        if dst_path:
            file_util.replace_file(filepath, dst_path)


class BuildConfigParser:
    ROOT_FLAG = 'config'
    WORKSPACE_FLAG = 'workspace'
    SOURCE_PATH_FLAG = 'source_path'
    TARGET_PATH_FLAG = 'target_path'
    SVN_URL_FLAG = 'svn_url'

    def __init__(self, config_path):
        self.config_path = config_path

    def parse(self):
        doc = xmltodict.parse(file_util.read_file_content(self.config_path))
        self.data = doc[BuildConfigParser.ROOT_FLAG]

    def get_config(self):
        return self.data


class CommitManager:
    BRANCH_FLAG = 'branch'
    ITEM_FLAG = 'item'
    TYPE_FLAG = 'type'
    URL_FLAG = 'url'
    FOLDER_NAME_FLAG = 'folder_name'
    RELATIVE_PATH_FLAG = 'relative_path'

    _TYPE_SVN = 'svn'
    _TYPE_GIT = 'git'

    def __init__(self, args):
        for name, value in vars(args).items():
            setattr(self, name, value)

        # 解析提交配置管理文件
        self.work_path = os.path.abspath(self.work_path)

        if not self.commit_config:
            commit_config_dirs = ['base', 'commit_config.xml']
            self.commit_config = os.sep.join(commit_config_dirs)

        self.commit_config = self.work_path + os.sep + self.commit_config
        self.repository = self.work_path + os.sep + 'repository'

        # 已成功提交分支路径数组
        self.success_upload_path_arr = []

    def get_item_info(self, upload_flag):
        # 先解析配置
        configParser = BuildConfigParser(self.commit_config)
        configParser.parse()
        ori_commit_config = configParser.get_config()
        branch_items = ori_commit_config[CommitManager.BRANCH_FLAG]
        if upload_flag in branch_items:
            sub_items = branch_items[upload_flag]
            if sub_items and CommitManager.ITEM_FLAG in sub_items:
                return sub_items[CommitManager.ITEM_FLAG]

        return None

    # 解析相关xml数据，执行提交操作
    def commit(self, item_key, commit_config, targer_config_path):
        # 判断是不是list
        if isinstance(commit_config, list):
            for item in commit_config:
                self.commit_item(item_key, item, targer_config_path)
        # 判断是不是字典
        elif isinstance(commit_config, dict):
            self.commit_item(item_key, commit_config, targer_config_path)
        else:
            raise Exception("xml error")

    # 为单项配置管理库提交文件
    def commit_item(self, item_key, item, targer_config_path):
        rep_type = item[CommitManager.TYPE_FLAG]
        source_path = self.repository + os.sep + item_key + os.sep + item[CommitManager.FOLDER_NAME_FLAG]
        # 判断目标文件是否重复
        if source_path in self.success_upload_path_arr:
            raise Exception('重复的目标文件夹"{}"，请检查xml配置文件!'.format(source_path))

        if CommitManager._TYPE_SVN == rep_type.lower():
            self.commit_with_svn(item[CommitManager.URL_FLAG], source_path, targer_config_path)
        elif CommitManager._TYPE_GIT == rep_type.lower():
            self.commit_with_git(item[CommitManager.URL_FLAG], source_path, item[CommitManager.RELATIVE_PATH_FLAG],
                                 targer_config_path, item[CommitManager.BRANCH_FLAG])
        else:
            raise Exception('Type {} is invalid!'.format(rep_type))

    def commit_with_svn(self, source_url, source_path, targer_config_path):
        print('\n=====svn url {}====='.format(source_url))

        source_path = file_util.normalpath(source_path)
        svn.checkout_or_update(source_path, source_url)
        to_upload_file_path = source_path + os.sep + _PACK_TARGET_FILE
        update_svn_file(to_upload_file_path, targer_config_path, _SVN_UPDATE_MSG)
        self.success_upload_path_arr.append(source_path)

    def commit_with_git(self, source_url, source_path, relative_path, targer_config_path, git_branch_name):
        print('\n=====git url {}====='.format(source_url))
        source_path = source_path + os.sep + git_branch_name
        source_path = file_util.normalpath(source_path)
        git.checkout_or_update(source_path, source_url, branch=git_branch_name)
        git_root = git.get_git_root(source_path)
        relative_file_path = relative_path + os.sep + _PACK_TARGET_FILE
        update_git_file(git_root, relative_file_path, targer_config_path, _SVN_UPDATE_MSG)
        self.success_upload_path_arr.append(source_path)


class ConfigBuildManager:
    def __init__(self, args):
        # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)

        self.work_path = os.path.abspath(self.work_path)

        # 解析基础配置文件路径
        if not self.base_config:
            base_config_dirs = ['base', 'update_config.xml']
            base_config = os.sep.join(base_config_dirs)
        else:
            base_config = self.base_config
        self.base_config = self.work_path + os.sep + base_config

        # 先解析配置
        configParser = BuildConfigParser(self.base_config)
        configParser.parse()
        self.ori_build_config = configParser.get_config()

        # svn配置文件目录
        ori_source_path = self.work_path + os.sep + self.ori_build_config[BuildConfigParser.WORKSPACE_FLAG][
            BuildConfigParser.SOURCE_PATH_FLAG]
        self.source_path = file_util.normalpath(ori_source_path)

        # 目标输出文件夹
        target_path = self.work_path + os.sep + self.ori_build_config[BuildConfigParser.WORKSPACE_FLAG][
            BuildConfigParser.TARGET_PATH_FLAG]
        self.target_path = file_util.normalpath(target_path)

    def process(self):
        # 进行代码更新操作
        if self.is_update:
            svn_url = self.ori_build_config[BuildConfigParser.SVN_URL_FLAG]
            svn.checkout_or_update(self.source_path, svn_url, self.svn_ver)

        process(self.source_path, self.target_path, self.type, self.filter_folders, self.upload_type)


# 获取第一层配置文件目录，返回文件名数组
def get_firstfolderitem(src_dir):
    child_dir_arr = []
    parent_dir = file_util.get_child_dirs(src_dir)
    parent_file = file_util.get_child_files(src_dir)
    parent_folder_arr = parent_dir + parent_file
    for tempdir in parent_folder_arr:
        if tempdir.startswith(src_dir):
            child_dir = tempdir[len(src_dir) + 1:]
            child_dir_arr.append(child_dir)
    return child_dir_arr


def process_item(src_dir, dst_dir, temp_dir, _type, ver_code, filter_folders, filter_out=_PACK_FILTER_OUT,
                 ver_file=_PACK_VER_FILE, target_root_name=_PACK_TARGET_ROOT_NAME, target_file=_PACK_TARGET_FILE):
    temp_target_dir = temp_dir + os.sep + target_root_name
    file_map = FileMap(_PACK_FLAGS[_type], src_dir, temp_target_dir)
    func = FileCopy(file_map)

    child_dir_arr = get_firstfolderitem(src_dir)
    if filter_folders:
        for listfile in child_dir_arr:
            listfile_path = src_dir + os.sep + listfile;
            # 是否在文件排除列表里面
            if listfile in filter_folders:
                # 判断是文件还是文件夹
                if os.path.isfile(listfile_path):
                    shutil.copy(listfile_path, temp_target_dir + os.sep + listfile)
                elif os.path.isdir(listfile_path):
                    shutil.copytree(listfile_path, temp_target_dir + os.sep + listfile)
            else:
                if os.path.isfile(listfile_path):
                    func(listfile_path)
                elif os.path.isdir(listfile_path):
                    file_util.process_dir(listfile_path, func)
    else:
        file_util.process_dir(src_dir, func)

        # 更新配置文件版本号
    if ver_file:
        # 将路径归一化，避免路径分隔符不一致引起问题
        ref_path = os.sep.join(re.split('[\\\/]+', ver_file))
        ver_path = temp_target_dir + os.sep + ref_path
        file_util.write_to_file(ver_path, str(ver_code), 'utf-8')

    # 将要排除的文件去除
    if filter_out:
        for item in filter_out:
            # 将路径归一化，避免路径分隔符不一致引起问题
            ref_path = os.sep.join(re.split('[\\\/]+', item))
            filepath = temp_target_dir + os.sep + ref_path
            if os.path.exists(filepath):
                if os.path.isfile(filepath):
                    os.remove(filepath)
                elif os.path.isdir(filepath):
                    shutil.rmtree(filepath)
            else:
                print('not exists ' + filepath)

        print('filter out files ok')

    # 将整个配置文件打包
    if target_file:
        target_path = dst_dir + os.sep + target_file
        base_target_dir = os.path.dirname(target_path)
        if not os.path.exists(base_target_dir):
            os.makedirs(base_target_dir)

        if os.path.isfile(target_path):
            os.remove(target_path)

        zip_util.zip_dir(temp_dir, target_path)


def get_ver_info(filepath):
    ver_info = file_util.read_file_content(filepath)
    return ver_info.strip()


def is_same_config(file_a, file_b):
    temp_dir_a = tempfile.mkdtemp()
    temp_dir_b = tempfile.mkdtemp()

    ver_rel_path = r'config_file\version.txt'

    ver_file_a = zip_util.unzip_specified_file(file_a, ver_rel_path, temp_dir_a)
    ver_a = get_ver_info(ver_file_a)

    ver_file_b = zip_util.unzip_specified_file(file_b, ver_rel_path, temp_dir_b)
    ver_b = get_ver_info(ver_file_b)

    # Clean up the directory yourself
    shutil.rmtree(temp_dir_a)
    shutil.rmtree(temp_dir_b)

    return ver_a == ver_b


def update_svn_file(target_file, new_file, msg):
    base_dir = os.path.dirname(target_file)
    # 先判断svn目录状态是否正常
    if not svn.status(base_dir):
        raise Exception('{} is not a valid svn source directory!'.format(base_dir))

    #     if not filecmp.cmp(new_svn_file, svn_target_file, shallow=False):
    if not is_same_config(new_file, target_file):
        file_util.replace_file(new_file, target_file)
        svn_paths = []
        svn_paths.append(target_file)
        svn.commit(msg, svn_paths)
    else:
        print('{} and {} is the same!'.format(new_file, target_file))


def update_git_file(git_root, relative_file_path, new_file, msg):
    # 先判断git目录状态是否正常
    if not git.is_repository(git_root):
        raise Exception('{} is not a valid git source directory!'.format(git_root))

    target_file = file_util.normalpath(os.path.join(git_root, relative_file_path))
    if not is_same_config(new_file, target_file):
        file_util.replace_file(new_file, target_file)
        paths = []
        paths.append(relative_file_path)
        git.push_to_remote(paths, msg, repository=None, refspecs=None, _dir=git_root)
    else:
        print('{} and {} is the same!'.format(new_file, target_file))


def process(src_dir, dst_dir, _type=_PACK_TYPE_ALL, filter_folders=[], _upload_type=_UPLOAD_TYPE_NONE):
    # 进行提取，过滤，更新操作
    temp_root = tempfile.gettempdir()
    pack_root = temp_root + os.sep + 'pytxxy_config'

    try:
        if os.path.isdir(pack_root):
            shutil.rmtree(pack_root)

        os.makedirs(pack_root)

        # 先获取当前svn目录的版本号
        ver_base = 0
        ver_base_path = src_dir + os.sep + _PACK_VER_BASE_FILE
        ver_base_str = file_util.read_file_content(ver_base_path)
        match = re.match('^\s*(\d+)\s*$', ver_base_str, re.S)
        if match:
            ver_base = int(match.group(1))
            print('version base is {}.'.format(ver_base))

        svn_ver_code = int(svn.get_revision(src_dir))

        ver_code = ver_base + svn_ver_code
        print('subversion code is {} and version code is {}.'.format(svn_ver_code, ver_code))
        dst_ver_dir = dst_dir + os.sep + str(ver_code)

        upload_target_path_dict = {}
        # 进行整体或单项提取打包操作
        if _type == _PACK_TYPE_ALL:
            for item in _PACK_SUB_DIRS:
                temp_dir = pack_root + os.sep + _PACK_SUB_DIRS[item]
                target_dir = dst_ver_dir + os.sep + _PACK_SUB_DIRS[item]
                process_item(src_dir, target_dir, temp_dir, item, ver_code, filter_folders)
                target_file = _PACK_TARGET_FILE
                target_path = target_dir + os.sep + target_file
                upload_target_path_dict[_PACK_SUB_DIRS[item]] = target_path

        else:
            temp_dir = pack_root + os.sep + _PACK_SUB_DIRS[_type]
            target_dir = dst_ver_dir + os.sep + _PACK_SUB_DIRS[_type]
            process_item(src_dir, target_dir, temp_dir, _type, ver_code, filter_folders)

            target_file = _PACK_TARGET_FILE
            target_path = target_dir + os.sep + target_file
            upload_target_path_dict[_PACK_SUB_DIRS[_type]] = target_path

        commitmanager = CommitManager(args)

        if _upload_type == _UPLOAD_TYPE_ALL:
            for item in _UPLOAD_SUB_DIRS:
                item_key = _UPLOAD_SUB_DIRS[item]
                config_info = commitmanager.get_item_info(item_key)
                if config_info:
                    commitmanager.commit(item_key, config_info, upload_target_path_dict[item_key])
        elif _upload_type != _UPLOAD_TYPE_NONE:
            item_key = _UPLOAD_SUB_DIRS[_upload_type]
            config_info = commitmanager.get_item_info(item_key)
            if config_info:
                commitmanager.commit(item_key, config_info, upload_target_path_dict[item_key])
    finally:
        # 清空临时文件夹内容
        if os.path.isdir(pack_root):
            shutil.rmtree(pack_root)


#             pass

# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='pack configure file.')
    parser.add_argument('work_path', metavar='work_path', help='working directory')
    parser.add_argument('-u', dest='is_update', action='store_true', default=False,
                        help='indicate to update svn firstly')
    parser.add_argument('-R', dest='filter_folders', action='store', default=[], nargs='+',
                        help='the folder you not want to eliminate')
    parser.add_argument('-c', metavar='base_config', dest='base_config',
                        help='base configure file, path relative to work path')
    parser.add_argument('-e', metavar='commit_config', dest='commit_config',
                        help='commit configure file, path relative to work path')
    parser.add_argument('-v', metavar='svn_ver', dest='svn_ver', action='store', default=None,
                        help='indicate updating to special version')

    src_group = parser.add_mutually_exclusive_group()
    src_group.add_argument('-s', dest='type', action='store_const', default=_PACK_TYPE_ALL, const=_PACK_TYPE_SERVER,
                           help='indicate to pack server configure file')
    src_group.add_argument('-a', dest='type', action='store_const', default=_PACK_TYPE_ALL, const=_PACK_TYPE_ANDROID,
                           help='indicate to pack android client configure file')
    src_group.add_argument('-i', dest='type', action='store_const', default=_PACK_TYPE_ALL, const=_PACK_TYPE_IOS,
                           help='indicate to pack IOS client configure file')

    src_group = parser.add_mutually_exclusive_group()
    src_group.add_argument('--ALL', dest='upload_type', action='store_const', default=_UPLOAD_TYPE_NONE,
                           const=_UPLOAD_TYPE_ALL, help='commit ios andriod config file')
    src_group.add_argument('-I', dest='upload_type', action='store_const', default=_UPLOAD_TYPE_NONE,
                           const=_UPLOAD_TYPE_IOS, help='commit ios config file')
    src_group.add_argument('-A', dest='upload_type', action='store_const', default=_UPLOAD_TYPE_NONE,
                           const=_UPLOAD_TYPE_ANDROID, help='commit andriod config file')

    #     parser.print_help()

    return parser.parse_args(src_args)


def main(args):
    filter_folders = args.filter_folders
    filter_folders_str = ','.join(filter_folders)
    print('filter_folders files: {}\n'.format(filter_folders_str))

    manager = ConfigBuildManager(args)
    manager.process()


if __name__ == '__main__':
    #     test_args = 'a b -i -u'.split()
    test_args = None
    args = get_args(test_args)
    utility.measure_time(main, args)

