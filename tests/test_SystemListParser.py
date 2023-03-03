import unittest
from unittest.mock import Mock
from susepatching import SystemListParser


class TestSystemListParser(unittest.TestCase):

    def setUp(self):
        client = Mock()
        client.systemgroup.listSystems.return_value = ["server1", "server2", "server3"]
        self.parser = SystemListParser(client, "not-used-filename")

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

    def test_systemListParserGroupItems(self):
        self.parser._add_system("group:my-servers-group,2023-03-03 18:00:00")
        self.assertDictEqual({"2023-03-03 18:00:00": ["server1", "server2", "server3"]}, self.parser.get_systems())
