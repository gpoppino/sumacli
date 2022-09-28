import unittest
from susePatching import SumaClient

class TestSumaClient(unittest.TestCase):

    def setUp(self):
        self.client = SumaClient()

    def tearDown(self):
        self.client = None

    def test_login(self):
        self.assertFalse(self.client.isLoggedIn())

        self.client.login()
        self.assertTrue(self.client.isLoggedIn())

        self.client.logout()
        self.assertFalse(self.client.isLoggedIn())
