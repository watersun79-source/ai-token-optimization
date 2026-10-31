import asyncio
import unittest

from tools.loopback_io_v844 import probe_local_tcp


class LocalIoTests(unittest.TestCase):
    def test_real_256_localhost_tcp_overlap(self):
        r = asyncio.run(probe_local_tcp(256))
        self.assertEqual(r["status"], "PASS")
        self.assertEqual(r["peak_server_connections_waiting"], 256)
        self.assertEqual(r["unique_completed"], 256)
        self.assertEqual(r["os_process_count"], 1)
        self.assertFalse(r["external_network_used"])
        self.assertFalse(r["hosted_24h_verified"])

    def test_small_batches(self):
        for n in (1, 4, 16):
            self.assertEqual(asyncio.run(probe_local_tcp(n))["status"], "PASS")

    def test_invalid_limits(self):
        for value in (0, 257, True, -1, 1.5):
            with self.assertRaises(ValueError):
                asyncio.run(probe_local_tcp(value))

    def test_invalid_timeout(self):
        for value in (0, 31, True, -1):
            with self.assertRaises(ValueError):
                asyncio.run(probe_local_tcp(1, value))


if __name__ == "__main__":
    unittest.main()
