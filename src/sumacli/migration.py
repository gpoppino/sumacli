import logging
from xmlrpc.client import Fault

from sumacli.scheduler import SchedulerFactory, Scheduler


class SystemProductMigrationScheduler(Scheduler):
    def __init__(self, client, system, date, args):
        self.__client = client
        self.__system = system
        self.__date = date
        self.__logger = logging.getLogger(__name__)
        self.__dry_run = args.dry_run
        self.__list_migration_targets = args.list_migration_targets

    def schedule(self):
        action_ids = []
        try:
            if self.__list_migration_targets or self.__system.kopts is not None:
                migration_targets = self.__client.system.listMigrationTargets(self.__system.get_id(self.__client))
                if self.__list_migration_targets:
                    if not migration_targets:
                        self.__logger.info(f"No migration targets found for system {self.__system.name}")
                        return None
                    self.__logger.info(f"Migration targets for system {self.__system.name}:")
                    for target in migration_targets:
                        self.__logger.info(f"  {target}")
                    return None

                if self.__system.kopts is not None:
                    migration_target_found = False
                    for target in migration_targets:
                        if target['ident'] == self.__system.kopts:
                            action_ids.append(self.__client.system.scheduleProductMigration(
                                self.__system.get_id(self.__client), self.__system.kopts, self.__system.target, [],
                                self.__dry_run, self.__date))
                            migration_target_found = True
                            break
                    if not migration_target_found:
                        self.__logger.warning(
                            f"Migration target {self.__system.kopts} not found for system {self.__system.name}")
            else:
                action_ids.append(self.__client.system.scheduleProductMigration(self.__system.get_id(self.__client),
                                                                                self.__system.target, [],
                                                                                self.__dry_run, self.__date))
            self.__logger.debug(f"Successfully scheduled product migration with action ID {action_ids}")
            if self.__dry_run:
                self.__logger.info(f"Dry run mode: no action taken for system {self.__system.name}")
        except Fault as err:
            self.__logger.error(f"Failed to schedule product migration for system {self.__system.name}")
            self.__logger.error("Fault code: %d" % err.faultCode)
            self.__logger.error("Fault string: %s" % err.faultString)
            return None
        except ValueError as err:
            self.__logger.error(err)
            return None
        return action_ids


class ProductMigrationSchedulerFactory(SchedulerFactory):
    def get_scheduler(self, client, system, schedule_date, args):
        if system.target is None:
            raise ValueError(f"System {system.name} has no migration target")
        scheduler = SystemProductMigrationScheduler(client, system, schedule_date, args)
        return scheduler
