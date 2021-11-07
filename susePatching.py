#!/usr/bin/python3

from xmlrpc.client import ServerProxy
from datetime import datetime
import ssl
import sys

class SumaClient:

    def __init__(self):
        self.__MANAGER_URL = "https://localhost:8443/rpc/api"
        self.__MANAGER_LOGIN = "your-username"
        self.__MANAGER_PASSWORD = "your-password"
        self.__key = None

    def login(self):
        if self.__key != None:
            return
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        self.__client = ServerProxy(self.__MANAGER_URL, context=context)
        self.__key = self.__client.auth.login(self.__MANAGER_LOGIN, self.__MANAGER_PASSWORD)

    def logout(self):
        if self.__key == None:
            return
        self.__client.auth.logout(self.__key)

    def isLoggedIn(self):
        return self.__key != None

    def getSessionKey(self):
        return self.__key

    def getInstance(self):
        return self.__client

class SystemPatchingScheduler:

    def __init__(self, client, system, date, patchType, rebootRequired, labelPrefix):
        self.__client = client
        self.__system = system
        self.__date = date
        self.__patchType = patchType
        self.__rebootRequired = rebootRequired
        self.__labelPrefix = labelPrefix

    def schedule(self):
        errata = self.__obtainSystemErrata(self.__system, self.__patchType)
        if errata == []:
            print("No patches of type " + self.__patchType + " available for system: " + self.__system + " . Skipping...")
            return False
        label = self.__labelPrefix + "-" + self.__system + str(self.__date)
        try:
            self.__createActionChain(label, self.__system, errata, self.__rebootRequired)
        except:
            print("Failed to create action chain for system: " + self.__system)
            return False
        if self.__client.getInstance().actionchain.scheduleChain(self.__client.getSessionKey(), label, datetime.strptime(self.__date, "%Y-%m-%d %H:%M:%S")) == 1:
            return True
        return False

    def getPatchType(self):
        return self.__patchType

    def __getSystemId(self, system):
        return self.__client.getInstance().system.getId(self.__client.getSessionKey(), system)[0]['id'] # TODO: tener en cuenta varios sistemas con el mismo nombre

    def __obtainSystemErrata(self, system, patchType):
        return self.__client.getInstance().system.getRelevantErrataByType(self.__client.getSessionKey(), self.__getSystemId(system), patchType)

    def __createActionChain(self, label, system, errata, requiredReboot):
        actionId = self.__client.getInstance().actionchain.createChain(self.__client.getSessionKey(), label)
        if actionId > 0:
            self.__addErrataToActionChain(system, errata, label)
            if requiredReboot:
                self.__addSystemRebootToActionChain(system, label)
        return actionId

    def __addErrataToActionChain(self, system, errata, label):
        errataIds = []
        for patch in errata:
            errataIds.append(patch['id'])
        return self.__client.getInstance().actionchain.addErrataUpdate(self.__client.getSessionKey(), self.__getSystemId(system), errataIds, label)

    def __addSystemRebootToActionChain(self, system, label):
        return self.__client.getInstance().actionchain.addSystemReboot(self.__client.getSessionKey(), self.__getSystemId(system), label)

def obtain_system_list_from_file(filename):
    systems = {}
    with open(filename) as f:
        for line in f:
            s, d = line.split(',')
            if d.rstrip() not in systems.keys():
                systems[d.rstrip()] = []
            systems[d.rstrip()].append(s)
    return systems

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: " + sys.argv[0] + " filename.csv")
        sys.exit(1)

    systems = obtain_system_list_from_file(sys.argv[1])
    if systems == {}:
        print("No systems found in file: " + sys.argv[1])
        print("The format of the file is: systemName,year-month-day hour:minute:second")
        print("Example: suma-client,2021-11-06 10:00:00")
        sys.exit(0)

    client = SumaClient()
    client.login()
    for date in systems.keys():
        if datetime.strptime(date, "%Y-%m-%d %H:%M:%S") < datetime.now():
            print("Date " + date + " is in the past! System(s) skipped: " + str(systems[date]))
            continue
        for system in systems[date]:
            patchingScheduler = SystemPatchingScheduler(client, system, date, 'Security Advisory', True, "security-patching")
            if patchingScheduler.schedule():
                print("SUCCESS => " + system + " scheduled successfully for " + patchingScheduler.getPatchType() + " patching at " + date)
            else:
                print("FAILED => " + system + " failed to be scheduled for " + patchingScheduler.getPatchType() + " patching at " + date)
    client.logout()
