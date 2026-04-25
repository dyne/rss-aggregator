import io
import unittest

from src import net


class _CloseTrackingBytesIO(io.BytesIO):
    def __init__(self, data):
        super().__init__(data)
        self.closed_by_helper = False

    def close(self):
        self.closed_by_helper = True
        super().close()


class NetTest(unittest.TestCase):
    def test_read_limited_bytes_accepts_exact_limit(self):
        body = net.read_limited_bytes(io.BytesIO(b"abcd"), 4)
        self.assertEqual(b"abcd", body)

    def test_read_limited_bytes_rejects_oversized_body(self):
        with self.assertRaises(net.ResponseTooLarge):
            net.read_limited_bytes(io.BytesIO(b"abcde"), 4)

    def test_read_limited_bytes_closes_response_when_requested(self):
        response = _CloseTrackingBytesIO(b"ok")
        self.assertEqual(b"ok", net.read_limited_bytes(response, 2, close=True))
        self.assertTrue(response.closed_by_helper)
