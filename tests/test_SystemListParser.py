import unittest
from susepatching import SystemListParser


class TestSystemListParser(unittest.TestCase):

    def setUp(self):
        self.parser = SystemListParser("not-used-filename")

    def test_systemListParserIsEmpty(self):
        self.assertDictEqual({}, self.parser.get_systems())

    def test_systemListParserOneItem(self):
        self.parser._add_system("instance-k3s-1.suse.local,2022-10-07 17:45:00")
        self.assertDictEqual(
            {"2022-10-07 17:45:00": ["instance-k3s-1.suse.local"]}, self.parser.get_systems())

    def test_systemListParserAllDifferentDateItems(self):
        self.parser._add_system("instance-k3s-1.suse.local,2022-10-07 17:45:00")
        self.parser._add_system("instance-k3s-2.suse.local,2022-10-08 17:50:00")
        self.assertDictEqual({"2022-10-07 17:45:00": ["instance-k3s-1.suse.local"], "2022-10-08 17:50:00": [
                             "instance-k3s-2.suse.local"]}, self.parser.get_systems())

    def test_systemListParserSameDateItems(self):
        self.parser._add_system("instance-k3s-1.suse.local,2022-10-07 17:45:00")
        self.parser._add_system("instance-k3s-2.suse.local,2022-10-08 17:50:00")
        self.parser._add_system("instance-k3s-3.suse.local,2022-10-07 17:45:00")
        self.assertDictEqual({"2022-10-07 17:45:00": ["instance-k3s-1.suse.local", "instance-k3s-3.suse.local"],
                             "2022-10-08 17:50:00": ["instance-k3s-2.suse.local"]}, self.parser.get_systems())

    def test_systemListParserInconsistentInput(self):
        self.assertFalse(self.parser._add_system("instance-k3s-1.suse.local;2023-12-05 13:00:00"))
        self.assertDictEqual({}, self.parser.get_systems())
