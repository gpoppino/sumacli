import logging
from xmlrpc.client import Fault

from sumacli.scheduler import SchedulerFactory, Scheduler
from sumacli.config_mgr import ConfigManager


class SystemUpgradeScheduler(Scheduler):
    def __init__(self, client, system, date):
        self.__client = client
        self.__system = system
        self.__date = date
        self.__logger = logging.getLogger(__name__)
        self.__kstree_label = None
        self.__kstree_data = None
        self.__config_manager = ConfigManager()

    def __get_org_id(self):
        profile_variables = self.__client.kickstart.profile.getVariables(self.__system.target)
        if 'org' in profile_variables.keys():
            return profile_variables['org']

        orgs = self.__client.org.listOrgs()
        for org in orgs:
            users = self.__client.org.listUsers(org['id'])
            if self.__config_manager.manager_login in [user['login'] for user in users]:
                return org['id']
        return orgs[0]['id']

    def __get_kickstart_tree(self):
        if self.__kstree_label is not None and self.__kstree_data is not None:
            return self.__kstree_label, self.__kstree_data
        self.__kstree_label = self.__client.kickstart.profile.getKickstartTree(self.__system.target)
        self.__kstree_data = self.__client.kickstart.tree.getDetails(self.__kstree_label)
        return self.__kstree_label, self.__kstree_data

    def __build_pillar_data(self):
        kstree_label, kstree_data = self.__get_kickstart_tree()
        org_id = self.__get_org_id()
        manager_fqdn = self.__config_manager.manager_fqdn
        autoyast = f"http://{manager_fqdn}/cblr/svc/op/autoinstall/system/{self.__system.name}:{org_id}"
        kopts = f"autoyast={autoyast} " + kstree_data['kernel_options'] + " autoupgrade=1"
        if self.__system.kopts is not None:
            kopts = kopts + " " + self.__system.kopts
        pillar_data = {"kernel": f"{org_id}/" + kstree_label + "/linux",
                       "initrd": f"{org_id}/" + kstree_label + "/initrd",
                       "uyuni-reinstall-name": "suse_patching_upgrade",
                       "kopts": kopts}
        return pillar_data

    def __set_system_record_variables(self):
        kstree_label, kstree_data = self.__get_kickstart_tree()
        reactivation_key = self.__client.system.obtainReactivationKey(self.__system.get_id(self.__client))
        variables = {"ks_distro": kstree_data['install_type']['label'],
                     "redhat_management_server": self.__client.manager_fqdn,
                     "redhat_management_key": reactivation_key}
        self.__client.system.setVariables(self.__system.get_id(self.__client), False, variables)

    def schedule(self):
        action_ids = None
        try:
            if self.__client.system.createSystemRecord(self.__system.get_id(self.__client),
                                                       self.__system.target) == 1:
                self.__logger.debug(f"Successfully created system record for system {self.__system.name}")

                self.__set_system_record_variables()

                self.__client.system.setPillar(self.__system.get_id(self.__client), "suse_patching_upgrade",
                                               self.__build_pillar_data())
                action_ids = [self.__client.system.scheduleApplyStates(self.__system.get_id(self.__client),
                                                                       ["bootloader.autoinstall"], self.__date, False)]
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
