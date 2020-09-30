import unittest
import os
import tempfile
import shutil
import creditutils.img_util as img_util
import creditutils.file_util as file_util
import ftp_upload


class Test(unittest.TestCase):


    def setUp(self):
        pass


    def tearDown(self):
        pass


    def testName(self):
        pass

def test_upload_apk():
    ftp_config_path = r'D:\auto_build\pytxxy'
    ver_name_info = '5.1.5beta_t_01'
    channel = '' # 调用的接口内部实现默认是空串
    target_name = '5.1.5beta_t_01-702-20200930.apk'
    source_name = '5.1.5beta_t_01-702-20200930.apk'
    ver_env = 'test'
    prj_code_ver = '319e2dd5f6a7043fde8770a08079fe26f0d65d92'
    app_code = 'txxy'

    to_upload_path = r'D:\auto_build\pytxxy\output\test\20200930_111054'
    mobile_os = 'Android'

    desc_data = {'info': 'just for test'}
    
    print(f'ftp_config_path: {ftp_config_path}')
    print(f'ver_name_info: {ver_name_info}')
    print(f'target_name: {target_name}')
    print(f'source_name: {source_name}')
    print(f'channel: {channel}')

    ftp_upload.upload_to_sftp(ftp_config_path, ver_name_info, ver_env, prj_code_ver, app_code,
                                to_upload_path, mobile_os=mobile_os, channel=channel, target_file_name=target_name,
                                source_file_name=source_name, desc_data=desc_data)

def test_upload_apk_with_protected():
    ftp_config_path = r'D:\auto_build\pytxxy'
    ver_name_info = '5.1.5beta_t_01'
    channel = 'oppo' # 调用的接口内部实现默认是空串
    target_name = '5.1.5beta_t_01-702-20200930.apk'
    source_name = '5.1.5beta_t_01-702-20200930_sec.apk'
    ver_env = 'test'
    prj_code_ver = '319e2dd5f6a7043fde8770a08079fe26f0d65d92'
    app_code = 'txxy'

    to_upload_path = r'D:\auto_build\pytxxy\output\test\20200930_142454'
    mobile_os = 'Android'

    desc_data = {'info': 'just for test'}
    
    print(f'ftp_config_path: {ftp_config_path}')
    print(f'ver_name_info: {ver_name_info}')
    print(f'target_name: {target_name}')
    print(f'source_name: {source_name}')
    print(f'channel: {channel}')

    ftp_upload.upload_to_sftp(ftp_config_path, ver_name_info, ver_env, prj_code_ver, app_code,
                                to_upload_path, mobile_os=mobile_os, channel=channel, target_file_name=target_name,
                                source_file_name=source_name, desc_data=desc_data)

def test_main():
    # test_upload_apk()
    test_upload_apk_with_protected()
    

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
#     unittest.main()

    test_main()