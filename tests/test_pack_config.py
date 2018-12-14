'''
Created on 2015年7月9日

@author: caifh
'''
import unittest
import pack_config

class Test(unittest.TestCase):


    def setUp(self):
        pass


    def tearDown(self):
        pass


    def testName(self):
        pass

def test_FileMap():
    flag = 'android'
#     flag = 'ios'
#     flag = ''
    src_root = r'D:\repository\信用天下APP项目\17 配置管理\config_file'
    dst_root = r'D:\temp\config'
    process = pack_config.FileMap(flag, src_root, dst_root)
    
    src_path = r'D:\repository\信用天下APP项目\17 配置管理\config_file\common\input_verify\lua\pay_pwd.lua'
    print(process(src_path))
    
    src_path = r'common\input_verify@android\lua\pay_pwd.lua'
    print(process(src_path))
    
    src_path = r'common\input_verify@ios\lua\pay_pwd.lua'
    print(process(src_path))
    
    src_path = r'image@android\bank_icon\spdb.png'
    print(process(src_path))
    
    src_path = r'image@ios\bank_icon\spdb.png'
    print(process(src_path))

def test_main():
    test_FileMap()

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
#     unittest.main()

    test_main()
    
    print('to the end')