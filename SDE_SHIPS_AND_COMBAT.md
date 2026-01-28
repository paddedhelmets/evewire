# EVE Online SDE: Ships and Combat Systems

**Report Date:** 2026-01-27
**SDE Version:** Current (via garveen/eve-sde-converter)
**Database:** `/home/genie/data/evewire/evewire_app.sqlite3`

---

## Executive Summary

This report explores the EVE Online Static Data Export (SDE) to understand how ships, modules, weapons, and combat systems work in EVE. The SDE contains **51,134 item types** across 48 categories, with detailed attributes for every ship, module, charge, drone, and fighter in the game.

### Key Statistics

| Category | Types Published |
|----------|----------------|
| Ships (Category 6) | 412 |
| Modules (Category 7) | 3,941 |
| Charges/Ammo (Category 8) | 1,015 |
| Drones (Category 18) | 133 |
| Fighters (Category 87) | 94 |
| **TOTAL** | **5,501** |

---

## 1. Ship Classes

EVE ships are organized into **46 different groups** within the Ship category. Ships progress through a clear size hierarchy:

### Size Progression (by Mass)

| Class | Example Ship | Mass (tons) | Volume (m³) |
|-------|-------------|-------------|-------------|
| Frigate | Rifter | 1,067 | 27,289 |
| Destroyer | Thrasher | 1,600 | 43,000 |
| Cruiser | Rupture | 12,200 | 96,000 |
| Battlecruiser | Hurricane | 12,800 | 216,000 |
| Battleship | Tempest | 99,500 | 450,000 |
| Dreadnought | Naglfar | 1,260,000 | 15,500,000 |
| Titan | Ragnarok | 2,200,000 | 100,000,000 |

### Ship Group Categories

#### Basic T1 Ships
- **Frigate (Group 25)** - 51 types - Small, fast, agile
- **Destroyer (Group 420)** - 20 types - Anti-frigate platforms
- **Cruiser (Group 26)** - 38 types - Mid-sized multi-role ships
- **Battlecruiser (Group 419)** - 21 types - Heavy cruisers with battleship-class weapons
- **Battleship (Group 27)** - 35 types - Largest sub-capital combat ships

#### Advanced T2 Ships
- **Assault Frigate (Group 324)** - 15 types - Heavy frigates
- **Heavy Assault Cruiser (Group 358)** - 14 types - Heavy cruisers
- **Interceptor (Group 831)** - 10 types - Fast tackle frigates
- **Covert Ops (Group 830)** - 9 types - Stealthy exploration frigates
- **Stealth Bomber (Group 834)** - 5 types - Torpedo bombers with cloaking
- **Logistics (Group 832)** - 7 types - Remote repair cruisers
- **Command Ship (Group 540)** - 8 types - Fleet boosting ships
- **Marauder (Group 900)** - 5 types - Bastion-mode battleships

#### Capital Ships
- **Carrier (Group 547)** - 4 types - Fighter and drone deployment platforms
- **Supercarrier (Group 659)** - 6 types - Super-capital fighter platforms
- **Dreadnought (Group 485)** - 13 types - Siege-mode capital ships
- **Titan (Group 30)** - 8 types - Super-capital doomsday platforms
- **Force Auxiliary (Group 1538)** - 6 types - Capital logistics

#### Industrial Ships
- **Hauler (Group 28)** - 18 types - Basic cargo transport
- **Mining Barge (Group 463)** - 3 types - Mining platforms
- **Exhumer (Group 543)** - 3 types - Advanced mining ships
- **Freighter (Group 513)** - 6 types - Large cargo transport
- **Jump Freighter (Group 902)** - 4 types - Capital cargo transport
- **Capital Industrial Ship (Group 883)** - 1 type - Industrial capital

#### Specialized Ships
- **Interdictor (Group 541)** - 4 types - Interdiction sphere launchers
- **Heavy Interdiction Cruiser (Group 894)** - 6 types - Infinite-point warp scramblers
- **Electronic Attack Ship (Group 893)** - 5 types - EWAR frigates
- **Force Recon Ship (Group 833)** - 10 types - Cloaky EWAR cruisers
- **Combat Recon Ship (Group 906)** - 4 types - EWAR cruisers
- **Black Ops (Group 898)** - 6 types - Covert battleships
- **Strategic Cruiser (Group 963)** - 4 types - Modular T3 cruisers
- **Tactical Destroyer (Group 1305)** - 5 types - Mode-switching destroyers
- **Logistics Frigate (Group 1527)** - 4 types - Frigate logistics
- **Command Destroyer (Group 1534)** - 6 types - Micro jump field generators

---

## 2. Module Categories

Modules are organized into **158 groups** within the Module category (Category 7), totaling **3,941 published types**.

### Module Functions

#### Weapon Systems (606 types)
| Module Type | Group ID | Types | Description |
|-------------|----------|-------|-------------|
| Energy Weapons | 53 | 216 | Laser weapons (EM/Thermal damage) |
| Hybrid Weapons | 74 | 223 | Railguns and Blasters (Kinetic/Thermal) |
| Projectile Weapons | 55 | 167 | Artillery and Autocannons (Explosive/Kinetic) |
| Missile Launchers | Various | 148 | All damage types, various sizes |

#### Shield Tanking (275 types)
| Module Type | Group ID | Types | Function |
|-------------|----------|-------|----------|
| Shield Booster | 40 | 94 | Active shield regeneration |
| Shield Hardener | 77 | 103 | Resistance modules (specific damage types) |
| Shield Extender | 38 | 36 | Passive shield HP increase |
| Remote Shield Booster | 41 | 42 | Remote shield repair (logistics) |

#### Armor Tanking (171 types)
| Module Type | Group ID | Types | Function |
|-------------|----------|-------|----------|
| Armor Repair Unit | 62 | 105 | Active armor regeneration |
| Armor Hardener | 167 | 34 | Resistance modules |
| Armor Plating | 168 | 32 | Passive armor HP increase |
| Remote Armor Repairer | 259 | - | Remote armor repair |

#### Propulsion (147 types)
| Module Type | Group ID | Types | Function |
|-------------|----------|-------|----------|
| Propulsion Module | 46 | 147 | Afterburners and Microwarpdrives |

#### Electronic Warfare (572 types)
| Module Type | Group ID | Types | Function |
|-------------|----------|-------|----------|
| Warp Scrambler | 52 | 57 | Prevents warping |
| Stasis Web | 65 | 19 | Reduces target speed |
| Energy Neutralizer | 71 | 57 | Drains capacitor |
| ECM | 213 | 11 | Breaks target locks |
| Target Painter | 303 | 428 | Increases target signature radius |

#### Damage Application (14 types)
| Module Type | Group ID | Types | Weapon System |
|-------------|----------|-------|---------------|
| Gyrostabilizer | 59 | - | Projectile |
| Heat Sink | 214 | - | Energy |
| Magnetic Field Stabilizer | 215 | - | Hybrid |
| Ballistic Control System | 216 | - | Missile |

---

## 3. Meta Levels (Item Variants)

The SDE tracks **13 different meta groups** representing item rarity and tech level. This creates a progression system from basic items to powerful variants.

### Meta Group Hierarchy

| Meta Level | Name | Items | Description |
|------------|------|-------|-------------|
| 1 | Tech I | 2,626 | Basic items |
| 2 | Tech II | 2,198 | Advanced Tech II versions |
| 3 | Storyline | 440 | Mission reward items |
| 4 | Faction | 2,838 | Faction-specific variants |
| 5 | Officer | 612 | Rare officer drops |
| 6 | Deadspace | 362 | Deadspace complex drops |
| 14 | Tech III | 273 | Strategic cruiser subsystems |
| 15 | Abyssal | 260 | Abyssal deadspace mods |
| 17 | Premium | 1,388 | Special edition |
| 19 | Limited Time | 1,461 | Event/time-limited |
| 52 | Structure Faction | 122 | Structure variants |
| 53 | Structure Tech II | 304 | Structure T2 |
| 54 | Structure Tech I | 492 | Structure T1 |

### Example Meta Progression: 1MN Afterburner

1. **Tech I (Base)**: 1MN Afterburner I
2. **Tech I (Variants)**:
   - 1MN Y-S8 Compact Afterburner (better fitting)
   - 1MN Monopropellant Enduring Afterburner (less cap use)
3. **Tech II**: 1MN Afterburner II (better stats)
4. **Storyline**: 1MN Analog Booster Afterburner
5. **Faction**: Domination 1MN Afterburner (significantly better)

---

## 4. Weapon Systems

EVE has four primary weapon systems, each with unique characteristics:

### Turret Weapons (606 types)

#### Energy Weapons (Lasers) - 216 types
- **Damage**: EM / Thermal
- **Ammunition**: Frequency Crystals (184 types)
- **Strengths**: Instant hit, optimal range tracking, no ammo consumption (T1 crystals)
- **Weaknesses**: High capacitor use, fixed damage types
- **Races**: Amarr

#### Hybrid Weapons - 223 types
- **Damage**: Kinetic / Thermal
- **Ammunition**: Hybrid Charges (208 types)
- **Types**: Railguns (long-range, high damage), Blasters (short-range, very high damage)
- **Strengths**: Balanced damage, versatile
- **Weaknesses**: Capacitor use, limited damage types
- **Races**: Gallente, Caldari

#### Projectile Weapons - 167 types
- **Damage**: Explosive / Kinetic
- **Ammunition**: Projectile Ammo (128 types)
- **Types**: Artillery (long-range, alpha strike), Autocannons (short-range, high DPS)
- **Strengths**: No capacitor use, flexible damage selection
- **Weaknesses**: falloff-based damage, reloading required
- **Races**: Minmatar

### Missile Systems (148 types)

- **Damage**: All four types (EM, Thermal, Kinetic, Explosive)
- **Ammunition**: Missiles (guided and unguided)
- **Types**:
  - Light Missile (17 types) - Frigate-sized
  - Heavy Missile (16 types) - Cruiser-sized
  - Cruise Missile (16 types) - Battleship-sized
  - Rocket (16 types) - Short-range frigate
  - Torpedo (16 types) - Short-range capital/battleship
- **Strengths**: Damage type selection, no tracking, guaranteed hit
- **Weaknesses**: Travel time, can be destroyed by defenders
- **Races**: Caldari (primary), all races have some missile options

### Drones (133 types total)

#### Combat Drones (80 types)
- **Damage**: All four types (EM, Thermal, Kinetic, Explosive)
- **Sizes**: Small, Medium, Heavy, Sentry
- **Examples**:
  - Hobgoblin I (Thermal)
  - Ogre I (Thermal)
  - Warrior I (Kinetic/Explosive)
  - Valkyrie I (Explosive)
- **Strengths**: Independent of ship, selectable damage, no capacitor
- **Weaknesses**: Can be destroyed, travel time, limited bandwidth

#### Other Drone Types
- **Electronic Warfare Drone** (12 types)
- **Logistic Drone** (18 types)
- **Energy Neutralizer Drone** (3 types)
- **Mining Drone** (14 types)
- **Salvage Drone** (3 types)
- **Stasis Webifying Drone** (3 types)

### Fighters (94 types)

#### Carrier Fighters
- **Light Fighter** (24 types) - Anti-support, fast
- **Heavy Fighter** (17 types) - Anti-capital, heavy damage
- **Support Fighter** (12 types) - Electronic warfare, logistics

#### Structure Fighters
- **Structure Light Fighter** (16 types)
- **Structure Heavy Fighter** (17 types)
- **Structure Support Fighter** (8 types)

---

## 5. Damage Types

EVE Online uses four damage types, which interact differently with shield and armor resistances:

| Damage Type | Best Against | Worst Against | Typical Users |
|-------------|--------------|---------------|---------------|
| **EM** (Electromagnetic) | Shields (40% base resist) | Armor (60% base resist) | Amarr (Lasers) |
| **Thermal** | Balanced | Balanced | All races (secondary) |
| **Kinetic** | Armor (20% base resist) | Shields (40% base resist) | Caldari (Railguns/Missiles) |
| **Explosive** | Armor (10% base resist) | Shields (50% base resist) | Minmatar (Projectiles) |

### Racial Damage Preferences

- **Amarr**: EM/Thermal (Lasers - fixed ratio)
- **Caldari**: Kinetic/Thermal (Railguns, Kinetic missiles)
- **Gallente**: Thermal/Kinetic (Blasters, Drones)
- **Minmatar**: Explosive/Kinetic (Projectiles - selectable)

---

## 6. Charges and Ammunition

The Charge category (Category 8) contains **1,015 published types** across 68 groups.

### Charge Types

#### Turret Ammunition
| Ammo Type | Types | Weapon System | Damage Types |
|-----------|-------|---------------|--------------|
| Projectile Ammo | 128 | Projectile Weapons | Selectable (EM/Th/Kin/Exp) |
| Hybrid Charge | 208 | Hybrid Weapons | Fixed mix (Kinetic/Thermal) |
| Frequency Crystal | 184 | Energy Weapons | Fixed mix (EM/Thermal) |

#### Missile Ammunition
| Missile Type | Types | Size | Notes |
|--------------|-------|------|-------|
| Light Missile | 17 | Frigate | Fast, light damage |
| Heavy Missile | 16 | Cruiser | Standard damage |
| Cruise Missile | 16 | Battleship | Long-range, heavy damage |
| Rocket | 16 | Frigate (short) | High DPS, short range |
| Torpedo | 16 | Capital/BS | Short-range, massive damage |
| Defender Missile | 1 | Countermeasure | Destroys incoming missiles |

#### Other Charges
- **Capacitor Booster Charge** (18 types) - Instant capacitor
- **Bomb** (4 types) - Area of effect weapons (Stealth Bombers)
- **Advanced Ammo** (32 types) - Tech II specialty ammunition

---

## 7. Key Ship Attributes

Ships are defined by hundreds of attributes in the SDE. Here are the most important ones:

### Fitting Attributes
- `powerOutput` - Power Grid (PG) - limits heavy modules
- `cpu` - CPU - limits electronics/modules
- `upgradeCapacity` - Calibration for rigs

### Capacitor System
- `capacitorCapacity` - Total capacitor (energy)
- `rechargeRate` - Capacitor recharge time

### Slot Layout
- `hiSlots` - High slots (weapons, tackle)
- `medSlots` - Medium slots (propulsion, shield, EWAR)
- `loSlots` - Low slots (tank, damage mods)
- `rigSlots` - Rig slots (passive bonuses)
- `subSystemSlot` - Tech III subsystem slots

### Hardpoints
- `turretSlotsLeft` - Turret hardpoints
- `launcherSlotsLeft` - Missile hardpoints

### Drone Capabilities
- `droneCapacity` - Drone bay volume (m³)
- `droneBandwidth` - Drone control bandwidth (MB/s)

### Tank Attributes
- `shieldCapacity` - Total shield HP
- `armorHP` - Total armor HP
- `hp` - Structure HP
- `shieldEmDamageResonance` - Shield EM resistance (lower is better)
- `armorThermalDamageResonance` - Armor Thermal resistance
- (etc. for all damage types)

### Mobility
- `maxVelocity` - Maximum sub-warp speed (m/s)
- `agility` - Ship agility (affects align time)
- `warpSpeedMultiplier` - Warp speed multiplier (AU/s)
- `mass` - Ship mass (affects acceleration, MWD boost)

---

## 8. Module Attributes

Modules also have detailed attributes that define their performance:

### Weapon Attributes
- `damage` - Base damage
- `rateOfFire` - Shots per second
- `optimalRange` - Optimal range (meters)
- `falloffRange` - Falloff range (turrets)
- `trackingSpeed` - Tracking ability (radians/sec)
- `capacity` - Ammo capacity

### Tank Module Attributes
- `shieldBonus` - Shield boost amount
- `armorDamageAmount` - Armor repair amount
- `emDamageResistance` - EM resistance bonus
- `capacitorNeed` - Capacitor usage per cycle

### Propulsion Attributes
- `speedBoostFactor` - Speed multiplier
- `speedFactor` - Base speed increase
- `capacitorNeed` - Capacitor usage
- `durationBonus` - Duration modifiers

### EWAR Attributes
- `rangeBonus` - Optimal range
- `falloffBonus` - Falloff range
- `speedFactor` - Speed reduction (webs)
- `maxRangeBonus` - Maximum range
- `scanResolutionBonus` - Lock speed bonus

---

## 9. SDE Database Structure

### Key Tables for Ships and Combat

#### Item Tables
- **evesde_invtypes** (51,134 rows) - All item types
- **evesde_invgroups** (1,578 rows) - Item groups
- **evesde_invcategories** (48 rows) - Item categories
- **evesde_invmetatypes** (13,376 rows) - Meta variant mappings
- **evesde_invmetagroups** (13 rows) - Meta group definitions

#### Attribute Tables
- **evesde_dgmattributetypes** (2,822 rows) - Attribute definitions
- **evesde_dgmatypeattributes** (620,542 rows) - Item attribute values
- **evesde_dgmeffects** (3,354 rows) - Effect definitions
- **evesde_dgmtypeeffects** (52,342 rows) - Item effects

#### Supporting Tables
- **evesde_chrraces** (11 rows) - Playable races
- **evesde_chrfactions** (27 rows) - Factions
- **evesde_eveicons** (4,452 rows) - Icon references
- **evesde_evegraphics** (5,549 rows) - Graphic references

---

## 10. Interesting Discoveries

### 1. Ship Scale
The mass difference between a Frigate (1,067 tons) and a Titan (2,200,000 tons) is over 2,000x. Volume scales similarly (27,289 m³ vs 100,000,000 m³).

### 2. Module Variety
With 3,941 module types across 158 groups, EVE has incredible fitting variety. Even within a single module type (like Shield Extenders), there are multiple variants with different stats.

### 3. Meta Progression
The meta system creates clear progression paths:
- Tech I → Named Tech I → Tech II → Faction → Deadspace/Officer
Each tier offers better stats at increasing cost/availability.

### 4. Damage Type Balance
Each race favors different damage types, creating tactical asymmetry. Amarr's EM/Thermal is best against shields but worst against armor. Minmatar's Explosive is the opposite.

### 5. Weapon System Diversity
- Turrets (606 types) - Tracking, optimal/falloff, instant hit
- Missiles (148 types) - No tracking, damage selection, travel time
- Drones (133 types) - Independent, selectable damage, destroyable
- Fighters (94 types) - Capital-class weapons, squad-based

### 6. Tanking Styles
- **Shield Tanking** (275 modules) - Regenerates, uses mid slots
- **Armor Tanking** (171 modules) - Permanent, uses low slots
- Both have active and passive variants

### 7. EWAR Complexity
With 572 EWAR modules, electronic warfare is a major combat system:
- Warp disruption (prevents escape)
- Stasis webs (reduces mobility)
- Energy neutralization (capacitor warfare)
- ECM (breaks locks)
- Target painting (increases vulnerability)

### 8. Tech III Subsystems
Tech III ships (273 subsystem items) offer modular customization, allowing players to swap ship capabilities like tanking, propulsion, and electronics.

---

## 11. Recommendations for Display

### Ship Display Suggestions

1. **Ship Browser**
   - Hierarchical view by Category → Group → Type
   - Filter by race, tech level, size
   - Compare multiple ships side-by-side
   - Show attribute differences highlighted

2. **Ship Detail Page**
   - Basic stats: Mass, Volume, Capacity
   - Fitting: Slots, Hardpoints, PG, CPU
   - Tank: Base shield/armor/structure HP, base resistances
   - Mobility: Speed, Agility, Warp speed
   - Drone: Bay capacity, Bandwidth
   - Bonuses: Role and ship bonuses (from attributes)

3. **Module Browser**
   - Categorize by function (Weapons, Tank, Propulsion, EWAR)
   - Show meta variants together
   - Attribute comparison tool
   - Fitting calculator integration

4. **Weapon Systems**
   - Turret comparison: Damage, range, tracking, capacitor
   - Missile comparison: Damage, flight time, velocity, range
   - Drone comparison: Damage, speed, hit points, bandwidth
   - Ammo comparison: Damage type split, range bonus, cap use

5. **Interactive Features**
   - Ship fitting simulator
   - Damage profile calculator
   - EHP calculator with selectable resist profiles
   - DPS calculator with selectable targets

### Data Visualization Ideas

1. **Ship Size Chart** - Logarithmic mass/volume comparison
2. **Damage Type Chart** - Race vs damage type matrix
3. **Meta Progression** - Attribute scaling chart (Tech I → Officer)
4. **Weapon Range Bands** - Visual comparison of weapon ranges
5. **Tank Comparison** - EHP charts for different tank profiles
6. **Fitting Tool** - Drag-and-drop module fitting with PG/CPU validation

---

## 12. Technical Notes

### Database Access
The SDE is stored in SQLite at `/home/genie/data/evewire/evewire_app.sqlite3` with `evesde_` table prefix. Django models are defined in `/home/genie/gt/evewire/crew/delve/core/sde/models.py`.

### Query Examples

```python
from core.sde.models import InvTypes, InvGroups, InvCategories

# Get all published frigates
frigate_group = InvGroups.objects.get(group_id=25)
frigates = InvTypes.objects.filter(group=frigate_group, published=True)

# Get all hybrid weapons
hybrid_group = InvGroups.objects.get(group_id=74)
hybrids = InvTypes.objects.filter(group=hybrid_group, published=True)

# Get meta variants for a module
base = InvTypes.objects.get(name='1MN Afterburner I')
variants = InvMetaTypes.objects.filter(parent_type=base)
```

### Performance Considerations
- The `dgmTypeAttributes` table has 620,542 rows - use selective queries
- Join with `type_id` for efficient attribute lookups
- Cache frequently accessed attribute definitions
- Consider materialized views for common queries

---

## Conclusion

The EVE SDE provides a comprehensive view of the game's combat mechanics, with over 5,500 ships, modules, charges, drones, and fighters. The data reveals:

1. **Deep Complexity** - 46 ship groups, 158 module groups, 13 meta levels
2. **Balanced Design** - Clear tradeoffs between weapon systems and tanking styles
3. **Progression Systems** - Meta variants provide clear upgrade paths
4. **Tactical Depth** - Damage types, EWAR, and mobility create strategic variety

This data can be used to build fitting tools, ship browsers, combat simulators, and educational resources for EVE players.

---

**Report Generated:** 2026-01-27
**SDE Browser Models:** `/home/genie/gt/evewire/crew/delve/core/sde/models.py`
**Total SDE Tables:** 53
**Total Item Types:** 51,134
