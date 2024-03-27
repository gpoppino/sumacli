import unittest
from unittest.mock import Mock
from suma.client_systems import SystemListParser


class TestSystemListParser(unittest.TestCase):

    def setUp(self):
        self.system1 = "instance-k3s-1.suse.local"
        self.system2 = "instance-k3s-2.suse.local"
        self.system3 = "instance-k3s-3.suse.local"
        self.date1 = "2022-10-07 17:45:00"
        self.date2 = "2022-10-08 17:50:00"
        self.date3 = "2023-03-03 18:00:00"

        client = Mock()
        client.systemgroup.listSystems.return_value = [{'country': '', 'rack': '',
                                                        'last_boot': '',
                                                       'lock_status': False, 'virtualization': 'KVM/QEMU',
                                                        'address2': '', 'city': '', 'address1': '', 'release': '15.4',
                                                        'description': '',
                                                        'machine_id': '46ce568287c84ed18d07cf7263d679ed',
                                                        'minion_id': self.system1, 'building': '',
                                                        'room': '', 'profile_name': self.system1,
                                                        'osa_status': 'unknown',
                                                        'hostname': self.system1,
                                                        'contact_method': 'default',
                                                        'addon_entitlements': ['monitoring_entitled'],
                                                        'auto_update': False, 'id': 1000010059, 'state': '',
                                                        'base_entitlement': 'salt_entitled'},
                                                       {'country': '', 'rack': '', 'last_boot': '',
                                                        'lock_status': False, 'virtualization': 'KVM/QEMU',
                                                        'address2': '', 'city': '', 'address1': '', 'release': '12.5',
                                                        'description': '',
                                                        'machine_id': '38546cbdff384e72ae86c037f06e9dd6',
                                                        'minion_id': self.system2,
                                                        'building': '', 'room': '',
                                                        'profile_name': self.system2,
                                                        'osa_status': 'unknown',
                                                        'hostname': self.system2,
                                                        'contact_method': 'default',
                                                        'addon_entitlements': [], 'auto_update': False,
                                                        'id': 1000010172, 'state': '',
                                                        'base_entitlement': 'salt_entitled'}]
        self.parser = SystemListParser(client, "not-used-filename")

    def test_systemListParserIsEmpty(self):
        self.assertDictEqual({}, self.parser.get_systems())

    def test_systemListParserOneItem(self):
        self.parser._add_system(f"{self.system1},{self.date1}")
        systems = self.parser.get_systems()
        self.assertEqual(self.date1, list(systems.keys())[0])
        self.assertEqual(self.system1, systems[self.date1][0].name)

    def test_systemListParserAllDifferentDateItems(self):
        self.parser._add_system(f"{self.system1},{self.date1}")
        self.parser._add_system(f"{self.system2},{self.date2}")
        systems = self.parser.get_systems()

        self.assertTrue(self.date1 in systems)
        self.assertTrue(self.date2 in systems)
        self.assertEqual(self.system1, systems[self.date1][0].name)
        self.assertEqual(self.system2, systems[self.date2][0].name)

    def test_systemListParserSameDateItems(self):
        self.parser._add_system(f"{self.system1},{self.date1}")
        self.parser._add_system(f"{self.system2},{self.date2}")
        self.parser._add_system(f"{self.system3},{self.date1}")
        systems = self.parser.get_systems()

        self.assertTrue(self.date1 in systems)
        self.assertTrue(self.date2 in systems)
        self.assertEqual(self.system1, systems[self.date1][0].name)
        self.assertEqual(self.system3, systems[self.date1][1].name)
        self.assertEqual(self.system2, systems[self.date2][0].name)

    def test_systemListParserInconsistentInput(self):
        self.assertFalse(self.parser._add_system(f"{self.system1} {self.date3}"))
        self.assertDictEqual({}, self.parser.get_systems())

    def test_systemListParserGroupItems(self):
        self.parser._add_system(f"group:my-servers-group,{self.date3}")
        systems = self.parser.get_systems()

        self.assertTrue(self.date3 in systems)
        self.assertEqual(self.system1, systems[self.date3][0].name)
        self.assertEqual(self.system2, systems[self.date3][1].name)

    def test_systemListParserTargetArgument(self):
        self.parser._add_system(f"{self.system1},{self.date1},target1")
        systems = self.parser.get_systems()
        self.assertEqual("target1", systems[self.date1][0].target)

    def test_systemListParserKoptsArgument(self):
        self.parser._add_system(f"{self.system1},{self.date1},target1,kopts1")
        systems = self.parser.get_systems()
        self.assertEqual("kopts1", systems[self.date1][0].kopts)
