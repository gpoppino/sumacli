from datetime import datetime, timedelta

from policy import ProductPatchingPolicyParser, get_advisory_types_for_system
from susepatching import AdvisoryType
import logging.config
import susepatching
import validator
import logging
import argparse
import sys


class SchedulerFactory:

    def get_scheduler(self, client, system, schedule_date, args):
        pass


class PatchingSchedulerFactory(SchedulerFactory):
    def get_scheduler(self, client, system, schedule_date, args):
        advisory_types = []
        if args.policy:
            policy_parser = ProductPatchingPolicyParser(args.policy)
            policy = policy_parser.parse()
            advisory_types = get_advisory_types_for_system(client, system.get_id(client), policy)
        else:
            if args.security:
                advisory_types.append(AdvisoryType.SECURITY)
            if args.bugfix:
                advisory_types.append(AdvisoryType.BUGFIX)
            if args.enhancement:
                advisory_types.append(AdvisoryType.PRODUCT_ENHANCEMENT)
            if args.all_patches:
                advisory_types = [AdvisoryType.ALL]

        scheduler = susepatching.SystemPatchingScheduler(client, system, schedule_date, advisory_types, args.reboot,
                                                         args.no_reboot, "patching")
        return scheduler


class ProductMigrationSchedulerFactory(SchedulerFactory):
    def get_scheduler(self, client, system, schedule_date, args):
        if system.migration_target is None:
            raise ValueError(f"System {system.name} has no migration target")
        scheduler = susepatching.SystemProductMigrationScheduler(client, system, schedule_date)
        return scheduler


def perform_scheduling(scheduler, system, date):
    logger = logging.getLogger(__name__)
    action_ids = scheduler.schedule()
    if action_ids is not None:
        if isinstance(scheduler, susepatching.SystemProductMigrationScheduler):
            logger.info(f"System {system.name} scheduled successfully for product migration at {date}")
        elif isinstance(scheduler, susepatching.SystemPatchingScheduler):
            advisory_types_description = [t.value + " " for t in scheduler.get_advisory_types()]
            logger.info(f"System {system.name} scheduled successfully for "
                        f"{advisory_types_description} patching at {date}")
    else:
        if isinstance(scheduler, susepatching.SystemProductMigrationScheduler):
            logger.error(f"System {system.name} failed to be scheduled for product migration at {date}")
        elif isinstance(scheduler, susepatching.SystemPatchingScheduler):
            advisory_types_description = [t.value + " " for t in scheduler.get_advisory_types()]
            logger.error(f"System {system.name} failed to be scheduled for "
                         f"{advisory_types_description} patching at {date}")
    return action_ids


# Exit codes:
# 0  success. every system has been scheduled for patching
# 2  total failure. improper command line options passed
# 64 partial failure. partial systems scheduling has failed
# 65 total failure. all systems scheduling has failed
# 66 total failure. all systems scheduling has failed due to improper input

def perform_suma_scheduling(factory, args):
    logger = logging.getLogger(__name__)

    client = susepatching.SumaClient()
    client.login()
    systems = susepatching.SystemListParser(client, args.filename).parse()
    if systems == {}:
        logger.error("No systems found in file: " + args.filename)
        logger.error("The format of the file is: systemName,year-month-day hour:minute:second")
        logger.error("Example: suma-client,2021-11-06 10:00:00")
        client.logout()
        sys.exit(66)

    exit_code = 0
    failed_systems = 0
    success_systems = 0
    action_id_file_manager = validator.ActionIDFileManager(args.save_action_ids_file)
    for date in systems.keys():
        schedule_date = datetime.now() if date == "now" else datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        delta = timedelta(seconds=5)
        if schedule_date + delta < datetime.now():
            system_names = [s.name for s in systems[date]]
            logger.warning(f"Date {date} is in the past! System(s) skipped: {system_names}")
            continue
        for system in systems[date]:
            try:
                scheduler = factory.get_scheduler(client, system, schedule_date, args)
            except ValueError as e:
                logger.error(f"System {system.name} failed to be scheduled at {date}: {e}")
                failed_systems += 1
                continue
            action_ids = perform_scheduling(scheduler, system, date)
            if action_ids is not None:
                action_id_file_manager.append(action_ids)
                success_systems += 1
            else:
                failed_systems += 1
    if action_id_file_manager.save():
        logger.info(f"Action IDs file saved: {action_id_file_manager.get_filename()}")
    client.logout()

    if failed_systems > 0 and success_systems > 0:
        exit_code = 64
    elif failed_systems > 0 and success_systems == 0:
        exit_code = 65
    elif failed_systems == 0 and success_systems > 0:
        exit_code = 0
    sys.exit(exit_code)


def perform_patching(args):
    factory = PatchingSchedulerFactory()
    perform_suma_scheduling(factory, args)


def perform_product_migration(args):
    factory = ProductMigrationSchedulerFactory()
    perform_suma_scheduling(factory, args)


def perform_validation(args):
    action_id_file_manager = validator.ActionIDFileManager(args.action_ids_filename)

    client = susepatching.SumaClient()
    client.login()

    action_id_validator = validator.ActionIDValidator(client, action_id_file_manager)
    action_id_validator.validate()

    client.logout()


def main():
    logging.config.fileConfig('logging.conf')

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(required=True, dest="cmd")

    patching_parser = subparsers.add_parser("patch", help="Patches or migrates systems.")
    patching_parser.add_argument("filename",
                                 help="Filename of systems and their schedules for patching.")
    patching_parser.add_argument("-p", "--policy", help="Products patching policy filename.")
    patching_parser.add_argument(
        "-a", "--all-patches", help="Apply all available patches to each system.", action="store_true")
    patching_parser.add_argument("-b", "--bugfix", help="Apply bug fix patches to each system.",
                                 action="store_true")
    patching_parser.add_argument("-e", "--enhancement", help="Apply product enhancement patches to each system.",
                                 action="store_true")
    patching_parser.add_argument("-s", "--security", help="Apply security patches to each system.",
                                 action="store_true")
    patching_parser.add_argument("-f", "--save-action-ids-file", help="File name to save action IDs of scheduled jobs.")
    group = patching_parser.add_mutually_exclusive_group()
    group.add_argument(
        "-r", "--reboot", help="Add a system reboot to each action chain for each system.", action="store_true")
    group.add_argument(
        "-n", "--no-reboot",
        help="Do not add a system reboot to the action chain of every system even if suggested by a patch.",
        action="store_true")
    patching_parser.set_defaults(func=perform_patching)

    migration_parser = subparsers.add_parser("migrate", help="Migrates systems to a new Service Pack.")
    migration_parser.add_argument("filename", help="Filename of systems and their schedules for migration.")
    migration_parser.add_argument("-f", "--save-action-ids-file",
                                  help="File name to save action IDs of scheduled jobs.")
    migration_parser.set_defaults(func=perform_product_migration)

    validator_parser = subparsers.add_parser("validate", help="Validates results from actions file.")
    validator_parser.add_argument("action_ids_filename", help="Validate results of actions specified in file.")
    validator_parser.set_defaults(func=perform_validation)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
