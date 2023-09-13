import base64
import requests
import tempfile
import unittest

from leptonai._internal.client_utils import get_file_content
from leptonai.photon.types.fileparam import FileParam


class TestClientUtils(unittest.TestCase):
    def test_get_file_content(self):
        msg = b"some random message"
        file_param = FileParam(msg)
        self.assertEqual(get_file_content(file_param), msg)

        with tempfile.NamedTemporaryFile() as f:
            f.write(msg)
            f.flush()
            self.assertEqual(get_file_content(f.name, allow_local_file=True), msg)

        try:
            content = get_file_content("https://www.google.com/robots.txt")
        except requests.ConnectionError:
            pass
        else:
            self.assertIn(b"User-agent", content)

        encoded = base64.b64encode(msg).decode("utf-8")
        self.assertEqual(get_file_content(encoded), msg)
        self.assertEqual(get_file_content("data:media/txt;base64," + encoded), msg)

        self.assertRaises(TypeError, get_file_content, 1)
        self.assertRaises(TypeError, get_file_content, [])
        self.assertRaises(TypeError, get_file_content, {})
        self.assertRaises(TypeError, get_file_content, [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
