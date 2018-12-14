'''
Created on 2017年5月10日

@author: caifh
'''
import unittest
import protect_android_app as proc

class Test(unittest.TestCase):


    def setUp(self):
        pass


    def tearDown(self):
        pass


    def testName(self):
        pass

def test_protect_with_dst_path():
    ip = '10.192.76.12'
    user_name = 'pyzx'
    password = 'pyzx12#$'
    file_path = r'D:\programs\shieldpy_v4\upload'
    dst_path = r'D:\programs\shieldpy_v4\download'
    result = proc.protect(ip, user_name, password, file_path, dst_path)
    print(result)
    
def test_protect_without_dst_path():
    ip = '10.192.76.12'
    user_name = 'pyzx'
    password = 'pyzx12#$'
    file_path = r'D:\programs\shieldpy_v4\upload'
    result = proc.protect(ip, user_name, password, file_path)
    print(result)
    
def test_protect_with_file():
    ip = '10.192.76.12'
    user_name = 'pyzx'
    password = 'pyzx12#$'
    file_path = r'D:\programs\shieldpy_v4\upload\3.0.0beta_p_12-294-20170401.apk'
    result = proc.protect(ip, user_name, password, file_path)
    print(result)

def test_main():
#     test_protect_with_dst_path()
#     test_protect_without_dst_path()
    test_protect_with_file()

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
#     unittest.main()
    
    test_main()

    print('to the end')