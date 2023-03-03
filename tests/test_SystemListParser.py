import unittest
from unittest.mock import Mock
from susepatching import SystemListParser


class TestSystemListParser(unittest.TestCase):

    def setUp(self):
        client = Mock()
        client.systemgroup.listSystems.return_value = [{'country': '', 'rack': '',
                                                        'last_boot': '',
                                                       'lock_status': False, 'virtualization': 'KVM/QEMU',
                                                        'address2': '', 'city': '', 'address1': '', 'release': '15.4',
                                                        'description': '',
                                                        'machine_id': '46ce568287c84ed18d07cf7263d679ed',
                                                        'minion_id': 'branch02.suse.local', 'building': '',
                                                        'room': '', 'profile_name': 'branch02.suse.local',
                                                        'osa_status': 'unknown', 'hostname': 'branch02.suse.local',
                                                        'contact_method': 'default',
                                                        'addon_entitlements': ['monitoring_entitled'],
                                                        'auto_update': False, 'id': 1000010059, 'state': '',
                                                        'base_entitlement': 'salt_entitled'},
                                                       {'country': '', 'rack': '', 'last_boot': '',
                                                        'lock_status': False, 'virtualization': 'KVM/QEMU',
                                                        'address2': '', 'city': '', 'address1': '', 'release': '12.5',
                                                        'description': '',
                                                        'machine_id': '38546cbdff384e72ae86c037f06e9dd6',
                                                        'minion_id': 'instance-lab-c_rehash-0.suse.local',
                                                        'building': '', 'room': '',
                                                        'profile_name': 'instance-lab-c_rehash-0.suse.local',
                                                        'osa_status': 'unknown',
                                                        'hostname': 'instance-lab-c_rehash-0.suse.local',
                                                        'contact_method': 'default',
                                                        'addon_entitlements': [], 'auto_update': False,
                                                        'id': 1000010172, 'state': '',
                                                        'base_entitlement': 'salt_entitled'}]
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
        self.assertDictEqual({"2023-03-03 18:00:00": ["branch02.suse.local", "instance-lab-c_rehash-0.suse.local"]},
                             self.parser.get_systems())
