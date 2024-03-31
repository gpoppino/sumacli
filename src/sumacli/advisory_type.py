from enum import Enum


class AdvisoryType(Enum):
    SECURITY = 'Security Advisory'
    BUGFIX = 'Bug Fix Advisory'
    PRODUCT_ENHANCEMENT = 'Product Enhancement Advisory'
    # This is not a SUMA advisory type, but a flag to mark that we will patch the system
    # with all patches available for it
    ALL = 'All Relevant Errata'
