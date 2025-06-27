import logging
from xmlrpc.client import Fault

from .scheduler import SchedulerFactory, Scheduler

class SystemUpgradeScheduler(Scheduler):
    def __init__(self, client, system, date):
        self.__client = client
        self.__system = system
        self.__date = date
        self.__logger = logging.getLogger(__name__)

    def schedule(self):
        action_ids = []
        try:
            advanced_options = {"kernel_options": self.__system.kernel_options,
                                "post_kernel_options": self.__system.post_kernel_options}
            proxy = self.__system.get_proxy_id(self.__client)
            if proxy != -1:
                action_ids.append(self.__client.system.provisionSystem(self.__system.get_id(self.__client), proxy,
                                                                   self.__system.target, self.__date, advanced_options))
            else:
                action_ids.append(self.__client.system.provisionSystem(self.__system.get_id(self.__client),
                                                                   self.__system.target, self.__date, advanced_options))
            self.__logger.debug(f"Successfully scheduled system upgrade with action ID {action_ids} " +
                                f"for system {self.__system.name}")
        except Fault as err:
            self.__logger.error(f"Failed to schedule upgrade for system {self.__system.name}")
            self.__logger.error("Fault code: %d" % err.faultCode)
            self.__logger.error("Fault string: %s" % err.faultString)
            return None
        except ValueError as err:
            self.__logger.error(err)
            return None
        return action_ids


class SystemUpgradeSchedulerFactory(SchedulerFactory):
    def get_scheduler(self, client, system, schedule_date, args):
        scheduler = SystemUpgradeScheduler(client, system, schedule_date)
        return scheduler
