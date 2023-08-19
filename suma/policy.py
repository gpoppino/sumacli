import csv
import logging
from pprint import pprint
from .patching import AdvisoryType


def get_advisory_types_for_system(client, system, policy):
    logger = logging.getLogger(__name__)
    for product in client.system.getInstalledProducts(system.get_id(client)):
        if product['isBaseProduct']:
            if product['friendlyName'] in policy:
                return policy[product['friendlyName']]
            else:
                logger.warning(f"Product '{product['friendlyName']}' not found in policy file for system {system.name}")
    return []


class ProductPatchingPolicyParser:

    def __init__(self, filename):
        self.__filename = filename

    def parse(self):
        policy = {}
        with open(self.__filename, mode="r") as file:
            csv_file = csv.reader(file)
            for product in csv_file:
                policy[product[0]] = []
                advisory_types = product[1].split()
                for advisory in advisory_types:
                    if advisory.lower() == 'all':
                        policy[product[0]].append(AdvisoryType.ALL)
                        break
                    if advisory.lower() == 'security':
                        policy[product[0]].append(AdvisoryType.SECURITY)
                        continue
                    if advisory.lower() == 'bugfix':
                        policy[product[0]].append(AdvisoryType.BUGFIX)
                        continue
                    if advisory.lower() == 'product_enhancement':
                        policy[product[0]].append(AdvisoryType.PRODUCT_ENHANCEMENT)
        return policy


if __name__ == "__main__":
    parser = ProductPatchingPolicyParser("../conf/product_patching_policy.conf")
    patching_policy = parser.parse()
    pprint(patching_policy)
