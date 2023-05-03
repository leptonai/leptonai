import unittest

class TestImport(unittest.TestCase):
    def test_import_has_photon(self):
        import lepton
        self.assertTrue(hasattr(lepton, 'photon'))

