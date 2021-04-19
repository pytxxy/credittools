from rpyc import Service
from rpyc.utils.server import ThreadedServer
from creditutils.trivial_util import print_t

'''
The reason services have names is for the service registry: 
normally, a server will broadcast its details to a nearby registry server for discovery. 
To use service discovery, a make sure you start the bin/rpyc_registry.py. 
This server listens on a broadcast UDP socket, and will answer to queries about which services are running where.

上面是官网原始说明，简单地说，如果要通过服务名称调用服务，则需要调用bin/rpyc_registry.py启动名称服务。实际研究显示，
在一个互通的网络中，启动一个该服务即可。
windows 下面可使用网盘“/develop/python/rpyc/runpy.bat”文件，可简化调用。
'''

class AppService(Service):
    ALIASES = ['execution_unit']

    def __init__(self) -> None:
        super().__init__()
        print_t('init success.')

    def compile(self, data) -> dict:
        '''
        编译完成后输出结果
        :param data: 编译参数
        :return:
        '''
        return None


def start_server():
    obj = AppService()
    s = ThreadedServer(obj, port=9999, auto_register=True)
    s.start()


def main():
    start_server()

if __name__ == '__main__':
    main()
