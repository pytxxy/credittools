# -*- coding:UTF-8 -*- # 标识为


import creditutils.exec_cmd as exec_cmd
import sys, re
import os
import subprocess
import shlex


class FilePulling:
    _INVALID_FILE_RE_OBJ = re.compile('^\s*$')
    _INSTALLED_RE_OBJ = re.compile(u'Success')
    _UNINSTALLED_RE_OBJ = re.compile(u'Success')
    _INSTALL_FAILED_ALREADY_EXISTS_RE = re.compile(u'INSTALL_FAILED_ALREADY_EXISTS')

    _RUN_ADB_FAILED_RE_OBJ = re.compile('^adb server is out of date')
    _VALID_DEVICE_LINE = re.compile('^\s*([^\s]+)\s+device')
    _ABNORMAL_DEVICE_LINE = re.compile('^\s*([^\s]+)\s+offline')

    def __init__(self, src_dir, dst_dir):
        self.src_dir = src_dir
        self.dst_dir = dst_dir
        self.dev_name_list = []
        self.is_empty = True

    def get_device_info(self):
        cmd_str = 'adb devices'
        result = exec_cmd.run_cmd_for_output_in_specified_dir(sys.path[0], cmd_str)
        lines = result.split('\r\n')[1:]

        # 如果出现异常的设备信息，则先处理然后再运行
        isAbnormal = self._check_device_lines_abnormality(lines)
        if isAbnormal:
            self._run_adb_kill_server_cmd()
            result = self._run_check_environment_cmd_for_result()
            lines = result.split('\r\n')[1:]

        self.dev_name_list = []
        for line in lines:
            isValid, dev_name = self._check_device_line_vality(line)
            if isValid:
                if dev_name in self.dev_name_list:
                    msg_info = u'设备存在重复的序列号'
                    raise ValueError(msg_info)
                else:
                    self.dev_name_list.append(dev_name)

        if self.dev_name_list:
            return True
        else:
            msg_info = u'没有可连接的手机设备'
            raise ValueError(msg_info)

    def check_environment(self):
        isReady = False

        try:
            self.get_device_info()
            if len(self.dev_name_list) == 1:
                isReady = True
        except Exception as e:
            isReady = False
            print(str(e))

        if not isReady:
            print('has no device or more than one device')

        return isReady

    def _check_device_line_abnormality(self, line):
        obj_ = FilePulling._ABNORMAL_DEVICE_LINE.match(line)
        if obj_:
            return True
        else:
            return False

    def _check_device_lines_abnormality(self, lines):
        is_abnormal = False
        for line in lines:
            result = self._check_device_line_abnormality(line)
            if result:
                is_abnormal = True
                break

        return is_abnormal

    def _check_device_line_vality(self, line):
        obj_ = FilePulling._VALID_DEVICE_LINE.match(line)
        if obj_:
            return True, obj_.group(1)
        else:
            return False, None

    def _check_file_vality(self, src_file):
        match_obj = FilePulling._INVALID_FILE_RE_OBJ.match(src_file)
        if not match_obj:
            return True
        else:
            return False

    def _run_adb_kill_server_cmd(self):
        try:
            cmd_str = 'adb kill-server'
            result = exec_cmd.run_cmd_for_stdout_ignores_exit_code(cmd_str)
            info_format = 'run {0}, result: {1}'
            info = info_format.format(cmd_str, result)
            print(info)

        except Exception as e:  # 其它可能的出错情况，当前暂不清楚会在什么条件下出现
            print(str(e))

    def __call__(self, src_file, print_flag=True):
        if not self._check_file_vality(src_file):
            raise Exception('file name "' + src_file + '" is invalid')

        if self.check_environment():
            cmd_info = 'adb pull {0}/{1} {2}'.format(self.src_dir, src_file, self.dst_dir)
            if print_flag:
                print(cmd_info)
            try:
                result = subprocess.check_output(cmd_info, shell=True, universal_newlines=True)
                if print_flag:
                    print(result)
            except subprocess.CalledProcessError as e:
                print((str(e)))
                return False

            return True
        else:
            return False

    def get_all_src_files(self):
        args = list()
        args.append('adb')
        args.append('shell')
        ls_cmd_str = 'cd {0} && ls'.format(self.src_dir)
        args.append(ls_cmd_str)

        try:
            result = subprocess.check_output(args, shell=True, universal_newlines=True)
        except subprocess.CalledProcessError as e:
            print((str(e)))
            return []

        return re.split('[\r\n]+', result)

    def pull_all_files(self, print_flag=True):
        self.is_empty = True
        content = self.get_all_src_files()
        #         print(content)
        for line in content:
            src_file = line.strip()
            if len(src_file) == 0:
                break

            self.is_empty = False
            self.__call__(src_file, print_flag)

        if self.is_empty:
            print('no file to pull')

    def remove_src_file(self, src_file, print_flag=True):
        if not self._check_file_vality(src_file):
            raise Exception('file name "' + src_file + '" is invalid')

        #         cmd_info = 'adb shell "cd {0} && rm {1}"'.format(self.src_dir, src_file)

        args = []
        args.append('adb')
        args.append('shell')
        rm_cmd_str = 'cd {0} && rm {1}'.format(self.src_dir, src_file)
        args.append(rm_cmd_str)
        if print_flag:
            print(args)

        try:
            result = subprocess.check_output(args, shell=True, universal_newlines=True)
            if print_flag:
                print(result)
        except subprocess.CalledProcessError as e:
            print((str(e)))

    def remove_all_src_files(self, print_flag=True):
        #         cmd_info = 'adb shell "cd {0} && rm *"'.format(src_dir)

        if self.is_empty:
            return

        args = []
        args.append('adb')
        args.append('shell')
        ls_cmd_str = 'cd {0} && rm *'.format(self.src_dir)
        args.append(ls_cmd_str)

        if print_flag:
            print(args)

        try:
            result = subprocess.check_output(args, shell=True, universal_newlines=True)
            if print_flag:
                print(result)
        except subprocess.CalledProcessError as e:
            print((str(e)))


def cmd_exec_test():
    args = []
    args.append('adb')
    args.append('shell')
    #     src_dir = '/sdcard/tiny/crash'
    src_dir = '/sdcard/crash'
    ls_cmd_str = 'cd {0} && ls'.format(src_dir)
    args.append(ls_cmd_str)

    try:
        result = subprocess.check_output(args, shell=True, universal_newlines=True)
        #         print(args)
        print(result)
    except subprocess.CalledProcessError as e:
        print((str(e)))
        return []

    return result.split('\n')


if __name__ == '__main__':
    req_cnt_1 = 3
    req_cnt_2 = 4
    del_flag = 1

    cnt = len(sys.argv)
    if cnt != req_cnt_1 and cnt != req_cnt_2:
        str_format = 'argument count should be {} or {}, but current count is {}'
        print(str_format.format(req_cnt_1, req_cnt_2, cnt))
        exit(1)
    #     else:
    #         print(sys.argv)

    src_path = sys.argv[1]
    dst_dir = os.path.abspath(sys.argv[2])
    to_del = False
    if cnt == req_cnt_2:
        del_para = int(sys.argv[3])
        if del_para == del_flag:
            to_del = True
        else:
            to_del = False

    file_flag = False
    if src_path[-1] == '*':
        file_flag = False
        src_dir = os.path.dirname(src_path)
    else:
        file_flag = True
        src_dir = os.path.dirname(src_path)
        to_pull = os.path.basename(src_path)

    file_pulling = FilePulling(src_dir, dst_dir)
    if not file_pulling.check_environment():
        exit(1)

    if file_flag:
        # 该部分代码用于从文件中读取文件列表
        # content = myfile.read_file_lines(to_pull)
        # for line in content:
        #    src_file = line.strip()
        #    if len(src_file) == 0:
        #        continue
        #    file_pulling(src_file)
        #    file_pulling.remove_src_file(src_file)

        # 直接拉取单个文件
        file_pulling(to_pull)
        if to_del:
            file_pulling.remove_src_file(to_pull)
    else:
        file_pulling.pull_all_files()
        if to_del:
            file_pulling.remove_all_src_files()

    #     cmd_exec_test()

    exit(0)
