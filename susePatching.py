#!/usr/bin/python3

from xmlrpc.client import ServerProxy
from xmlrpc.client import Fault
from datetime import datetime
from enum import Enum
import logging.config
import logging
import configparser
import argparse
import ssl
import sys


class AdvisoryType(Enum):
    SECURITY = 'Security Advisory'
    BUGFIX = 'Bug Fix Advisory'
    PRODUCT_ENHANCEMENT = 'Produt Enhancement Advisory'
    # This is not a SUMA advisory type, but a flag to mark that we will patch the system with all patches available for it
    ALL = 'All Relevant Errata'


class _MultiCallMethod:
    def __init__(self, client, name):
        self.__client = client
        self.__name = name

    def __getattr__(self, name):
        return _MultiCallMethod(self.__client, "%s.%s" % (self.__name, name))

    def __call__(self, *args):
        m = getattr(self.__client.getInstance(), self.__name)
        if args == ():
            return m(self.__client.getSessionKey())
        else:
            return m(self.__client.getSessionKey(), *args)


class SumaClient:

    def __init__(self, config_filename="config.ini"):
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

    def isLoggedIn(self):
        return self.__key is not None

    def getSessionKey(self):
        return self.__key

    def getInstance(self):
        return self.__client


class SystemPatchingScheduler:

    def __init__(self, client, system, date, advisoryType, rebootRequired, labelPrefix):
        self.__client = client
        self.__system = system
        self.__date = date
        self.__advisoryType = advisoryType
        self.__rebootRequired = rebootRequired
        self.__labelPrefix = labelPrefix
        self.__systemErrataInspector = SystemErrataInspector(client, system, advisoryType)
        self.__logger = logging.getLogger(__name__)

    def schedule(self):
        scheduleDate = datetime.strptime(self.__date, "%Y-%m-%d %H:%M:%S")
        if self.__systemHasInProgressAction(self.__system, scheduleDate):
            self.__logger.error("System '" + self.__system + "' already has an action in progress for " + self.__date + ". Skipped...")
            return False

        try:
            errata = self.__systemErrataInspector.obtainSystemErrata()
        except ValueError as err:
            self.__logger.error(err)
            return False

        if errata == []:
            self.__logger.warning("No patches of type '" + self.__advisoryType.value +
                  "' available for system: " + self.__system + " . Skipping...")
            return False

        label = self.__labelPrefix + "-" + self.__system + str(self.__date)
        try:
            self.__createActionChain(
                label, self.__system, errata, self.__rebootRequired)
        except Fault as err:
            self.__logger.error("Failed to create action chain for system: " + self.__system)
            self.__logger.error("Fault code: %d" % err.faultCode)
            self.__logger.error("Fault string: %s" % err.faultString)
            return False

        if self.__client.actionchain.scheduleChain(label, scheduleDate) == 1:
            return True
        return False

    def getAdvisoryType(self):
        return self.__advisoryType

    def __systemHasInProgressAction(self, system, scheduleDate):
        inProgressActions = self.__client.schedule.listInProgressActions()
        for action in inProgressActions:
            converted = datetime.strptime(action['earliest'].value, "%Y%m%dT%H:%M:%S").isoformat()
            if scheduleDate.isoformat() == converted:
                for s in self.__client.schedule.listInProgressSystems(action['id']):
                    if s['server_name'] == system:
                        return True
        return False

    def __createActionChain(self, label, system, errata, requiredReboot):
        actionId = self.__client.actionchain.createChain(label)
        if actionId > 0:
            self.__addErrataToActionChain(system, errata, label)
            if requiredReboot or self.__systemErrataInspector.hasSuggestedReboot():
                self.__addSystemRebootToActionChain(system, label)
        return actionId

    def __addErrataToActionChain(self, system, errata, label):
        errataIds = []
        for patch in errata:
            errataIds.append(patch['id'])
        return self.__client.actionchain.addErrataUpdate(self.__systemErrataInspector.getSystemId(), errataIds, label)

    def __addSystemRebootToActionChain(self, system, label):
        return self.__client.actionchain.addSystemReboot(self.__systemErrataInspector.getSystemId(), label)


class SystemErrataInspector:

    def __init__(self, client, system, advisoryType):
        self.__client = client
        self.__system = system
        self.__advisoryType = advisoryType
        self.__errata = []

    def hasSuggestedReboot(self):
        for patch in self.obtainSystemErrata():
            keywords = self.__client.errata.listKeywords(patch['advisory_name'])
            if 'reboot_suggested' in keywords:
                return True
        return False

    def obtainSystemErrata(self):
        if self.__errata != []:
            return self.__errata
        if self.__advisoryType == AdvisoryType.ALL:
            self.__errata = self.__client.system.getRelevantErrata(self.getSystemId())
        else:
            self.__errata = self.__client.system.getRelevantErrataByType(self.getSystemId(), self.__advisoryType.value)
        return self.__errata

    def getSystemId(self):
        if len(self.__client.system.getId(self.__system)) == 0:
            raise ValueError("No such system: " + self.__system)
        return self.__client.system.getId(self.__system)[0]['id']


class SystemListParser:

    def __init__(self, sFilename):
        self.__filename = sFilename
        self.__systems = {}
        self.__logger = logging.getLogger(__name__)

    def parse(self):
        with open(self.__filename) as f:
            for line in f:
                if not self._addSystem(line):
                    self.__logger.error("Line skipped: " + line)
        return self.__systems

    def getSystems(self):
        return self.__systems

    def _addSystem(self, line):
        if len(line.strip()) == 0:
            return False
        try:
            s, d = line.split(',')
        except ValueError:
            return False
        s = s.strip()
        d = d.strip()
        if d not in self.__systems.keys():
            self.__systems[d] = []
        self.__systems[d].append(s)
        return True

# Exit codes:
# 0  success. every system has been scheduled for patching
# 2  total failure. improper command line options passed
# 64 partial failure. partial systems scheduling has failed
# 65 total failure. all systems scheduling has failed
# 66 total failure. all systems scheduling has failed due to improper input

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "filename", help="Name of the file in which systems and their schedules for patching are listed.")
    parser.add_argument(
        "-a", "--allpatches", help="Apply all available patches to each system.", action="store_true")
    parser.add_argument(
        "-r", "--reboot", help="Add a system reboot to each action chain for each system.", action="store_true")
    args = parser.parse_args()

    logging.config.fileConfig('logging.conf')
    logger = logging.getLogger(__name__)

    systems = SystemListParser(args.filename).parse()
    if systems == {}:
        logger.error("No systems found in file: " + args.filename)
        logger.error("The format of the file is: systemName,year-month-day hour:minute:second")
        logger.error("Example: suma-client,2021-11-06 10:00:00")
        sys.exit(66)

    exit_code = 0
    failed_systems = 0
    success_systems = 0
    client = SumaClient()
    client.login()
    for date in systems.keys():
        if datetime.strptime(date, "%Y-%m-%d %H:%M:%S") < datetime.now():
            logger.warning("Date " + date +
                  " is in the past! System(s) skipped: " + str(systems[date]))
            continue
        for system in systems[date]:
            patchingScheduler = SystemPatchingScheduler(
                client, system, date, AdvisoryType.ALL if args.allpatches else AdvisoryType.SECURITY, args.reboot, "patching")
            if patchingScheduler.schedule():
                logger.info("SUCCESS => " + system + " scheduled successfully for " +
                      patchingScheduler.getAdvisoryType().value + " patching at " + date)
                success_systems += 1
            else:
                logger.error("FAILED => " + system + " failed to be scheduled for " +
                      patchingScheduler.getAdvisoryType().value + " patching at " + date)
                failed_systems += 1
    client.logout()
    if failed_systems > 0 and success_systems > 0:
        exit_code = 64
    elif failed_systems > 0 and success_systems == 0:
        exit_code = 65
    elif failed_systems == 0 and success_systems > 0:
        exit_code = 0
    sys.exit(exit_code)
