import time
from typing import Tuple
import unittest
from unittest.mock import Mock, MagicMock, patch
from central_control import Producer, Consumer


class Test(unittest.TestCase):

    def setUp(self):
        producer = Producer.get_instance()
        self.consumer = Consumer(producer)

    def tearDown(self):
        del self.consumer
        obj = Producer.get_instance()
        del obj

    def testProducer_queue(self):
        producer = Producer.get_instance()
        a = 'what'
        producer.put(a)
        b = producer.get()
        self.assertEqual(b, a, f'b: {b}, a: {a}')

    def testProducer_get_new_index(self):
        first = 1
        producer = Producer.get_instance()
        index_f = producer.get_new_index()
        self.assertEqual(index_f, first, f'index_f: {index_f}, first: {first}')
        index_s = producer.get_new_index()
        second = index_f + 1
        self.assertEqual(index_s, second, f'index_s: {index_s}, second: {second}')
        
    def testProducer_switch_data(self):
        a = dict()
        index = 10
        a['a'] = 1
        a['b'] = 'what'
        producer = Producer.get_instance()
        producer.set_switch_data(10, a)
        info = producer.get_switch_data(index)
        self.assertEqual(info, a, f'info: {info}, a: {a}')

        is_normal = True
        producer.del_switch_data(index)
        try:
            producer.get_switch_data(index)
            is_normal = False
        except KeyError:
            is_normal = True
        
        self.assertEqual(is_normal, True, f'is_normal: {is_normal}, expected: {True}')

    def testConsumer_get_server_key(self):
        item = ('192.168.1.101', 18861)
        target = '192.168.1.101:18861'
        result = self.consumer.get_server_key(item)
        self.assertEqual(result, target, f'result: {result}, target: {target}')

    def testConsumer_get_server_host_ip(self):
        src = '192.168.1.101:18861'
        host_t = '192.168.1.101'
        ip_t = 18861
        host, ip = self.consumer.get_server_host_ip(src)
        self.assertEqual(host, host_t, f'host: {host}, host_t: {host_t}')
        self.assertEqual(ip, ip_t, f'ip: {ip}, ip_t: {ip_t}')

    def testConsumer_get_new_server_info(self):
        a = (('192.168.1.101', 18861),)
        k = self.consumer.get_server_key(a[0])
        target = dict()
        target[k] = 0
        result = self.consumer.get_new_server_info(a)
        self.assertEqual(result, target, f'result: {result}, target: {target}')

        a = (('192.168.1.101', 18861), ('192.168.2.1', 9920),)
        target = dict()
        k = self.consumer.get_server_key(a[0])
        target[k] = 0
        k = self.consumer.get_server_key(a[1])
        target[k] = 0
        result = self.consumer.get_new_server_info(a)
        self.assertEqual(result, target, f'result: {result}, target: {target}')

    def testConsumer_update_server(self):
        self.consumer.record.clear()
        a = (('192.168.1.101', 18861),)
        self.consumer.update_server(a)
        k = self.consumer.get_server_key(a[0])
        target = dict()
        target[k] = 0
        self.assertEqual(self.consumer.record, target, f'record: {self.consumer.record}, target: {target}')

        b = (('192.168.1.101', 18861), ('192.168.2.1', 9920),)
        self.consumer.update_server(b)
        target = dict()
        k = self.consumer.get_server_key(b[0])
        target[k] = 0
        k = self.consumer.get_server_key(b[1])
        target[k] = 0
        self.assertEqual(self.consumer.record, target, f'record: {self.consumer.record}, target: {target}')

        c = (('192.168.1.101', 18861),)
        k = self.consumer.get_server_key(b[1])
        self.consumer.record[k] += 1
        curr_time = int(time.time())
        self.consumer.time_record[k] = curr_time
        time_fun = Mock(return_value=curr_time+100)
        with patch.object(time, 'time', time_fun) as mock_method:
            self.consumer.update_server(c)
            target = dict()
            j = self.consumer.get_server_key(c[0])
            target[j] = 0
            target[k] = 1
            self.assertEqual(self.consumer.record, target, f'record: {self.consumer.record}, target: {target}')
            mock_method.assert_called_once()

        d = (('192.168.1.101', 18861),)
        k = self.consumer.get_server_key(b[1])
        self.consumer.record[k] -= 1
        self.consumer.update_server(d)
        target = dict()
        j = self.consumer.get_server_key(d[0])
        target[j] = 0
        self.assertEqual(self.consumer.record, target, f'record: {self.consumer.record}, target: {target}')

if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()