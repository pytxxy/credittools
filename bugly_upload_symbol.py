import os
import subprocess
import xmltodict
import creditutils.file_util as file_util


class BuilderLabel:
    CONFIG = 'config'
    PATH = 'path'
    LIB = 'lib'
    JDK = 'jdk'
    DEV = 'dev'
    PRO = 'pro'
    NAME = 'name'
    APP_ID = 'appId'
    APP_KEY = 'appKey'
    BUNDLE_ID = 'bundleId'


class BuildConfigParser:
    def __init__(self, config_path):
        self.config_path = config_path

    def parse(self):
        doc = xmltodict.parse(file_util.read_file_content(self.config_path))
        self.data = doc[BuilderLabel.CONFIG]

    def get_config(self):
        return self.data


class BuglyManager:
    def __init__(self, work_path) -> None:
        self.work_path = os.path.abspath(work_path)

        # 解析基础配置文件路径
        base_config_dirs = ['config', 'base', 'bugly_config.xml']
        base_config = os.sep.join(base_config_dirs)
        self.base_config = os.path.join(self.work_path, base_config)

        # 先解析配置
        configParser = BuildConfigParser(self.base_config)
        configParser.parse()
        self.ori_build_config = configParser.get_config()
        pass

    """
    上传符号表
    """
    def uploadSymbol(self, ver_env, app_code, app_version, mapping_path):
        app_config = self.ori_build_config[app_code]
        bundle_id = app_config[BuilderLabel.BUNDLE_ID]
        env_config = app_config[BuilderLabel.DEV]
        if ver_env in app_config.keys():
            env_config = app_config[ver_env]
        app_id = env_config[BuilderLabel.APP_ID]
        app_key = env_config[BuilderLabel.APP_KEY]
        lib_path = os.path.join(self.work_path, self.ori_build_config[BuilderLabel.PATH][BuilderLabel.LIB])
        jdk_path = ''
        if BuilderLabel.JDK in self.ori_build_config[BuilderLabel.PATH].keys():
            jdk_path = self.ori_build_config[BuilderLabel.PATH][BuilderLabel.JDK]
        exec_cmd = f'{jdk_path}java -jar {lib_path} -appid {app_id} -appkey {app_key} -bundleid {bundle_id} -version {app_version} -platform Android -inputMapping {mapping_path}'
        try:
            subprocess.check_call(exec_cmd, shell=True)
        except subprocess.CalledProcessError:
            raise


# if __name__ == '__main__':
#     work_path = 'D:/tools/package_app/public/build_script/android/app'
#     mapping_path = 'D:/tools/bugly/mapping.txt'
#     manager = BuglyManager(work_path)
#     manager.uploadSymbol('dev', 'txxy', '6.0.0beta_d_01', mapping_path)
