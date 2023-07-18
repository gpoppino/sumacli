import csv
from pprint import pprint

from susepatching import AdvisoryType


def get_advisory_types_for_system(client, system_id, policy):
    for product in client.system.getInstalledProducts(system_id):
        if product['isBaseProduct']:
            return policy[product['friendlyName']]
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
    parser = ProductPatchingPolicyParser("product_patching_policy.conf")
    patching_policy = parser.parse()
    pprint(patching_policy)
