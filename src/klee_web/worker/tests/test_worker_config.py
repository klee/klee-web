import unittest

import fakeredis
from worker.worker_config import WorkerConfig


class TestWorkerConfig(unittest.TestCase):
    def setUp(self):
        self.worker_config = WorkerConfig()
        self.worker_config.r = fakeredis.FakeStrictRedis()

    def test_redis_set(self):
        key, value = "key_set", "5"
        self.worker_config.set_config(key, value)
        self.assertEqual(int(value), self.worker_config.get_config(key))

    def test_redis_get_nonexistent_key(self):
        self.assertEqual(None, self.worker_config.get_config("invalid_key"))

    def test_redis_correct_casting(self):
        key, value = "key_casting", 5
        self.worker_config.set_config(key, value)
        self.assertEqual(value, self.worker_config.get_config(key))

    def test_redis_doesnt_cast_strings(self):
        key, value = "key_string_casting", b"value"
        self.worker_config.set_config(key, value)
        self.assertEqual(value, self.worker_config.get_config(key))

    def test_timeout_cpu_and_memory_defaults(self):
        timeout_val_defualt = 600
        cpu_share_default = 100
        memory_limit_default = 1024

        self.assertEqual(timeout_val_defualt, self.worker_config.timeout)
        self.assertEqual(cpu_share_default, self.worker_config.cpu_share)
        self.assertEqual(memory_limit_default, self.worker_config.memory_limit)

    def test_timeout_cpu_and_memory_properties(self):
        timeout, timeout_val = "timeout", "10"
        cpu_share, cpu_share_val = "cpu_share", "20"
        memory_limit, memory_limit_val = "memory_limit", "30"

        self.worker_config.set_config(timeout, timeout_val)
        self.worker_config.set_config(cpu_share, cpu_share_val)
        self.worker_config.set_config(memory_limit, memory_limit_val)

        self.assertEqual(int(timeout_val), self.worker_config.timeout)
        self.assertEqual(int(cpu_share_val), self.worker_config.cpu_share)
        self.assertEqual(int(memory_limit_val),
                         self.worker_config.memory_limit)


if __name__ == '__main__':
    unittest.main()
