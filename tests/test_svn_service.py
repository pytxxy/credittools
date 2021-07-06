import unittest
import os
import time
import tempfile
import shutil
import svn_service
from svn_service import SvnService
import creditutils.file_util as file_util

class Test(unittest.TestCase):


    def setUp(self):
        self.temp_dir = tempfile.gettempdir()
        self.svn_name = 'txxy'
        self.svn_dir =  os.path.join(self.temp_dir, self.svn_name)
        hooks_dir = 'hooks'
        self.dir_path = os.path.join(self.svn_dir, hooks_dir)
        
        self.normal = 'pre-commit_normal.cmd'
        self.refuse = 'pre-commit_refuse.cmd'
        self.target = 'pre-commit.cmd'

        if not os.path.isdir(self.dir_path):
            os.makedirs(self.dir_path)

        self.normal_str = 'a'
        self.refuse_str = 'b'
        self.normal_path = os.path.join(self.dir_path, self.normal)
        self.refuse_path = os.path.join(self.dir_path, self.refuse)
        self.target_path = os.path.join(self.dir_path, self.target)

        file_util.write_to_file(self.normal_path, self.normal_str, encoding='utf-8')
        file_util.write_to_file(self.refuse_path, self.refuse_str, encoding='utf-8')

    def tearDown(self):
        if os.path.isdir(self.svn_dir):
            shutil.rmtree(self.svn_dir)

    def testSwitch_commit_with_file(self):
        service = SvnService(self.temp_dir, normal=self.normal, refuse=self.refuse, target=self.target)
        target_path = self.target_path
        normal_str = self.normal_str
        refuse_str = self.refuse_str
        svn_name = self.svn_name

        # 验证原本可正常提交情况，当前要切换为可提交情况
        file_util.write_to_file(target_path, normal_str, encoding='utf-8')
        time.sleep(1)
        target_m_time = os.path.getmtime(target_path)
        service.switch_commit_with_file(svn_name, True)
        new_target_m_time = os.path.getmtime(target_path)
        content = file_util.read_file_content(target_path, encoding_='utf-8')
        self.assertEqual(target_m_time, new_target_m_time, f'target_c_time: {target_m_time}, new_target_c_time: {new_target_m_time}')
        self.assertEqual(content, normal_str, f'content: {content}, normal_str: {normal_str}')

        # 验证原本非正常提交情况，当前要切换为可提交情况
        file_util.write_to_file(target_path, refuse_str, encoding='utf-8')
        time.sleep(1)
        target_m_time = os.path.getmtime(target_path)
        service.switch_commit_with_file(svn_name, True)
        new_target_m_time = os.path.getmtime(target_path)
        content = file_util.read_file_content(target_path, encoding_='utf-8')
        self.assertNotEqual(target_m_time, new_target_m_time, f'target_c_time: {target_m_time}, new_target_c_time: {new_target_m_time}')
        self.assertEqual(content, normal_str, f'content: {content}, normal_str: {normal_str}')

        # 验证原本可正常提交情况，当前要切换为不可提交情况
        file_util.write_to_file(target_path, normal_str, encoding='utf-8')
        time.sleep(1)
        target_m_time = os.path.getmtime(target_path)
        service.switch_commit_with_file(svn_name, False)
        new_target_m_time = os.path.getmtime(target_path)
        content = file_util.read_file_content(target_path, encoding_='utf-8')
        self.assertNotEqual(target_m_time, new_target_m_time, f'target_c_time: {target_m_time}, new_target_c_time: {new_target_m_time}')
        self.assertEqual(content, refuse_str, f'content: {content}, refuse_str: {refuse_str}')

        # 验证原本非正常提交情况，当前要切换为不可提交情况
        file_util.write_to_file(target_path, refuse_str, encoding='utf-8')
        time.sleep(1)
        target_m_time = os.path.getmtime(target_path)
        service.switch_commit_with_file(svn_name, False)
        new_target_m_time = os.path.getmtime(target_path)
        content = file_util.read_file_content(target_path, encoding_='utf-8')
        self.assertEqual(target_m_time, new_target_m_time, f'target_c_time: {target_m_time}, new_target_c_time: {new_target_m_time}')
        self.assertEqual(content, refuse_str, f'content: {content}, refuse_str: {refuse_str}')

    def testExposed_switch_commit(self):
        token='abc'
        file_util.write_to_file(self.target_path, self.normal_str, encoding='utf-8')
        service = SvnService(self.temp_dir, token=token, normal=self.normal, refuse=self.refuse, target=self.target)
        code, _ = service.exposed_switch_commit(self.svn_name, True, token=token)
        self.assertEqual(code, svn_service.CODE_SUCCESS, f'code: {code}, expect: {svn_service.CODE_SUCCESS}')

        code, _ = service.exposed_switch_commit(self.svn_name, True)
        self.assertEqual(code, svn_service.CODE_INVALID_TOKEN, f'code: {code}, expect: {svn_service.CODE_INVALID_TOKEN}')

        os.remove(self.target_path)
        code, _ = service.exposed_switch_commit(self.svn_name, True, token=token)
        self.assertEqual(code, svn_service.CODE_FAILED, f'code: {code}, expect: {svn_service.CODE_FAILED}')

if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()