import unittest
import os
import ftp_download
import creditutils.utility_util as util


class Test(unittest.TestCase):


    def setUp(self):
        pass


    def tearDown(self):
        pass


    def testName(self):
        pass

def test_download_apk():
    ftp_config_path = r'D:\auto_build\release_apk\config\sftp_config.xml'
    local_dir_path=r'D:\auto_build\release_apk\apk\txxy\5.1.8'
    ver_name = '5.1.8'
    
    print(f'ftp_config_path: {ftp_config_path}')
    print(f'local_dir_path: {local_dir_path}')
    print(f'ver_name: {ver_name}')

    ftp_download.Manager.download_sftp_file(ftp_config_path, local_dir_path, ver_name)

def test_download_apk_with_other_channel():
    # ftp_config_path = r'D:\auto_build\release_apk\config\sftp_config.xml'
    # local_dir_path=r'D:\auto_build\release_apk\apk\txxy\5.1.8\google'
    ftp_config_path = '/data/android/auto_build/pytxxy/config/base/sftp_config.xml'
    local_dir_path='/data/temp/apk/5.1.8/google'
    ver_name = '5.1.8'
    channel='google'
    
    print(f'ftp_config_path: {ftp_config_path}')
    print(f'local_dir_path: {local_dir_path}')
    print(f'ver_name: {ver_name}')
    print(f'channel: {channel}')

    ftp_download.Manager.download_sftp_file(ftp_config_path, local_dir_path, ver_name, channel=channel, as_file=False, debug=False)

def test_download_apk_with_ver_no():
    # ftp_config_path = r'D:\auto_build\release_apk\config\sftp_config.xml'
    # local_dir_path=r'D:\auto_build\release_apk\apk\xycx\1.1.8'
    ftp_config_path = '/data/android/auto_build/pytxxy/config/base/sftp_config.xml'
    local_dir_path='/data/temp/apk/xycx/1.1.8'
    ver_name = '1.1.8'
    ver_env = 'test'
    ver_no='t_02'
    sftp_root_tag = 'xycx'
    target_file_name='xycx.apk'
    
    print(f'ftp_config_path: {ftp_config_path}')
    print(f'local_dir_path: {local_dir_path}')
    print(f'ver_name: {ver_name}')
    print(f'ver_env: {ver_env}')
    print(f'ver_no: {ver_no}')
    print(f'sftp_root_tag: {sftp_root_tag}')
    print(f'target_file_name: {target_file_name}')

    ftp_download.Manager.download_sftp_file(ftp_config_path, local_dir_path, ver_name, ver_env=ver_env, sftp_root_tag=sftp_root_tag,
                    ver_no=ver_no, target_file_name=target_file_name, force=True, as_file=False, debug=False)

def test_main():
    # test_download_apk()
    # test_download_apk_with_other_channel()
    test_download_apk_with_ver_no()
    

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
#     unittest.main()

    util.measure_time(test_main)