import unittest
import os
import release_apk
import creditutils.trivial_util as util


class Test(unittest.TestCase):


    def setUp(self):
        pass


    def tearDown(self):
        pass


    def testName(self):
        pass

def test_generator_run():
    work_path = r'D:\auto_build\release_apk'
    app_code = 'txxy'
    ver_name = '5.1.8'
    
    print(f'work_path: {work_path}')
    print(f'app_code: {app_code}')
    print(f'ver_name: {ver_name}')
    generator = release_apk.Generator(work_path, app_code, ver_name)
    generator.process()


def test_uploader_run():
    work_path = r'D:\auto_build\release_apk'
    app_code = 'txxy'
    ver_name = '5.1.8'
    
    print(f'work_path: {work_path}')
    print(f'app_code: {app_code}')
    print(f'ver_name: {ver_name}')
    uploader = release_apk.Uploader(work_path, app_code, ver_name)
    uploader.process()
    print(uploader.get_zip_uploaded_list())
    print(uploader.get_official_addr())


def test_notifier_run():
    work_path = r'D:\auto_build\release_apk'
    app_code = 'txxy'
    ver_name = '5.1.8'
    
    print(f'work_path: {work_path}')
    print(f'app_code: {app_code}')
    print(f'ver_name: {ver_name}')
    uploader = release_apk.Uploader(work_path, app_code, ver_name)

    notifier = release_apk.Notifier(work_path, app_code, ver_name)
    addr = uploader.get_official_addr()
    addr_list = uploader.get_zip_uploaded_list()
    notifier.notify_to_upgrade(addr)
    notifier.notify_to_publish(addr_list)


def test_main():
    # test_generator_run()
    # test_uploader_run()
    test_notifier_run()
    

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
#     unittest.main()

    util.measure_time(test_main)