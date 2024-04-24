#!/usr/bin/python3
import importlib.resources
import os.path
from datetime import datetime, timedelta
from sumacli import utils, validator, client_systems, patching, migration, upgrade, client as suma_xmlrpc_client
import logging.config
import logging
import argparse
import sys


def perform_scheduling(scheduler, system, date):
    logger = logging.getLogger(__name__)
    action_ids = scheduler.schedule()
    if action_ids:
        if isinstance(scheduler, migration.SystemProductMigrationScheduler):
            logger.info(f"System {system.name} scheduled successfully for product migration at {date}")
        elif isinstance(scheduler, patching.SystemPatchingScheduler):
            advisory_types_description = [t.value + " " for t in scheduler.get_advisory_types()]
            logger.info(f"System {system.name} scheduled successfully for "
                        f"{advisory_types_description} patching at {date}")
        elif isinstance(scheduler, utils.SystemPackageRefreshScheduler):
            logger.info(f"System {system.name} scheduled successfully for a package refresh at {date}")
        elif isinstance(scheduler, upgrade.SystemUpgradeScheduler):
            logger.info(f"System {system.name} scheduled successfully for upgrade at {date}")
    else:
        if isinstance(scheduler, migration.SystemProductMigrationScheduler):
            logger.error(f"System {system.name} failed to be scheduled for product migration at {date}")
        elif isinstance(scheduler, patching.SystemPatchingScheduler):
            advisory_types_description = [t.value + " " for t in scheduler.get_advisory_types()]
            logger.error(f"System {system.name} failed to be scheduled for "
                         f"{advisory_types_description} patching at {date}")
        elif isinstance(scheduler, utils.SystemPackageRefreshScheduler):
            logger.error(f"System {system.name} failed to be scheduled for a package refresh at {date}")
        elif isinstance(scheduler, upgrade.SystemUpgradeScheduler):
            logger.error(f"System {system.name} failed to be scheduled for upgrade at {date}")
    return action_ids


# Exit codes:
# 0  success. every system has been scheduled for patching
# 2  total failure. improper command line options passed
# 64 partial failure. partial systems scheduling has failed
# 65 total failure. all systems scheduling has failed
# 66 total failure. all systems scheduling has failed due to improper input

def perform_suma_scheduling(factory, args):
    logger = logging.getLogger(__name__)

    client = suma_xmlrpc_client.SumaClient(args.config)
    client.login()
    systems = client_systems.SystemListParser(client, args.filename).parse()
    if systems == {}:
        logger.error("No systems found in file: " + args.filename)
        logger.error("The format of the file is: systemName,year-month-day hour:minute:second")
        logger.error("Example: sumacli-client,2021-11-06 10:00:00")
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

    if failed_systems > 0 and success_systems > 0:
        exit_code = 64
    elif failed_systems > 0 and success_systems == 0:
        exit_code = 65
    elif failed_systems == 0 and success_systems > 0:
        exit_code = 0
    sys.exit(exit_code)


def perform_patching(args):
    factory = patching.PatchingSchedulerFactory()
    perform_suma_scheduling(factory, args)


def perform_product_migration(args):
    factory = migration.ProductMigrationSchedulerFactory()
    perform_suma_scheduling(factory, args)


def perform_system_upgrade(args):
    factory = upgrade.SystemUpgradeSchedulerFactory()
    perform_suma_scheduling(factory, args)


def perform_validation(args):
    action_id_file_manager = validator.ActionIDFileManager(args.action_ids_filename)

    client = suma_xmlrpc_client.SumaClient()
    client.login()

    action_id_validator = validator.ActionIDValidator(client, action_id_file_manager)
    action_id_validator.validate()


def perform_utils_tasks(args):
    factory = utils.UtilsSchedulerFactory()
    perform_suma_scheduling(factory, args)


def perform_user_tasks(args):
    client = suma_xmlrpc_client.SumaClient(args.config)

    if args.login:
        client.login()
    elif args.logout:
        client.logout()


def main():
    logging_file = "/etc/sumacli/logging.conf"
    if not os.path.isfile(logging_file):
        logging_file = importlib.resources.files("sumacli").joinpath("conf/logging.conf")
    logging.config.fileConfig(logging_file)
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Config filename.", required=False)
    subparsers = parser.add_subparsers(required=True, dest="cmd")

    patching_parser = subparsers.add_parser("patch", help="Patches systems.")
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
    migration_parser.add_argument("-d", "--dry-run", help="Dry run mode. Do not perform the migration.",
                                  action="store_true")
    migration_parser.add_argument("-l", "--list-migration-targets", help="List migration targets for each system.",
                                  action="store_true")
    migration_parser.set_defaults(func=perform_product_migration)

    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrades systems to a new product version.")
    upgrade_parser.add_argument("filename", help="Filename of systems and their schedules for upgrade.")
    upgrade_parser.add_argument("-f", "--save-action-ids-file", help="File name to save action IDs of scheduled jobs.")
    upgrade_parser.set_defaults(func=perform_system_upgrade)

    validator_parser = subparsers.add_parser("validate", help="Validates results from actions file.")
    validator_parser.add_argument("action_ids_filename", help="Validate results of actions specified in file.")
    validator_parser.set_defaults(func=perform_validation)

    utils_parser = subparsers.add_parser("utils", help="Some utility commands to run on systems.")
    utils_parser.add_argument("filename", help="Filename of systems and their schedules for utility commands.")
    utils_parser.add_argument("-r", "--package-refresh", help="Schedules a package list refresh for a system.",
                              action="store_true", required=True)
    utils_parser.add_argument("-f", "--save-action-ids-file", help="File name to save action IDs of scheduled jobs.")
    utils_parser.set_defaults(func=perform_utils_tasks)

    user_parser = subparsers.add_parser("user", help="User management commands.")
    user_parser.add_argument("-i", "--login", help="Logs in to the server.", action="store_true")
    user_parser.add_argument("-o", "--logout", help="Logs out the user from the server.", action="store_true")
    user_parser.set_defaults(func=perform_user_tasks)

    args = parser.parse_args()
    if args.cmd == 'patch':
        if args.policy is None and args.all_patches is False and args.bugfix is False and \
                args.enhancement is False and args.security is False:
            patching_parser.print_usage()
            logger.error("The 'patch' subcommand needs at least one patching option")
            sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
