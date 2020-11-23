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

def test_main():
    test_generator_run()
    

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
#     unittest.main()

    util.measure_time(test_main)