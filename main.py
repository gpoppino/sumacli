from datetime import datetime, timedelta
import logging.config
import susepatching
import logging
import argparse
import sys


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
        "-a", "--all-patches", help="Apply all available patches to each system.", action="store_true")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-r", "--reboot", help="Add a system reboot to each action chain for each system.", action="store_true")
    group.add_argument(
        "-n", "--no-reboot",
        help="Do not add a system reboot to the action chain of every system even if suggested by a patch.",
        action="store_true")
    args = parser.parse_args()

    logging.config.fileConfig('logging.conf')
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
    for date in systems.keys():
        schedule_date = datetime.now() if date == "now" else datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        delta = timedelta(seconds=5)
        if schedule_date + delta < datetime.now():
            system_names = [s.name for s in systems[date]]
            logger.warning(f"Date {date} is in the past! System(s) skipped: {system_names}")
            continue
        for system in systems[date]:
            if system.migration_target:
                productMigrationScheduler = susepatching.SystemProductMigrationScheduler(client, system, schedule_date)
                if productMigrationScheduler.schedule():
                    logger.info(f"System {system.name} scheduled successfully for product migration at {date}")
                    success_systems += 1
                else:
                    logger.error(f"System {system.name} failed to be scheduled for product migration at {date}")
                    failed_systems += 1
            else:
                patchingScheduler = susepatching.SystemPatchingScheduler(
                    client, system, schedule_date,
                    susepatching.AdvisoryType.ALL if args.all_patches else susepatching.AdvisoryType.SECURITY,
                    args.reboot, args.no_reboot, "patching")
                if patchingScheduler.schedule():
                    logger.info(f"System {system.name} scheduled successfully for "
                                f"{patchingScheduler.get_advisory_type().value} patching at {date}")
                    success_systems += 1
                else:
                    logger.error(f"System {system.name} failed to be scheduled for "
                                 f"{patchingScheduler.get_advisory_type().value} patching at {date}")
                    failed_systems += 1
    client.logout()

    if failed_systems > 0 and success_systems > 0:
        exit_code = 64
    elif failed_systems > 0 and success_systems == 0:
        exit_code = 65
    elif failed_systems == 0 and success_systems > 0:
        exit_code = 0
    sys.exit(exit_code)
