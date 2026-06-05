import unittest


class TestImport(unittest.TestCase):
    def test_version(self):
        from leptonai import __version__

        self.assertIsNotNone(__version__)


if __name__ == "__main__":
    unittest.main()
