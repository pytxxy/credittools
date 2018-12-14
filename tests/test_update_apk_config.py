'''
Created on 2015年4月16日

@author: caifh
'''
import unittest
from update_apk_config import ApkConfigUpdater
import os
from creditutils import apk_util


class Test(unittest.TestCase):


    def setUp(self):
        pass


    def tearDown(self):
        pass


    def testName(self):
        pass

def test_ApkConfigUpdater():
    apk_path = r'D:\version_build\pytxxy\output\pytxxy-debug-pytxxyV1.2.0.Build150304-20150415.apk'
    apk_items = apk_util.get_apk_info(apk_path)
    
    dst_path = r'D:\version_build\pytxxy\config\template\upgrade.json'
    updater = ApkConfigUpdater(dst_path)
    updater._update_json_file(apk_path, apk_items)

def test_main():
    test_ApkConfigUpdater()


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
#     unittest.main()

    test_main()