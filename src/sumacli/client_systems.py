import csv
import logging
from xmlrpc.client import Fault
from sumacli.advisory_type import AdvisoryType


class SystemErrataInspector:

    def __init__(self, client, system, advisory_types):
        self.__client = client
        self.__system = system
        self.__advisoryTypes = advisory_types
        self.__errata = []

    def has_suggested_reboot(self):
        for patch in self.obtain_system_errata():
            keywords = self.__client.errata.listKeywords(patch['advisory_name'])
            if 'reboot_suggested' in keywords:
                return True
        return False

    def obtain_system_errata(self):
        if self.__errata:
            return self.__errata

        if AdvisoryType.ALL in self.__advisoryTypes:
            self.__errata = self.__client.system.getRelevantErrata(self.__system.get_id(self.__client))
        else:
            for advisoryType in self.__advisoryTypes:
                self.__errata += self.__client.system.getRelevantErrataByType(self.__system.get_id(self.__client),
                                                                              advisoryType.value)
        return self.__errata


class System:
    def __init__(self, name, target=None, kopts=None):
        self.__name = name
        self.__target = target
        self.__kopts = kopts

    @property
    def name(self):
        return self.__name

    @property
    def target(self):
        return self.__target

    @property
    def kopts(self):
        return self.__kopts

    def get_id(self, client):
        system_id = client.system.getId(self.__name)
        if len(system_id) == 0:
            raise ValueError("No such system: " + self.__name)
        return system_id[0]['id']


class SystemListParser:

    def __init__(self, client, systems_filename):
        self.__client = client
        self.__filename = systems_filename
        self.__systems = {}
        self.__logger = logging.getLogger(__name__)

    def parse(self):
        with open(self.__filename) as f:
            csvreader = csv.reader(f)
            for data in csvreader:
                if not self._add_system(data):
                    self.__logger.error(f'Line skipped: {data}')
        return self.__systems

    def get_systems(self):
        return self.__systems

    def _get_systems_from_group(self, group):
        try:
            systems = self.__client.systemgroup.listSystems(group)
        except Fault as err:
            self.__logger.error(err.faultString)
            self.__logger.warning(f'Group "{group}" does not exist!')
            return []
        return systems

    def _add_system(self, data):
        if not data:
            return False
        if len(data) == 1 or len(data) > 4:
            # system specified but no date or invalid data
            return False
        s = data[0].strip()
        d = data[1].strip()
        target = None
        if len(data) >= 3:
            target = data[2].strip()
        kopts = None
        if len(data) == 4:
            kopts = data[3]
        if d not in self.__systems.keys():
            self.__systems[d] = []
        if ":" in s:
            group = s.split(':')[1]
            systems = self._get_systems_from_group(group)
            [self.__systems[d].append(System(s.get('profile_name'), target, kopts)) for s in systems]
        else:
            self.__systems[d].append(System(s, target, kopts))
        return True
