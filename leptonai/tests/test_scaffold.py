import unittest


class TestImport(unittest.TestCase):
    def test_import_has_photon(self):
        import leptonai

        self.assertTrue(hasattr(leptonai, "photon"))


if __name__ == "__main__":
    unittest.main()
