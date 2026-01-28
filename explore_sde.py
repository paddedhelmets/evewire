#!/usr/bin/env python3
"""
Explore EVE Online SDE to understand structures, starbases, and deployables.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, '/home/genie/gt/evewire/crew/delve')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'evewire.settings')
django.setup()

from core.sde.models import (
    InvTypes, InvGroups, InvCategories, InvControlTowerResources,
    DgmTypeAttributes, StaStations, DgmAttributeTypes
)
from django.db.models import Q

def explore_starbases():
    """Explore starbase (POS) types"""
    print("\n" + "="*80)
    print("STARBASE (POS) TYPES")
    print("="*80)

    starbase_cat = InvCategories.objects.get(category_id=23)
    groups = InvGroups.objects.filter(category=starbase_cat, published=True)

    for group in groups:
        types = InvTypes.objects.filter(group=group, published=True).order_by('name')
        print(f"\n{group.group_name} ({types.count()} types):")
        for t in types:
            print(f"  - {t.name} (ID: {t.type_id})")

def explore_pos_fuel():
    """Explore POS fuel requirements"""
    print("\n" + "="*80)
    print("POS FUEL REQUIREMENTS")
    print("="*80)

    # Get Control Tower group
    ct_group = InvGroups.objects.get(group_id=365)
    towers = InvTypes.objects.filter(group=ct_group, published=True).order_by('name')

    # Sample a few towers
    for tower in towers[:12]:  # Get one of each race/size combination
        print(f"\n{tower.name} (ID: {tower.type_id}):")

        resources = InvControlTowerResources.objects.filter(
            control_tower_type_id=tower.type_id
        )

        for res in resources:
            # Get resource type info manually
            try:
                resource_type = InvTypes.objects.get(type_id=res.resource_type_id)
                purpose_desc = {
                    1: "Consumption",
                    2: "CPU",
                    3: "Power",
                    4: "Reinforce"
                }.get(res.purpose, f"Purpose {res.purpose}")

                print(f"  - {resource_type.name}: {res.quantity} [{purpose_desc}]")
            except InvTypes.DoesNotExist:
                print(f"  - Unknown Resource ID {res.resource_type_id}: {res.quantity}")

def explore_structures():
    """Explore upwell structures"""
    print("\n" + "="*80)
    print("UPWELL STRUCTURES")
    print("="*80)

    structure_cat = InvCategories.objects.get(category_id=65)
    groups = InvGroups.objects.filter(category=structure_cat, published=True)

    for group in groups:
        types = InvTypes.objects.filter(group=group, published=True).order_by('name')
        print(f"\n{group.group_name} ({types.count()} types):")
        for t in types:
            print(f"  - {t.name} (ID: {t.type_id})")

def explore_structure_modules():
    """Explore structure modules (sample)"""
    print("\n" + "="*80)
    print("STRUCTURE MODULES (Sample)")
    print("="*80)

    module_cat = InvCategories.objects.get(category_id=66)
    groups = InvGroups.objects.filter(category=module_cat, published=True)

    for group in groups:
        types = InvTypes.objects.filter(group=group, published=True).order_by('name')
        print(f"\n{group.group_name} ({types.count()} types):")
        for t in types[:3]:  # Show first 3
            print(f"  - {t.name} (ID: {t.type_id})")
        if types.count() > 3:
            print(f"  ... and {types.count() - 3} more")

def explore_reactions():
    """Explore reaction types"""
    print("\n" + "="*80)
    print("REACTIONS")
    print("="*80)

    reaction_cat = InvCategories.objects.get(category_id=24)
    groups = InvGroups.objects.filter(category=reaction_cat, published=True)

    for group in groups:
        types = InvTypes.objects.filter(group=group, published=True).order_by('name')
        print(f"\n{group.group_name} ({types.count()} types):")
        for t in types[:10]:
            print(f"  - {t.name} (ID: {t.type_id})")

def explore_sovereignty():
    """Explore sovereignty structures"""
    print("\n" + "="*80)
    print("SOVEREIGNTY STRUCTURES")
    print("="*80)

    sov_cat = InvCategories.objects.get(category_id=40)
    groups = InvGroups.objects.filter(category=sov_cat, published=True)

    for group in groups:
        types = InvTypes.objects.filter(group=group, published=True).order_by('name')
        print(f"\n{group.group_name} ({types.count()} types):")
        for t in types:
            print(f"  - {t.name} (ID: {t.type_id})")

def explore_structure_attributes():
    """Explore key structure attributes"""
    print("\n" + "="*80)
    print("STRUCTURE ATTRIBUTES")
    print("="*80)

    # Get a citadel example
    citadel_group = InvGroups.objects.get(group_id=1657)
    citadel = InvTypes.objects.filter(group=citadel_group, published=True).first()

    if citadel:
        print(f"\nExample: {citadel.name} (ID: {citadel.type_id})")
        print("\nKey Attributes:")

        # Get attributes
        attrs = DgmTypeAttributes.objects.filter(type=citadel.type_id)

        # Show interesting attributes
        interesting = ['cpuOutput', 'powerOutput', 'fuelBayCapacity', 'capacity',
                      'shieldCapacity', 'armorHP', 'hp', 'maxTargetRange']

        for attr in attrs[:50]:  # Limit to first 50
            try:
                from core.sde.models import DgmAttributeTypes
                attr_type = DgmAttributeTypes.objects.get(attribute_id=attr.attribute_id)
                attr_name = attr_type.attribute_name
                if any(i.lower() in attr_name.lower() for i in interesting):
                    value = attr.value_float if attr.value_float is not None else attr.value_int
                    print(f"  {attr_type.display_name}: {value}")
            except DgmAttributeTypes.DoesNotExist:
                pass

def explore_stations():
    """Explore NPC stations"""
    print("\n" + "="*80)
    print("NPC STATIONS")
    print("="*80)

    station_count = StaStations.objects.count()
    print(f"\nTotal NPC Stations: {station_count}")

    # Get unique station types
    station_type_ids = StaStations.objects.values_list('station_type_id', flat=True).distinct()
    station_types = InvTypes.objects.filter(type_id__in=station_type_ids)

    print(f"\nUnique Station Types: {station_types.count()}")
    print("\nSample station types:")
    for st in station_types[:15]:
        print(f"  - {st.name} (ID: {st.type_id})")

    # Sample a station
    sample_station = StaStations.objects.first()
    if sample_station:
        print(f"\nSample Station: {sample_station.station_name}")
        print(f"  System ID: {sample_station.solar_system_id}")
        print(f"  Type ID: {sample_station.station_type_id}")
        print(f"  Corporation ID: {sample_station.corporation_id}")

def explore_starbase_detail():
    """Detailed look at starbase control towers"""
    print("\n" + "="*80)
    print("STARBASE CONTROL TOWERS - DETAILED")
    print("="*80)

    ct_group = InvGroups.objects.get(group_id=365)
    towers = InvTypes.objects.filter(group=ct_group, published=True).order_by('name')

    print(f"\nTotal Control Towers: {towers.count()}")

    # Group by race
    races = {}
    for tower in towers:
        for race in ['Caldari', 'Minmatar', 'Amarr', 'Gallente']:
            if race in tower.name:
                if race not in races:
                    races[race] = []
                races[race].append(tower.name)
                break

    for race, tower_list in sorted(races.items()):
        print(f"\n{race}:")
        for tower in sorted(tower_list):
            print(f"  - {tower}")

def main():
    print("="*80)
    print("EVE ONLINE SDE STRUCTURE EXPLORATION")
    print("="*80)

    explore_starbases()
    explore_starbase_detail()
    explore_pos_fuel()
    explore_structures()
    explore_structure_modules()
    explore_reactions()
    explore_sovereignty()
    # explore_structure_attributes()  # Skipping due to model issues
    explore_stations()

    print("\n" + "="*80)
    print("EXPLORATION COMPLETE")
    print("="*80 + "\n")

if __name__ == '__main__':
    main()
