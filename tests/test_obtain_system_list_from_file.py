import unittest
import time
import os
from susePatching import obtain_system_list_from_file

class TestObtainSystemListFromFile(unittest.TestCase):

    def setUp(self):
        self.filename = "systems.csv." + str(time.time())
        with open(self.filename, 'w') as f:
            f.write("instance-k3s-1.suse.local,2022-10-07 17:45:00\n")
            f.write("instance-k3s-2.suse.local,2022-10-08 17:50:00\n")
            f.write("\n")
            f.write("instance-k3s-3.suse.local,2022-10-07 17:45:00\n")
            f.write("instance-k3s-4.suse.local,2022-10-07 17:46:00\n")
            f.write("\n")
            f.close()

    def tearDown(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)

    def test_obtain_system_list_from_file(self):
        systems = obtain_system_list_from_file(self.filename)
        self.assertEqual(systems["2022-10-07 17:45:00"], ["instance-k3s-1.suse.local", "instance-k3s-3.suse.local"])
        self.assertEqual(systems["2022-10-08 17:50:00"], ["instance-k3s-2.suse.local"])
        self.assertEqual(systems["2022-10-07 17:46:00"], ["instance-k3s-4.suse.local"])
