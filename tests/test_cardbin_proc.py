'''
Created on 2017年9月16日

@author: caifh
'''
import unittest
import cardbin_proc as proc
import os

class Test(unittest.TestCase):


    def setUp(self):
        self.dir = os.path.dirname(__file__)


    def tearDown(self):
        pass


#     def testDataProcess_process(self):
#         filename = 'cardbin_20170912.xlsx'
#         file_path = os.path.join(self.dir, filename)
#         process = proc.DataProcess(file_path)
#         data = process.process()
#         self.data = data
#         self.error_data = process.get_error_data()
#         
#         expected = '004055'
#         actual = data[0][proc.Label.cardbin]
#         msg = 'expecting {}, but got {}!'.format(expected, actual)
#         self.assertEqual(expected, actual, msg)

    def testLuaProcess_process(self):
        filename = 'cardbin_20170912.xlsx'
        file_path = os.path.join(self.dir, filename)
        process = proc.DataProcess(file_path)
        data = process.process()
        self.data = data
        self.error_data = process.get_error_data()
        
        expected = '004055'
        actual = data[0][proc.Label.cardbin]
        msg = 'expecting {}, but got {}!'.format(expected, actual)
        self.assertEqual(expected, actual, msg)
        
        filename = 'luhmBank.lua'
        dst_file = 'luhmBank_1.lua'
        file_path = os.path.join(self.dir, filename)
        dst_path = os.path.join(self.dir, dst_file)
        process = proc.LuaProcess(file_path, dst_path)
        rtn = process.process(self.data, self.error_data)
        
        expected = True
        actual = rtn
        msg = 'expecting {}, but got {}!'.format(expected, actual)
        self.assertEqual(expected, actual, msg)

def test_all():
    pass

def test_main():
    test_all()

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
#     test_main()