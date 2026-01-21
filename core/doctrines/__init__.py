"""
Doctrine and fleet fitting management.

Provides models and services for:
- Storing doctrine fit specifications (from zkillboard clustering)
- Validating assets against doctrine requirements
- Generating shopping lists for missing items
- Calculating location capacity for doctrine ships
"""

default_app_config = 'core.doctrines.apps.DoctrinesConfig'
