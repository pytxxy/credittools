import os
import xmltodict
import creditutils.file_util as file_util

class ConfigParser:
    DEFAULT_ROOT_TAG = 'config'

    def __init__(self, config_path, root_tag=DEFAULT_ROOT_TAG):
        self.config_path = config_path
        self.root_tag = root_tag

    def parse(self):
        doc = xmltodict.parse(file_util.read_file_content(self.config_path))
        self.data = doc[self.root_tag]

    def get_config(self):
        return self.data

    @staticmethod
    def parse_config(config_path, root_tag=DEFAULT_ROOT_TAG):
        parser = ConfigParser(config_path, root_tag=root_tag)
        parser.parse()
        return parser.get_config()