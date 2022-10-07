import unittest
from unittest.mock import Mock
from susePatching import AdvisoryType
from susePatching import SystemErrataInspector

class TestSystemErrataInspector(unittest.TestCase):

    def setUp(self):
        pass

    def test_hasSuggestedReboot(self):
        client = Mock()
        client.system.getRelevantErrata.return_value = [{"advisory_name": "My Advisory"}]
        client.errata.listKeywords.return_value = ['testing', 'having fun', 'reboot_suggested', "nothing"]
        client.system.getId.return_value = [{'id': '100100001'}]

        systemErrataInspector = SystemErrataInspector(client, "mysystem.suse.local", AdvisoryType.ALL)

        self.assertTrue(systemErrataInspector.hasSuggestedReboot())

    def test_doesNotHaveSuggestedReboot(self):
        client = Mock()
        client.system.getRelevantErrata.return_value = [{"advisory_name": "My Advisory"}]
        client.errata.listKeywords.return_value = ['testing', 'having fun', "nothing", 'restart_suggested']
        client.system.getId.return_value = [{'id': '100100001'}]

        systemErrataInspector = SystemErrataInspector(client, "mysystem.suse.local", AdvisoryType.ALL)

        self.assertFalse(systemErrataInspector.hasSuggestedReboot())

    def test_RaisesValueErrorNoSuchSystem(self):
        client = Mock()
        client.system.getId.return_value = []

        systemErrataInspector = SystemErrataInspector(client, "mysystem.suse.local", AdvisoryType.ALL)

        with self.assertRaises(ValueError):
            systemErrataInspector.getSystemId()
