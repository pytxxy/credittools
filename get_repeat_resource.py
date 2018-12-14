'''
Created on 2017年9月11日

@author: wangmeng

Android重复文件资源收集，目前只针对drawable目录和string文案字符串重复的收集统计
入参：应用工程的资源文件所在的根目录路径，如"Txxy-Android\pytxxy\res"
输出：在res目录会输出重复的drawable和string资源并分别存储到文件

'''
import os
import creditutils.file_util as myfile
import creditutils.hash_util as myhash
import argparse

class ResourceFilter:
    def __init__(self, args):
        if args is not None:
            for name, value in vars(args).items():
                setattr(self, name, value)

    # 过滤重复的资源值
    def filter_duplicated_values(self, root_dir_path, dupicated_result, is_drawable_or_string):
        # 遍历所记录的重复字符串，若存在逗号拼接的，说明有重复的串，这时需要拼接并存到文件
        dupicated_content = []
        for result_key in dupicated_result.keys():
            result_value = dupicated_result[result_key]
            value_list = result_value.split(',')
            if len(value_list) > 1:
                if is_drawable_or_string:
                    dupicated_content.append('{}\n\n'.format(result_value))
                else:
                    dupicated_content.append('{}: {}\n\n'.format(result_key, result_value))
                
        if len(dupicated_content) == 0:
            if is_drawable_or_string:
                print('没有找到重复的drawable资源.')
            else:
                print('没有找到重复的string资源.')
        else:
            file_name = '重复的字符串资源.txt';
            success_tip = '已将重复的字符串资源记录到文件，可在{}目录中查看.';
            if is_drawable_or_string:
                file_name = '重复的drawable资源.txt'
                success_tip = '已将重复的drawable资源记录到文件，可在{}目录中查看.'
              
            # 记录数据到本地文件
            root_parent_dir = os.path.join(os.path.dirname(root_dir_path))
            file_path = '{}\\{}'.format(root_parent_dir, file_name);
            myfile.write_to_file(file_path, ''.join(dupicated_content), encoding='utf-8')
    
            print(success_tip.format(root_parent_dir)) 
    

    # 过滤重复的drawable文件    
    def filter_drawable_files(self, drawable_dirs):
        dict_result = {}
        root_dir_path = ''
        for drawable_dir in drawable_dirs:
            if len(root_dir_path) == 0:
                root_dir_path = drawable_dir
                
            # 遍历一级目录及目录下面所有文件，将文件名和md5作为映射存到字典中
            list_files = myfile.get_file_list(drawable_dir)
            for fpath in list_files:
                file_absolute_path = drawable_dir + '\\' + fpath;
                # 用md5区分文件是否一致
                md5_str = myhash.get_file_md5(file_absolute_path)
                with_dir_name_path = drawable_dir[drawable_dir.rindex('\\') + 1 : len(drawable_dir)] + '\\' + fpath
                if md5_str in dict_result.keys():
                    # 若存在则将值用逗号拼接在一起
                    dict_result[md5_str] = '{}, {}'.format(dict_result[md5_str], with_dir_name_path)
                else:
                    dict_result[md5_str] = with_dir_name_path
                
        
        # 遍历映射字典，检测是否有重复的sha1，有则说明有相同的图标文件，并将相同的文件打印出来(暂时不做删除)
        self.filter_duplicated_values(root_dir_path, dict_result, True)
    

    # 通过xml解析来过滤value资源文件中重复的字符串                
    def filter_string_values(self, root_dir_path):
        try:
            import xml.etree.cElementTree as ET
        except ImportError:
            import xml.etree.ElementTree as ET
    
        ele_dupicated_result = {}
        list_files = myfile.get_file_list(root_dir_path)
        for fpath in list_files:
            file_absolute_path = root_dir_path + '\\' + fpath;
            tree = ET.ElementTree(file=file_absolute_path)
            # 解析每个文件中<string "name">xxxx</string>标签中内容，并以字典方式存储记录下来
            for elem in tree.iter(tag='string'):
                child_text = elem.text
                child_attrib = elem.attrib
                attrib_name = child_attrib['name']
                if child_text in ele_dupicated_result.keys():
                    # 若存在则将值用逗号拼接在一起
                    ele_dupicated_result[child_text] = '{}, {}'.format(ele_dupicated_result[child_text], attrib_name + '(' + fpath + ')')
                else:
                    ele_dupicated_result[child_text] = attrib_name + '(' + fpath + ')'
                continue;
        
        # 遍历所记录的重复字符串，若存在逗号拼接的，说明有重复的串，这时需要拼接并存到文件
        self.filter_duplicated_values(root_dir_path, ele_dupicated_result, False)

    # 执行资源过滤    
    def do_filter(self):
        drawable_dirs = []
        child_dirs = myfile.get_child_dirs(self.res)
        for child_dir in child_dirs:
            dir_name = child_dir[child_dir.rindex('\\') + 1 : len(child_dir)]
            if dir_name == 'values':
                self.filter_string_values(child_dir)
            elif dir_name.find('drawable') == 0:
                drawable_dirs.append(child_dir)
         
        self.filter_drawable_files(drawable_dirs)

        
# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='smart compress image(PNG or JPEG).')
    parser.add_argument('res', metavar='res', help='source file or directory')
    return parser.parse_args(src_args)

# 程序入口
def main():
    test_args = ''.split()  # @UnusedVariable
    test_args = None
    args = get_args(test_args)
    res_filter = ResourceFilter(args)
    res_filter.do_filter()

# 测试入口
def test_main():
    res_filter = ResourceFilter(None)
    res_filter.res = 'E:\\develop\\workshare\\Txxy-Android\\pytxxy\\res'
    res_filter.do_filter()
        
if __name__ == '__main__':
#     test_main()
    main()

