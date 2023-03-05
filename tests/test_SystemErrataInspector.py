import unittest
from unittest.mock import Mock
from susepatching import AdvisoryType
from susepatching import SystemErrataInspector
from susepatching import System


class TestSystemErrataInspector(unittest.TestCase):

    def setUp(self):
        self.system = System("mysystem.suse.local")

    def test_hasSuggestedReboot(self):
        client = Mock()
        client.system.getRelevantErrata.return_value = [{"advisory_name": "My Advisory"}]
        client.errata.listKeywords.return_value = ['testing', 'having fun', 'reboot_suggested', "nothing"]
        client.system.getId.return_value = [{'id': '100100001'}]

        system_errata_inspector = SystemErrataInspector(client, self.system, AdvisoryType.ALL)

        self.assertTrue(system_errata_inspector.has_suggested_reboot())

    def test_doesNotHaveSuggestedReboot(self):
        client = Mock()
        client.system.getRelevantErrata.return_value = [{"advisory_name": "My Advisory"}]
        client.errata.listKeywords.return_value = ['testing', 'having fun', "nothing", 'restart_suggested']
        client.system.getId.return_value = [{'id': '100100001'}]

        system_errata_inspector = SystemErrataInspector(client, self.system, AdvisoryType.ALL)

        self.assertFalse(system_errata_inspector.has_suggested_reboot())
