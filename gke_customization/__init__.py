
__version__ = '0.0.1'

import erpnext.accounts.party as party_module
from gke_customization.overrides.validate_party import  gke_custom_validate_account_party_type

party_module.validate_account_party_type =  gke_custom_validate_account_party_type
