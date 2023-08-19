#!/usr/bin/python3

from xmlrpc.client import ServerProxy
from xmlrpc.client import Fault
from datetime import datetime
from enum import Enum
import logging.config
import logging
import configparser
import ssl


class AdvisoryType(Enum):
    SECURITY = 'Security Advisory'
    BUGFIX = 'Bug Fix Advisory'
    PRODUCT_ENHANCEMENT = 'Product Enhancement Advisory'
    # This is not a SUMA advisory type, but a flag to mark that we will patch the system
    # with all patches available for it
    ALL = 'All Relevant Errata'


class _MultiCallMethod:
    def __init__(self, client, name):
        self.__client = client
        self.__name = name

    def __getattr__(self, name):
        return _MultiCallMethod(self.__client, "%s.%s" % (self.__name, name))

    def __call__(self, *args):
        m = getattr(self.__client.get_instance(), self.__name)
        if args == ():
            return m(self.__client.get_session_key())
        else:
            return m(self.__client.get_session_key(), *args)


class SumaClient:

    def __init__(self, config_filename="conf/config.ini"):
        config = configparser.ConfigParser()
        config.read(config_filename)

        self.__MANAGER_URL = config['server']['api_url']
        self.__MANAGER_LOGIN = config['credentials']['username']
        self.__MANAGER_PASSWORD = config['credentials']['password']
        self.__key = None
        self.__client = None

    def __getattr__(self, name):
        return _MultiCallMethod(self, name)

    def login(self):
        if self.__key is not None:
            return
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        self.__client = ServerProxy(self.__MANAGER_URL, context=context)
        self.__key = self.__client.auth.login(
            self.__MANAGER_LOGIN, self.__MANAGER_PASSWORD)

    def logout(self):
        if self.__key is None:
            return
        self.__client.auth.logout(self.__key)
        self.__client("close")()
        self.__key = None

    def is_logged_in(self):
        return self.__key is not None

    def get_session_key(self):
        return self.__key

    def get_instance(self):
        return self.__client


class Scheduler:
    def schedule(self):
        pass


class SystemPatchingScheduler(Scheduler):

    def __init__(self, client, system, date, advisory_types, reboot_required, no_reboot, label_prefix):
        self.__client = client
        self.__system = system
        self.__date = date
        self.__advisoryTypes = advisory_types
        self.__rebootRequired = reboot_required
        self.__noReboot = no_reboot
        self.__labelPrefix = label_prefix
        self.__systemErrataInspector = SystemErrataInspector(client, system, advisory_types)
        self.__logger = logging.getLogger(__name__)

    def schedule(self):
        if self.__system_has_in_progress_action(self.__system.name, self.__date):
            self.__logger.error(f"System {self.__system.name} already has an action in progress at {str(self.__date)}")
            return None

        try:
            errata = self.__systemErrataInspector.obtain_system_errata()
        except ValueError as err:
            self.__logger.error(err)
            return None

        if not errata:
            advisory_types_descriptions = [t.value + " " for t in self.__advisoryTypes]
            self.__logger.warning(f"No patches of type {advisory_types_descriptions} available for system: "
                                  f"{self.__system.name} . Skipping...")
            return None

        label = self.__labelPrefix + "-" + self.__system.name + str(self.__date)
        try:
            action_ids = self.__create_action_chain(label, errata, self.__rebootRequired, self.__noReboot)
        except Fault as err:
            self.__logger.error("Failed to create action chain for system: " + self.__system.name)
            self.__logger.error("Fault code: %d" % err.faultCode)
            self.__logger.error("Fault string: %s" % err.faultString)
            return -1

        if self.__client.actionchain.scheduleChain(label, self.__date) == 1:
            return action_ids
        return None

    def get_advisory_types(self):
        return self.__advisoryTypes

    def __system_has_in_progress_action(self, system, schedule_date):
        in_progress_actions = self.__client.schedule.listInProgressActions()
        for action in in_progress_actions:
            converted = datetime.strptime(action['earliest'].value, "%Y%m%dT%H:%M:%S").isoformat()
            if schedule_date.isoformat() == converted:
                for s in self.__client.schedule.listInProgressSystems(action['id']):
                    if s['server_name'] == system:
                        return True
        return False

    def __create_action_chain(self, label, errata, required_reboot, no_reboot):
        action_ids = []
        if self.__client.actionchain.createChain(label) > 0:
            errata_action_id = self.__add_errata_to_action_chain(errata, label)
            if errata_action_id > 0:
                action_ids.append(errata_action_id)
                self.__logger.debug("Successfully added errata to action chain with label: " + label)
            if required_reboot or self.__systemErrataInspector.has_suggested_reboot() and not no_reboot:
                reboot_action_id = self.__add_system_reboot_to_action_chain(label)
                if reboot_action_id > 0:
                    action_ids.append(reboot_action_id)
                    self.__logger.debug("Successfully added system reboot to action chain with label: " + label)
        return action_ids

    def __add_errata_to_action_chain(self, errata, label):
        errata_ids = []
        for patch in errata:
            errata_ids.append(patch['id'])
        return self.__client.actionchain.addErrataUpdate(self.__system.get_id(self.__client), errata_ids, label)

    def __add_system_reboot_to_action_chain(self, label):
        return self.__client.actionchain.addSystemReboot(self.__system.get_id(self.__client), label)


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


class SystemProductMigrationScheduler(Scheduler):
    def __init__(self, client, system, date):
        self.__client = client
        self.__system = system
        self.__date = date
        self.__logger = logging.getLogger(__name__)

    def schedule(self):
        action_ids = []
        try:
            action_ids.append(self.__client.system.scheduleProductMigration(self.__system.get_id(self.__client),
                                                                            self.__system.migration_target, [], False,
                                                                            self.__date))
            self.__logger.debug(f"Successfully scheduled product migration with action ID {action_ids}")
        except Fault as err:
            self.__logger.error(f"Failed to schedule product migration for system {self.__system.name}")
            self.__logger.error("Fault code: %d" % err.faultCode)
            self.__logger.error("Fault string: %s" % err.faultString)
            return None
        return action_ids


class System:
    def __init__(self, name, migration_target=None):
        self.__name = name
        self.__migration_target = migration_target

    @property
    def name(self):
        return self.__name

    @property
    def migration_target(self):
        return self.__migration_target

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
            for line in f:
                if not self._add_system(line):
                    self.__logger.error("Line skipped: " + line)
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

    def _add_system(self, line):
        if len(line.strip()) == 0:
            return False
        try:
            data = line.split(',')
        except ValueError:
            return False
        if len(data) == 1 or len(data) > 3:
            # system specified but no date or invalid data
            return False
        s = data[0].strip()
        d = data[1].strip()
        target = None
        if len(data) == 3:
            target = data[2]
        if d not in self.__systems.keys():
            self.__systems[d] = []
        if ":" in s:
            group = s.split(':')[1]
            systems = self._get_systems_from_group(group)
            [self.__systems[d].append(System(s.get('profile_name'), target)) for s in systems]
        else:
            self.__systems[d].append(System(s, target))
        return True
