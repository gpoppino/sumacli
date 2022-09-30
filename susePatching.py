#!/usr/bin/python3

from xmlrpc.client import ServerProxy
from xmlrpc.client import Fault
from datetime import datetime
from enum import Enum
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


class SumaClient:

    def __init__(self, config_filename="config.ini"):
        config = configparser.ConfigParser()
        config.read(config_filename)

        self.__MANAGER_URL = config['server']['api_url']
        self.__MANAGER_LOGIN = config['credentials']['username']
        self.__MANAGER_PASSWORD = config['credentials']['password']
        self.__key = None

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

    def schedule(self):
        errata = self.__systemErrataInspector.obtainSystemErrata()
        if errata == []:
            print("No patches of type '" + self.__advisoryType.value +
                  "' available for system: " + self.__system + " . Skipping...")
            return False

        label = self.__labelPrefix + "-" + self.__system + str(self.__date)
        try:
            self.__createActionChain(
                label, self.__system, errata, self.__rebootRequired)
        except Fault as err:
            print("Failed to create action chain for system: " + self.__system)
            print("Fault code: %d" % err.faultCode)
            print("Fault string: %s" % err.faultString)
            return False

        if self.__client.getInstance().actionchain.scheduleChain(self.__client.getSessionKey(), label, datetime.strptime(self.__date, "%Y-%m-%d %H:%M:%S")) == 1:
            return True
        return False

    def getAdvisoryType(self):
        return self.__advisoryType

    def __createActionChain(self, label, system, errata, requiredReboot):
        actionId = self.__client.getInstance().actionchain.createChain(
            self.__client.getSessionKey(), label)
        if actionId > 0:
            self.__addErrataToActionChain(system, errata, label)
            if requiredReboot or self.__systemErrataInspector.hasSuggestedReboot():
                self.__addSystemRebootToActionChain(system, label)
        return actionId

    def __addErrataToActionChain(self, system, errata, label):
        errataIds = []
        for patch in errata:
            errataIds.append(patch['id'])
        return self.__client.getInstance().actionchain.addErrataUpdate(self.__client.getSessionKey(), self.__systemErrataInspector.getSystemId(), errataIds, label)

    def __addSystemRebootToActionChain(self, system, label):
        return self.__client.getInstance().actionchain.addSystemReboot(self.__client.getSessionKey(), self.__systemErrataInspector.getSystemId(), label)


class SystemErrataInspector:

    def __init__(self, client, system, advisoryType):
        self.__client = client
        self.__system = system
        self.__advisoryType = advisoryType
        self.__errata = []

    def hasSuggestedReboot(self):
        for patch in self.obtainSystemErrata():
            keywords = self.__client.getInstance().errata.listKeywords(self.__client.getSessionKey(), patch['advisory_name'])
            if 'reboot_suggested' in keywords:
                return True
        return False

    def obtainSystemErrata(self):
        if self.__errata != []:
            return self.__errata
        if self.__advisoryType == AdvisoryType.ALL:
            self.__errata = self.__client.getInstance().system.getRelevantErrata(self.__client.getSessionKey(), self.getSystemId())
        else:
            self.__errata = self.__client.getInstance().system.getRelevantErrataByType(self.__client.getSessionKey(),
                self.getSystemId(), self.__advisoryType.value)
        return self.__errata

    def getSystemId(self):
        return self.__client.getInstance().system.getId(self.__client.getSessionKey(), self.__system)[0]['id']


class SystemListParser:

    def __init__(self, sFilename):
        self.__filename = sFilename
        self.__systems = {}

    def parse(self):
        with open(self.__filename) as f:
            for line in f:
                if not self._addSystem(line):
                    print("Line skipped: " + line)
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "filename", help="Name of the file in which systems and their schedules for patching are listed.")
    parser.add_argument(
        "-a", "--allpatches", help="Apply all available patches to each system.", action="store_true")
    parser.add_argument(
        "-r", "--reboot", help="Add a system reboot to each action chain for each system.", action="store_true")
    args = parser.parse_args()

    systems = SystemListParser(args.filename).parse()
    if systems == {}:
        print("No systems found in file: " + args.filename)
        print("The format of the file is: systemName,year-month-day hour:minute:second")
        print("Example: suma-client,2021-11-06 10:00:00")
        sys.exit(0)

    client = SumaClient()
    client.login()
    for date in systems.keys():
        if datetime.strptime(date, "%Y-%m-%d %H:%M:%S") < datetime.now():
            print("Date " + date +
                  " is in the past! System(s) skipped: " + str(systems[date]))
            continue
        for system in systems[date]:
            patchingScheduler = SystemPatchingScheduler(
                client, system, date, AdvisoryType.ALL if args.allpatches else AdvisoryType.SECURITY, args.reboot, "patching")
            if patchingScheduler.schedule():
                print("SUCCESS => " + system + " scheduled successfully for " +
                      patchingScheduler.getAdvisoryType().value + " patching at " + date)
            else:
                print("FAILED => " + system + " failed to be scheduled for " +
                      patchingScheduler.getAdvisoryType().value + " patching at " + date)
    client.logout()
