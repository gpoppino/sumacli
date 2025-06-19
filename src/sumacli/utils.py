import logging
from xmlrpc.client import Fault

from .scheduler import SchedulerFactory, Scheduler


class SystemPackageRefreshScheduler(Scheduler):

    def __init__(self, client, system, date):
        self.__client = client
        self.__system = system
        self.__date = date
        self.__logger = logging.getLogger(__name__)

    def schedule(self):
        action_ids = []
        try:
            action_ids.append(self.__client.system.schedulePackageRefresh(self.__system.get_id(self.__client), self.__date))
            self.__logger.debug(f"Successfully scheduled package refresh with action ID {action_ids}")
        except Fault as err:
            self.__logger.error(f"Failed to schedule package refresh for system {self.__system.name}")
            self.__logger.error("Fault code: %d" % err.faultCode)
            self.__logger.error("Fault string: %s" % err.faultString)
            return None
        except ValueError as err:
            self.__logger.error(err)
            return None
        return action_ids


class SystemRebootScheduler(Scheduler):

    def __init__(self, client, system, date):
        self.__client = client
        self.__system = system
        self.__date = date
        self.__logger = logging.getLogger(__name__)

    def schedule(self):
        action_ids = []
        try:
            action_ids.append(self.__client.system.scheduleReboot(self.__system.get_id(self.__client), self.__date))
            self.__logger.debug(f"Successfully scheduled reboot with action ID {action_ids}")
        except Fault as err:
            self.__logger.error(f"Failed to schedule reboot for system {self.__system.name}")
            self.__logger.error("Fault code: %d" % err.faultCode)
            self.__logger.error("Fault string: %s" % err.faultString)
            return None
        except ValueError as err:
            self.__logger.error(err)
            return None
        return action_ids


class UtilsSchedulerFactory(SchedulerFactory):

    def get_scheduler(self, client, system, schedule_date, args):
        if args.package_refresh:
            scheduler = SystemPackageRefreshScheduler(client, system, schedule_date)
        elif args.reboot:
            scheduler = SystemRebootScheduler(client, system, schedule_date)
        else:
            raise ValueError("No option specified")
        return scheduler
