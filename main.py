from datetime import datetime, timedelta
from susepatching import AdvisoryType
import logging.config
import susepatching
import validator
import logging
import argparse
import sys


def perform_scheduling(scheduler, system, date):
    logger = logging.getLogger(__name__)
    action_ids = scheduler.schedule()
    if action_ids is not None:
        if isinstance(scheduler, susepatching.SystemProductMigrationScheduler):
            logger.info(f"System {system.name} scheduled successfully for product migration at {date}")
        elif isinstance(scheduler, susepatching.SystemPatchingScheduler):
            logger.info(f"System {system.name} scheduled successfully for "
                        f"{scheduler.get_advisory_type().value} patching at {date}")
    else:
        if isinstance(scheduler, susepatching.SystemProductMigrationScheduler):
            logger.error(f"System {system.name} failed to be scheduled for product migration at {date}")
        elif isinstance(scheduler, susepatching.SystemPatchingScheduler):
            logger.error(f"System {system.name} failed to be scheduled for "
                         f"{scheduler.get_advisory_type().value} patching at {date}")
    return action_ids


# Exit codes:
# 0  success. every system has been scheduled for patching
# 2  total failure. improper command line options passed
# 64 partial failure. partial systems scheduling has failed
# 65 total failure. all systems scheduling has failed
# 66 total failure. all systems scheduling has failed due to improper input

def perform_patching(args):
    logger = logging.getLogger(__name__)

    client = susepatching.SumaClient()
    client.login()
    systems = susepatching.SystemListParser(client, args.patching_filename).parse()
    if systems == {}:
        logger.error("No systems found in file: " + args.patching_filename)
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
            if system.migration_target:
                scheduler = susepatching.SystemProductMigrationScheduler(client, system, schedule_date)
            else:
                advisory_type = AdvisoryType.ALL if args.all_patches else AdvisoryType.SECURITY
                scheduler = susepatching.SystemPatchingScheduler(client, system, schedule_date, advisory_type,
                                                                 args.reboot, args.no_reboot, "patching")

            action_ids = perform_scheduling(scheduler, system, date)
            if action_ids is not None:
                action_id_file_manager.append(action_ids)
                success_systems += 1
            else:
                failed_systems += 1
    action_id_file_manager.save()
    logger.info(f"Action IDs file saved: {action_id_file_manager.get_filename()}")
    client.logout()

    if failed_systems > 0 and success_systems > 0:
        exit_code = 64
    elif failed_systems > 0 and success_systems == 0:
        exit_code = 65
    elif failed_systems == 0 and success_systems > 0:
        exit_code = 0
    sys.exit(exit_code)


def perform_validation(args):
    action_id_file_manager = validator.ActionIDFileManager(args.actions_file)

    client = susepatching.SumaClient()
    client.login()

    action_id_validator = validator.ActionIDValidator(client, action_id_file_manager)
    action_id_validator.validate()

    client.logout()


def main():
    logging.config.fileConfig('logging.conf')

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(required=True)

    patching_parser = subparsers.add_parser("patch", help="Patches or migrates systems.")
    patching_parser.add_argument("patching_filename",
                                 help="Filename of systems and their schedules for patching or migration.")
    patching_parser.add_argument(
        "-a", "--all-patches", help="Apply all available patches to each system.", action="store_true")
    patching_parser.add_argument("-s", "--save-action-ids-file", help="File name to save action IDs of scheduled jobs.")
    group = patching_parser.add_mutually_exclusive_group()
    group.add_argument(
        "-r", "--reboot", help="Add a system reboot to each action chain for each system.", action="store_true")
    group.add_argument(
        "-n", "--no-reboot",
        help="Do not add a system reboot to the action chain of every system even if suggested by a patch.",
        action="store_true")
    patching_parser.set_defaults(func=perform_patching)

    validator_parser = subparsers.add_parser("validate", help="Validates results from actions file.")
    validator_parser.add_argument("-f", "--actions-file", required=True,
                                  help="Validate results of actions specified in file.")
    validator_parser.set_defaults(func=perform_validation)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
