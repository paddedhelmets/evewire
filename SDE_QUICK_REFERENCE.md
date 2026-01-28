# EVE SDE Quick Reference Guide

## Database Location
- **Path**: `/home/genie/data/evewire/evewire_app.sqlite3`
- **Tables**: 53 SDE tables with `evesde_` prefix
- **Total Items**: 51,134 types

## Category IDs
| ID | Category | Published Types |
|----|----------|-----------------|
| 6 | Ship | 412 |
| 7 | Module | 3,941 |
| 8 | Charge | 1,015 |
| 18 | Drone | 133 |
| 87 | Fighter | 94 |

## Ship Group IDs (Key Groups)
| ID | Group | Types |
|----|-------|-------|
| 25 | Frigate | 51 |
| 26 | Cruiser | 38 |
| 27 | Battleship | 35 |
| 28 | Hauler | 18 |
| 30 | Titan | 8 |
| 420 | Destroyer | 20 |
| 419 | Combat Battlecruiser | 21 |
| 485 | Dreadnought | 13 |
| 547 | Carrier | 4 |
| 659 | Supercarrier | 6 |
| 831 | Interceptor | 10 |
| 832 | Logistics | 7 |
| 898 | Black Ops | 6 |

## Module Group IDs (Key Groups)
| ID | Group | Function |
|----|-------|----------|
| 53 | Energy Weapon | Lasers (EM/Thermal) |
| 74 | Hybrid Weapon | Rails/Blasters (Kin/Therm) |
| 55 | Projectile Weapon | Arty/Autos (Exp/Kin) |
| 255 | Missile Launcher | All damage types |
| 40 | Shield Booster | Active shield tank |
| 77 | Shield Hardener | Shield resistances |
| 62 | Armor Repair Unit | Active armor tank |
| 46 | Propulsion Module | AB/MWD |
| 52 | Warp Scrambler | Prevent warp |
| 65 | Stasis Web | Slow target |
| 71 | Energy Neutralizer | Drain capacitor |

## Meta Groups
| ID | Name | Items |
|----|------|-------|
| 1 | Tech I | 2,626 |
| 2 | Tech II | 2,198 |
| 3 | Storyline | 440 |
| 4 | Faction | 2,838 |
| 5 | Officer | 612 |
| 6 | Deadspace | 362 |

## Key Ship Attributes
**Fitting:**
- `powerOutput` - Power Grid
- `cpu` - CPU
- `upgradeCapacity` - Calibration

**Slots:**
- `hiSlots` - High slots
- `medSlots` - Medium slots
- `loSlots` - Low slots
- `rigSlots` - Rig slots

**Hardpoints:**
- `turretSlotsLeft` - Turrets
- `launcherSlotsLeft` - Missile launchers

**Drones:**
- `droneCapacity` - Drone bay (m³)
- `droneBandwidth` - Bandwidth (MB/s)

**Tank:**
- `shieldCapacity` - Shield HP
- `armorHP` - Armor HP
- `hp` - Structure HP

**Mobility:**
- `maxVelocity` - Speed (m/s)
- `agility` - Align time
- `warpSpeedMultiplier` - Warp speed

## Damage Types
| Type | Best Against | Worst Against |
|------|--------------|---------------|
| EM | Shield (40%) | Armor (60%) |
| Thermal | Balanced | Balanced |
| Kinetic | Armor (20%) | Shield (40%) |
| Explosive | Armor (10%) | Shield (50%) |

## Racial Weapon Preferences
| Race | Weapon | Damage Types |
|------|--------|--------------|
| Amarr | Lasers | EM/Thermal |
| Caldari | Hybrids/Missiles | Kinetic/Thermal |
| Gallente | Hybrids/Drones | Thermal/Kinetic |
| Minmatar | Projectiles | Explosive/Kinetic |

## Django Query Examples
```python
from core.sde.models import InvTypes, InvGroups, InvCategories

# Get all ships
ship_cat = InvCategories.objects.get(category_id=6)
ships = InvTypes.objects.filter(group__category=ship_cat, published=True)

# Get frigates
frigate_group = InvGroups.objects.get(group_id=25)
frigates = InvTypes.objects.filter(group=frigate_group, published=True)

# Get hybrid weapons
hybrid_group = InvGroups.objects.get(group_id=74)
weapons = InvTypes.objects.filter(group=hybrid_group, published=True)

# Get meta variants
base = InvTypes.objects.get(name='1MN Afterburner I')
variants = InvMetaTypes.objects.filter(parent_type=base)
```

## SDE Import
```bash
python manage.py import_sde_browser --help
python manage.py import_sde_browser --list
python manage.py import_sde_browser --tables=invTypes,invGroups
```

## Report Files
- **Full Report**: `/home/genie/gt/evewire/crew/delve/SDE_SHIPS_AND_COMBAT.md`
- **Quick Reference**: `/home/genie/gt/evewire/crew/delve/SDE_QUICK_REFERENCE.md`
