import os
import time
import datetime
import argparse
import shutil
import re


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


class ProcessManager:
    def __init__(self, args):
        # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)

        self.src = os.path.abspath(self.src)
        # print(self.src)
        self.dst = os.path.abspath(self.dst)
        # print(self.dst)
        # print(type(self.save_days))

    def process(self):
        # 先进行备份操作
        # 获取当前时间
        curr_time = time.localtime()
        time_str = time.strftime('%Y%m%d_%H%M%S', curr_time)
        target_dir = os.path.join(self.dst, time_str)
        if os.path.isdir(target_dir):
            shutil.rmtree(target_dir)

        shutil.copytree(self.src, target_dir)

        # 删除要求天数以外的备份文件夹
        dir_list = self.get_dir_list(self.dst)
        end_date_str = time_str.split('_')[0]
        for item in dir_list:
            begin_date_str = item.split('_')[0]
            diff_days = self.get_str_datetime_diff_days(begin_date_str, end_date_str)
            if diff_days > self.save_days:
                whole_path = os.path.join(self.dst, item)
                shutil.rmtree(whole_path)

    @staticmethod
    def get_dir_list(dir_):
        date_format = '\d{8}_\d{6}'
        middle = os.listdir(dir_)
        result = list()
        for item in middle:
            whole = os.path.join(dir_, item)
            if os.path.isdir(whole):
                match_obj = re.match(date_format, item)
                if match_obj:
                    result.append(item)

        return result

    @staticmethod
    def str_to_datetime(date_str):
        return datetime.datetime.strptime(date_str, '%Y%m%d')

    def get_str_datetime_diff_days(self, begin_date_str, end_date_str):
        begin_date = self.str_to_datetime(begin_date_str)
        end_date = self.str_to_datetime(end_date_str)
        diff_date = end_date - begin_date
        return diff_date.days


# 对输入参数进行解析，设置相应参数
# 主要参数为源目录、备份目录，保留天数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='pack configure file.')
    parser.add_argument('src', metavar='src', help='the directory to backup from')
    parser.add_argument('dst', metavar='dst', help='the target directory for backup')
    parser.add_argument('-t', metavar='temp_dir', dest='temp_dir', action='store', type=str,
                        help='indicate the temp dir to save compressed file')
    parser.add_argument('-s', metavar='save_days', dest='save_days', action='store', type=int, default=5,
                        help='indicate the data save days')

    #     parser.print_help()

    return parser.parse_args(src_args)


def main(src_args):
    manager = ProcessManager(src_args)
    manager.process()


if __name__ == '__main__':
    test_args = None
    args = get_args(test_args)
    measure_time(main, args)
