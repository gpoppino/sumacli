import logging
from xmlrpc.client import Fault

from suma.scheduler import SchedulerFactory, Scheduler


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


class ProductMigrationSchedulerFactory(SchedulerFactory):
    def get_scheduler(self, client, system, schedule_date, args):
        if system.migration_target is None:
            raise ValueError(f"System {system.name} has no migration target")
        scheduler = SystemProductMigrationScheduler(client, system, schedule_date)
        return scheduler
