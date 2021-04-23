import time
from typing import Tuple
from rpyc import Service
from rpyc.utils.server import ThreadedServer
import threading
from threading import Event
from queue import Queue
import rpyc
from creditutils.trivial_util import print_t


'''
The reason services have names is for the service registry: 
normally, a server will broadcast its details to a nearby registry server for discovery. 
To use service discovery, a make sure you start the bin/rpyc_registry.py. 
This server listens on a broadcast UDP socket, and will answer to queries about which services are running where.

上面是官网原始说明，简单地说，如果要通过服务名称调用服务，则需要调用bin/rpyc_registry.py启动名称服务。实际研究显示，
在一个互通的网络中，启动一个该服务即可。
windows 下面可使用网盘“/develop/python/rpyc/runpy.bat”文件，可简化调用。

整体策略：
1.维护一个生产者任务队列，所有过来的任务，都放到该队列中。
2.维护一个消费者调度器，负责依据实际执行任务服务的情况，将待处理任务分配给有能力且空闲下来的执行单元进行处理。
3.执行单元处理完毕后，要通知消费者调度器，然后由消费者调度器通知原始调用程序，完成一次任务的闭环。
'''

# 默认监听超时时间
DEFAULT_LISTEN_TIMEOUT = 8*60*60
# DEFAULT_LISTEN_TIMEOUT = 128

# 返回状态值
CODE_SUCCESS = 0
CODE_FAILED = 1

class Flag:
    index = 'index'
    event = 'event'
    data = 'data'

class Producer:
    instance = None

    def __init__(self, size=256) -> None:
        self.size = size
        self.queue = Queue(maxsize=self.size)
        self.switchboard = dict()
        self.curr_index = 0
        self.lock = threading.Lock()

    def put(self, data):
        self.queue.put(data)

    def get(self):
        return self.queue.get()

    def task_done(self):
        return self.queue.task_done()

    def get_new_index(self):
        with self.lock:
            self.curr_index += 1
            return self.curr_index

    def set_switch_data(self, index, info):
        self.switchboard[index] = info

    def get_switch_data(self, index):
        return self.switchboard[index]

    def del_switch_data(self, index):
        del self.switchboard[index]

    @staticmethod
    def get_instance():
        if not Producer.instance:
            Producer.instance = Producer()

        return Producer.instance


class Consumer:
    def __init__(self, producer, unit_name='execution_unit') -> None:
        self.producer = producer
        self.unit_name = unit_name
        self.record = dict()
        self.lock = threading.Lock()

    def process(self):
        thread = threading.Thread(target=self.processor)
        # 设置为守护线程，主线程结束时，该线程也会相应结束。
        thread.setDaemon(True)
        thread.start()

    def processor(self):
        '''
        先查看当前是否有空闲的执行单元，如果有，则从生产者队列中取出一个任务进行分配。
        '''
        to_wait = 0.1
        while True:
            try:
                result = rpyc.discover(self.unit_name)
                self.update_server(result)
                with self.lock:
                    for item in self.record:
                        if self.record[item] <= 0:
                            node = self.producer.get()
                            thread = threading.Thread(target=self.sub_processor, args=(item, node))
                            thread.start()
                            self.record[item] += 1
            except rpyc.utils.factory.DiscoveryError:
                print_t(f'not found server with name {self.unit_name}!')
                
            # 先等待一段时间
            time.sleep(to_wait)

    def sub_processor(self, *args, **kwargs):
        item = args[0]
        node = args[1]
        host, ip = self.get_server_host_ip(item)
        conn = rpyc.connect(host, ip)
        index = node[Flag.index]
        param = node[Flag.data]
        try:
            result = conn.root.compile(param)
        except TimeoutError:
            result = (CODE_FAILED, 'call compile timeout in central_control!')
            
        # print_t(result)
        conn.close()
        info = self.producer.get_switch_data(index)
        self.producer.task_done()
        info[Flag.data] = result
        info[Flag.event].set()
        with self.lock:
            self.record[item] -= 1

    def get_new_server_info(self, info):
        server_map = dict()
        for item in info:
            k = self.get_server_key(item)
            server_map[k] = 0

        return server_map

    def update_server(self, result):
        server_map = self.get_new_server_info(result)
        with self.lock:
            for item in server_map:
                if item not in self.record:
                    self.record[item] = 0
            
            # 对于已经消失的服务节点，如果当前处于闲置状态，则清除出去。
            to_del_list = list()
            for item in self.record:
                if item not in server_map:
                    if self.record[item] <= 0:
                        to_del_list.append(item)

            for k in to_del_list:
                del self.record[k]

    def get_server_key(self, item):
        ip = item[0]
        port = item[1]
        return f'{ip}:{port}'

    def get_server_host_ip(self, k):
        items = k.split(':')
        return items[0], int(items[1])


class CentralControlService(Service):
    ALIASES = ['central_control']

    def __init__(self) -> None:
        super().__init__()
        print_t('init success.')

    def exposed_process(self, data) -> Tuple[int, str]:
        '''
        实现Android版本的编译
        :param data: 所有调用编译需要用到的参数
        :return: 调用结果状态
        '''
        producer = Producer.get_instance()
        index = producer.get_new_index()
        info = dict()
        info[Flag.event] = Event()
        info[Flag.event].clear()
        info[Flag.data] = None
        producer.set_switch_data(index, info)
        target = dict()
        target[Flag.index] = index
        target[Flag.data] = data

        print_t('to put queue.')
        producer.put(target)

        print_t('wait to been processed.')
        info[Flag.event].wait()

        print_t('process completed.')
        result = info[Flag.data]

        producer.del_switch_data(index)

        return result


def start_server():
    producer = Producer.get_instance()
    consumer = Consumer(producer)
    consumer.process()
    s = ThreadedServer(CentralControlService, port=9999, auto_register=True, listener_timeout=DEFAULT_LISTEN_TIMEOUT)
    s.start()


def main():
    start_server()


if __name__ == '__main__':
    main()
