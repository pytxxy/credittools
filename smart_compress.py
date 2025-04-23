'''
Created on 2016年10月21日

@author: caifh

使用"https://tinypng.com/"网站提供的 smart compression 技术对指定文件后缀名的PNG及JPG文件进行压缩；
支持文件夹指压缩和单文件压缩;
因为每一个key有压缩数据限制(免费版key支持500个)，所以如果要大批量进行图片压缩，需要自己先搞定key的问题；

功能验证列表：
1.先验证整体拷贝和非整体拷贝功能是否正常；(E:\temp\cloud_res\mini_src_01)
2.验证网上压缩功能是否正常；(E:\temp\cloud_res\mini_src_01)
3.验证拷贝只打标签功能是否正常；(E:\temp\cloud_res\mini_src_02)
4.验证本地更新功能是否正常；(E:\temp\cloud_res\mini_src_03)
5.验证本地只打标签功能是否正常；(E:\temp\cloud_res\mini_src_04)

'''

import tinify
import argparse
import os
import creditutils.file_util as myfile
import creditutils.trivial_util as utility
import shutil
import piexif
import traceback
import sys
import tempfile
import creditutils.png_util as png_util
from creditutils.img_util import detect_image_type, ImageType


class Compression:

    def __init__(self, cer_key):
        tinify.key = cer_key

    # 必须保证是成员方法，保证tinify.key 可被正常初始化
    @staticmethod
    def compress_file(src, dst):
        if not os.path.exists(src):
            raise Exception('{} not exists'.format(src))

        try:
            source = tinify.from_file(src)
            dir_name = os.path.dirname(dst)
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
            source.to_file(dst)
        except Exception:
            print('error.message: ', traceback.format_exc())
            sys.exit(1)


class ProcessManager:
    COMPRESSED_FLAG_CHUNK_INDEX = 1
    SUPPORT_IMAGE_SUFFIX = ['.png', '.jpg', '.jpeg']
    COMPRESSED_KEY = 'UserComment'

    def __init__(self, args):
        # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)

        self.src = os.path.abspath(self.src)
        self.comp = Compression(self.cer_key)
        self.temp_dir = None

    def process(self):
        try:
            if not self.dst:
                self.temp_dir = tempfile.mkdtemp()

            if os.path.isfile(self.src):
                if self.dst:
                    ori_dst = os.path.abspath(myfile.normalpath(self.dst))
                    if ori_dst.endswith(os.path.sep):
                        target_path = os.path.join(ori_dst, os.path.basename(self.src))
                    else:
                        target_path = ori_dst
                    self.process_common_func(self.src, target_path, self.identification, self.old_key, self.to_copy, self.tag_only)
                else:
                    self.process_modify_func(self.src, self.identification, self.old_key, self.tag_only)
            elif os.path.isdir(self.src):
                if self.dst:
                    myfile.process_dir_src_to_dst(self.src, self.dst, self.process_common_func, self.identification, self.old_key, self.to_copy, self.tag_only)
                else:
                    myfile.process_dir(self.src, self.process_modify_func, self.identification, self.old_key, self.tag_only)
            else:
                raise Exception('{} not exists'.format(self.src))
        finally:
            if not self.dst:
                if os.path.isdir(self.temp_dir):
                    shutil.rmtree(self.temp_dir)

    # to_copy 标识是否直接拷贝不相干或者已经压缩过文件, tag_only 标识是否只是纯粹加压缩标签
    def process_common_func(self, src_file, dst_file, compressed_identify, old_compressed_identify,
                            to_copy=False, tag_only=False):
        ext_name = os.path.splitext(src_file.lower())[1]
        filename = os.path.split(src_file)[1]
        # 非指定后缀名文件无须处理
        if ext_name not in ProcessManager.SUPPORT_IMAGE_SUFFIX:
            if to_copy:
                # 直接复制到目标文件夹
                shutil.copyfile(src_file, dst_file)
                print("copy {} to {} success".format(src_file, dst_file))

            return

        if filename.lower().endswith('.9.png'):
            if to_copy:
                # 如果是.9图则直接复制到目标文件夹
                shutil.copyfile(src_file, dst_file)
                print("copy {} to {} success".format(src_file, dst_file))

            return

        # 判断是否已经压缩过
        is_compressed = ProcessManager.check_if_compressed(src_file, compressed_identify, old_compressed_identify)
        if is_compressed:
            if to_copy:
                # 已经压缩过则复制到目标文件夹
                shutil.copyfile(src_file, dst_file)
                print("copy {} to {} success".format(src_file, dst_file))

            return
        else:
            # 如果只是标记是否压缩，则无须上传网络压缩(用于标记已经压缩但是没有打标记的文件)
            if not tag_only:
                print(src_file, dst_file)
                self.comp.compress_file(src_file, dst_file)
                print('smart compress "{}" to "{}" success.'.format(src_file, dst_file))
            else:
                shutil.copyfile(src_file, dst_file)

            if os.path.isfile(dst_file):
                # 为目标文件增加压缩标识
                ProcessManager.add_compressed_flag(dst_file, compressed_identify)
                print('add compressed flag to "{}" success.'.format(dst_file))
            else:
                print('process "{}" to "{}" failed!'.format(src_file, dst_file))

    # tag_only 标识是否只是纯粹加压缩标签
    def process_modify_func(self, src_file, compressed_identify, old_compressed_identify, tag_only=False):
        ext_name = os.path.splitext(src_file.lower())[1]
        filename = os.path.split(src_file)[1]
        # 非指定后缀名的文件无须处理
        if ext_name not in ProcessManager.SUPPORT_IMAGE_SUFFIX:
            return

        # android 使用的是.9图片无须处理
        if filename.lower().endswith('.9.png'):
            return

        # 已经压缩过的无须处理
        is_compressed = ProcessManager.check_if_compressed(src_file, compressed_identify, old_compressed_identify)
        if is_compressed:
            return
        else:
            temp_name = os.path.basename(tempfile.mktemp()) + os.path.basename(src_file)
            temp_file = os.path.join(self.temp_dir, temp_name)
            shutil.copyfile(src_file, temp_file)

            # 如果只是标记是否压缩，则无须上传网络压缩(用于标记已经压缩但是没有打标记的文件)
            if not tag_only:
                self.comp.compress_file(temp_file, src_file)
                print('smart compress "{}" success.'.format(src_file))

            # 为目标文件增加压缩标识
            ProcessManager.add_compressed_flag(src_file, compressed_identify)
            print('add compressed flag to "{}" success.'.format(src_file))

    # 给png 图片文件增加压缩标识
    @staticmethod
    def add_compressed_flag_to_png_file(file_path, compressed_identify):
        png_util.insert_text_chunk(file_path, compressed_identify,
                                   ProcessManager.COMPRESSED_FLAG_CHUNK_INDEX)

    # 给jpeg 图片文件增加压缩标识
    @staticmethod
    def add_compressed_flag_to_jpeg_file(file_path, compressed_identify):
        exif_dict = piexif.load(file_path)
        comment_tag = piexif.ExifIFD.UserComment
        exif_info = exif_dict['Exif']
        exif_info[comment_tag] = compressed_identify.encode()
        piexif.insert(piexif.dump(exif_dict), file_path)

    # 给图片文件增加压缩标识
    @staticmethod
    def add_compressed_flag(src_path, compressed_identify):
        img_type = detect_image_type(src_path)
        if ImageType.JPEG == img_type:
            ProcessManager.add_compressed_flag_to_jpeg_file(src_path, compressed_identify)
        elif ImageType.PNG == img_type:
            ProcessManager.add_compressed_flag_to_png_file(src_path, compressed_identify)

    # 检测png 文件是否包含压缩标识
    @staticmethod
    def check_if_png_compressed(file_path, compressed_identify, old_compressed_identify):
        # print(f'file_path: {file_path}.')
        data = png_util.get_text_chunk_data(file_path, 1)
        if data:
            if data == compressed_identify:
                return True

            # 检查是否有旧的标识，替换成新的标识
            if data == old_compressed_identify:
                ProcessManager.add_compressed_flag(file_path, compressed_identify)
                return True
        else:
            return False

    # 检测jpeg 文件是否包含压缩标识
    @staticmethod
    def check_if_jpeg_compressed(file_path, compressed_identify, old_compressed_identify):
        exif_dict = piexif.load(file_path)
        comment_tag = piexif.ExifIFD.UserComment
        exif_info = exif_dict['Exif']
        if exif_info:
            if comment_tag in exif_info:
                if exif_info[comment_tag] == compressed_identify.encode():
                    return True

                # 检查是否有旧的标识，替换成新的标识
                if exif_info[comment_tag] == old_compressed_identify:
                    ProcessManager.add_compressed_flag(file_path, compressed_identify)
                    return True

        return False

    # 检查文件是否含有压缩标识
    @staticmethod
    def check_if_compressed(file_path, compressed_identify, old_compressed_identify):
        img_type = detect_image_type(file_path)
        if ImageType.PNG == img_type:
            return ProcessManager.check_if_png_compressed(file_path, compressed_identify, old_compressed_identify)
        elif ImageType.JPEG == img_type:
            return ProcessManager.check_if_jpeg_compressed(file_path, compressed_identify, old_compressed_identify)

        return False

def main(args):
    manager = ProcessManager(args)
    manager.process()


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='smart compress image(PNG or JPEG).')
    parser.add_argument('src', metavar='src',
                        help='source file or directory')

    parser.add_argument('-k', dest='cer_key', default=None,  required=True,
                        help='indicate the certificate key.')

    parser.add_argument('-o', dest='dst', metavar='dst', default=None,
                        help='target file or directory')

    parser.add_argument('-a', dest='to_copy', action='store_true', default=False,
                        help='specify if to copy all files!')

    parser.add_argument('-t', dest='tag_only', action='store_true', default=False,
                        help='specify only to tag compressed!')

    parser.add_argument('-i', dest='identification', default='ImageCompressed',
                        help='the label of the compressed picture')

    parser.add_argument('--old', dest='old_key', default=None,
                        help='the old label, and will be replaced with new default label.')

    return parser.parse_args(src_args)


if __name__ == '__main__':
    test_args = ''.split()
    test_args = None
    input_args = get_args(test_args)
    utility.measure_time(main, input_args)

