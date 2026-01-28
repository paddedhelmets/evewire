# EVE Online SDE: Structures, Starbases, and Deployables

A comprehensive exploration of EVE Online's structure systems based on the Static Data Export (SDE).

## Table of Contents

1. [Introduction](#introduction)
2. [Starbases (Player Owned Structures)](#starbases-player-owned-structures)
3. [POS Fuel Requirements](#pos-fuel-requirements)
4. [Upwell Structures](#upwell-structures)
5. [Structure Modules](#structure-modules)
6. [Reactions](#reactions)
7. [Sovereignty Structures](#sovereignty-structures)
8. [NPC Stations vs Player Structures](#npc-stations-vs-player-structures)
9. [Key Findings](#key-findings)

---

## Introduction

EVE Online features multiple types of player-deployable structures, each serving different purposes:

- **Starbases (POS)**: Legacy modular structures anchored at moons
- **Upwell Structures**: Modern citadels, engineering complexes, and refineries
- **Sovereignty Structures**: Used for claiming and holding nullsec space
- **Reaction Arrays**: For moon mining and material processing

The SDE categorizes these across several categories:
- Category 23: Starbase
- Category 24: Reaction
- Category 40: Sovereignty Structures
- Category 65: Structure (Upwell)
- Category 66: Structure Module

---

## Starbases (Player Owned Structures)

Starbases, also known as POS (Player Owned Structures), are modular structures anchored at moons. They consist of a Control Tower with various attached modules.

### Control Towers

There are **42 total control tower types** in the SDE, organized by race and size:

#### Faction Control Towers (12)

Each empire has three sizes:

**Amarr**
- Amarr Control Tower (Large)
- Amarr Control Tower Medium
- Amarr Control Tower Small

**Caldari**
- Caldari Control Tower (Large)
- Caldari Control Tower Medium
- Caldari Control Tower Small

**Gallente**
- Gallente Control Tower (Large)
- Gallente Control Tower Medium
- Gallente Control Tower Small

**Minmatar**
- Minmatar Control Tower (Large)
- Minmatar Control Tower Medium
- Minmatar Control Tower Small

#### Pirate Faction Control Towers (30)

Pirate factions offer control towers with different bonuses:

**Angel Cartel** (3 sizes)
- Angel Control Tower
- Angel Control Tower Medium
- Angel Control Tower Small

**Blood Raiders** (6 variants)
- Blood Control Tower (3 sizes)
- Dark Blood Control Tower (3 sizes)

**Guristas** (6 variants)
- Guristas Control Tower (3 sizes)
- Dread Guristas Control Tower (3 sizes)

**Sansha's Nation** (6 variants)
- Sansha Control Tower (3 sizes)
- True Sansha Control Tower (3 sizes)

**Serpentis** (3 sizes)
- Serpentis Control Tower
- Serpentis Control Tower Medium
- Serpentis Control Tower Small

**Shadow** (3 sizes)
- Shadow Control Tower
- Shadow Control Tower Medium
- Shadow Control Tower Small

**Domination** (3 sizes)
- Domination Control Tower
- Domination Control Tower Medium
- Domination Control Tower Small

### Starbase Modules (28 Groups)

Starbases support a wide variety of modules for different functions:

#### Production Modules (4 groups)
- **Assembly Array** (16 types): Various sizes for different ship classes
  - Advanced Large/Medium/Small Ship Assembly Arrays
  - Capital/Supercapital Ship Assembly Arrays
  - Component/Ammunition/Drone/Subsystem Assembly Arrays
  - Drug Lab for boosters
  - Thukker Component Assembly Array

- **Mobile Reactor** (5 types): For moon material reactions
  - Simple Reactor Array
  - Complex Reactor Array
  - Biochemical Reactor Array
  - Polymer Reactor Array
  - Medium Biochemical Reactor Array

- **Reprocessing Array** (2 types)
  - Reprocessing Array
  - Intensive Reprocessing Array

- **Compression Array** (1 type)
  - Compression Array

#### Defensive Modules (10 groups)

**Weapon Batteries** (4 groups)
- **Mobile Laser Sentry** (30 types): Beam and Pulse lasers
  - Standard, Blood, Dark Blood, Sansha, True Sansha variants

- **Mobile Hybrid Sentry** (18 types): Railguns and Blasters
  - Standard, Serpentis, Shadow variants

- **Mobile Projectile Sentry** (18 types): Artillery and Autocannons
  - Standard, Angel, Domination variants

- **Mobile Missile Sentry** (9 types): Cruise and Torpedo launchers
  - Standard, Guristas, Dread Guristas variants

**Electronic Warfare** (4 groups)
- **Electronic Warfare Battery** (12 types): ECM jammers
  - Ion Field, Phase Inversion, Spatial Destabilization, White Noise
  - Guristas and Dread Guristas variants

- **Energy Neutralizing Battery** (5 types): Capacitor neutralizers
  - Standard, Blood, Dark Blood, Sansha, True Sansha variants

- **Sensor Dampening Battery** (3 types): Sensor dampeners
  - Standard, Serpentis, Shadow variants

- **Stasis Webification Battery** (3 types): Webifiers
  - Standard, Angel, Domination variants

- **Warp Scrambling Battery** (6 types): Warp disruptors/scramblers
  - Standard, Serpentis, Shadow variants

**Defensive Enhancements** (2 groups)
- **Shield Hardening Array** (4 types): Resist modules
  - Ballistic Deflection, Explosion Dampening, Heat Dissipation, Photon Scattering

- **Tracking Array** (1 type): Turret tracking enhancement

#### Storage Modules (2 groups)
- **Corporate Hangar Array** (1 type): Corporate storage
- **Personal Hangar** (1 type): Individual pilot storage

**Silo** (7 types): Material storage for reactions
- General Silo, Biochemical Silo, Catalyst Silo
- Hazardous Chemical Silo, Hybrid Polymer Silo
- Coupling Array, General Storage

#### Support Modules (6 groups)
- **Ship Maintenance Array** (2 types): Ship fitting and storage
- **Laboratory** (4 types): Research and invention
  - Research Laboratory, Experimental Laboratory
  - Design Laboratory, Hyasyoda Research Laboratory

- **Moon Mining** (1 type): Moon Harvesting Array

- **Jump Portal Array** (1 type): Jump Bridge for fleet mobility

- **Cynosural Generator Array** (1 type): Cynosural field generation

- **Cynosural System Jammer** (1 type): Prevents cynosural fields

- **Scanner Array** (1 type): System scanning capabilities

---

## POS Fuel Requirements

### Fuel Blocks

Starbases consume **Fuel Blocks** based on their size and race:

| Tower Size | Consumption/Hour |
|------------|------------------|
| Large      | 40 blocks        |
| Medium     | 20 blocks        |
| Small      | 10 blocks        |

### Fuel Types by Race

Each faction uses a specific fuel block type:

| Faction | Fuel Block | Pirate Variants |
|---------|------------|-----------------|
| Amarr | Helium Fuel Block | Blood, Dark Blood |
| Caldari | Nitrogen Fuel Block | - |
| Gallente | Oxygen Fuel Block | Serpentis, Shadow |
| Minmatar | Hydrogen Fuel Block | Angel, Domination |
| - | - | Guristas, Sansha, True Sansha |

**Note**: Pirate faction towers consume 10% less fuel (36/18/9 instead of 40/20/10).

### Strontium Clathrates (Reinforcement Fuel)

All towers require Strontium Clathrates for reinforced mode:

| Tower Size | Strontium Capacity |
|------------|-------------------|
| Large      | 400 units         |
| Medium     | 200 units         |
| Small      | 100 units         |

### Starbase Charters (High-Sec Only)

In high-security space, towers additionally consume **Starbase Charters** based on the faction controlling the region:

- Amarr Empire Starbase Charter
- Caldari State Starbase Charter
- Gallente Federation Starbase Charter
- Minmatar Republic Starbase Charter
- Khanid Kingdom Starbase Charter
- Ammatar Mandate Starbase Charter

All towers require 1 charter per hour regardless of their faction.

### Resource Purpose Codes

The SDE tracks resources by purpose:
- **Purpose 1**: Consumption (fuel blocks, charters)
- **Purpose 2**: CPU usage (not shown in current data)
- **Purpose 3**: PowerGrid usage (not shown in current data)
- **Purpose 4**: Reinforce (strontium clathrates)

---

## Upwell Structures

Upwell structures are the modern replacement for starbases, introduced in 2016. They offer better defenses, asset safety, and more flexibility.

### Structure Classes (7 Groups)

#### 1. Citadels (9 types)

Combat-focused defensive structures:

**Size Classes**
- **Astrahus** (Medium): ID 35832
- **Fortizar** (Large): ID 35833
  - Special editions: 'Draccous', 'Horizon', 'Marginis', 'Moreau', 'Prometheus'
- **Keepstar** (XL): ID 35834
- **Upwell Palatine Keepstar** (XL Special): ID 40340

#### 2. Engineering Complexes (3 types)

Industrial structures for manufacturing and research:

- **Raitaru** (Medium): ID 35825
- **Azbel** (Large): ID 35826
- **Sotiyo** (XL): ID 35827

#### 3. Refineries (2 types)

Mining and reprocessing focused structures:

- **Athanor** (Medium): ID 35835
- **Tatara** (XL): ID 35836

#### 4. Upwell Moon Drill (1 type)

Specialized moon mining structure:

- **Metenox Moon Drill**: ID 81826
  - Passively mines moons over time
  - Requires significant fuel and setup

#### 5. Infrastructure Structures (3 types)

**Ansiblex Jump Bridge** (ID 35841)
- Creates jump bridges for fleet mobility
- Connects two systems for rapid transit

**Pharolux Cyno Beacon** (ID 35840)
- Generates cynosural field for capital jumps
- More flexible than ship-mounted cynos

**Tenebrex Cyno Jammer** (ID 37534)
- Prevents cynosural fields in the system
- Critical for nullsec defense

---

## Structure Modules

Structure modules (Category 66) provide services, weapons, and bonuses to Upwell structures. There are **over 100 different groups** of modules.

### Major Module Categories

#### Service Modules (5+ groups)

**Citadel Services**
- Standup Cloning Center
- Standup Market Hub

**Engineering Services**
- Standup Capital Shipyard
- Standup Invention Lab
- Standup Hyasyoda Research Lab

**Resource Processing**
- Standup Biochemical Reactor
- Standup Composite Reactor
- Standup Hybrid Reactor
- Standup Moon Drill

#### Weapon Systems (10+ groups)

- **Structure XL Missile Launcher**: Anticapital missiles
- **Structure Multirole Missile Launcher**: Standard missiles
- **Structure Guided Bomb Launcher**: Area effect bombs
- **Structure Energy Neutralizer**: Capacitor warfare
- **Structure ECM Battery**: Electronic countermeasures
- **Structure Burst Projector**: AOE effects
- **Structure Doomsday Weapon**: XL-only superweapon

#### Fitting Modules (4 groups)

- **Structure Fitting Module**
  - Standup Co-Processor Array (CPU upgrade)
  - Standup Reactor Control Unit (PG upgrade)
  - Standup Capacitor Power Relay
  - Standup Signal Amplifier

- **Structure Weapon Upgrade**
  - Standup Ballistic Control System
  - Standup Missile Guidance Enhancer

- **Structure Capacitor Battery**: Active tanking module
- **Structure Armor Reinforcer**: Passive armor tank

#### Defensive Modules (2 groups)

- **Structure Stasis Webifier**: Speed reduction
- **Structure Warp Scrambler**: Tackle prevention

#### Disruption (1 group)

**Structure Disruption Battery** (6 types)
- Standup Jammer Burst Projector variants
- Electronic warfare against enemy ships

#### Rigs (80+ types)

Rigs provide permanent bonuses to structures. They come in three sizes:

**Combat Rigs**
- Missile Application, Projection
- Energy Neutralizer, EW systems
- Targeting, Max Targets

**Engineering Rigs**
- Manufacturing time and material efficiency
- Research time and cost
- Invention bonuses
- Split across M, L, XL sizes

**Drilling Rigs**
- Moon drilling efficiency and stability

**Resource Rigs**
- Ore, ice, and moon ore reprocessing
- Asteroid, ice, moon ore specialization

**Reactor Rigs**
- Biochemical, composite, hybrid reactions
- Material and time efficiency

#### Quantum Cores (9 types)

Required for anchoring XL structures:
- Astrahus/Athanor/Raitaru Upwell Quantum Core
- Azbel/Fortizar Upwell Quantum Core
- Keepstar/Tatara/Sotiyo Upwell Quantum Core
- Palatine Keepstar Upwell Quantum Core

#### Outpost Conversion Rigs (104 types)

Special rigs for converting former nullsec outposts to Upwell structures:
- Various combinations of bonuses (A1, A2, A3, etc.)
- Abbreviated (A) or Optimized (O) variants

---

## Reactions

Reaction structures (Category 24) are used for moon mining and material processing. However, in the current SDE data, **all reaction groups show 0 published types**.

### Reaction Groups (5)

1. **Simple Reaction** (0 published types)
2. **Complex Reactions** (0 published types)
3. **Simple Biochemical Reactions** (0 published types)
4. **Complex Biochemical Reactions** (0 published types)
5. **Hybrid Reactions** (0 published types)

**Note**: This suggests that reactions are now handled through Structure Modules (Standup Reactors) rather than separate reaction types, or the data has been moved to a different system.

### Starbase Reactor Arrays

While not in the Reaction category, Starbases include **Mobile Reactor** modules:

- **Simple Reactor Array**: Basic moon material reactions
- **Complex Reactor Array**: Advanced reactions
- **Biochemical Reactor Array**: Gas and booster reactions
- **Polymer Reactor Array**: T3 component reactions
- **Medium Biochemical Reactor Array**: Medium gas reactions

---

## Sovereignty Structures

Sovereignty structures (Category 40) are used for claiming and holding nullsec space.

### Sovereignty Structures (2 types)

#### 1. Territorial Claim Unit (TCU)

- **Defunct Territorial Claim Unit**: ID 32226
- Used to claim sovereignty in a system
- Deprecated in favor of the new sovereignty system

#### 2. Sovereignty Hub

- **Sovereignty Hub**: ID 32458
- Central structure for the new sovereignty system
- Requires infrastructure hubs to function
- Anchors the sovereignty claim

**Note**: The "Defunct" designation indicates the old sovereignty system has been replaced with the Entosis-based system introduced in 2015.

---

## NPC Stations vs Player Structures

### NPC Stations (staStations Table)

The SDE contains **5,154 NPC stations** across New Eden, with **43 unique station types**.

#### Station Type Examples

**Amarr Stations**
- Amarr Standard Station
- Amarr Industrial Station
- Amarr Mining Station
- Amarr Research Station
- Amarr Station Military
- Amarr Trade Post
- Amarr Station Hub

**Caldari Stations**
- Caldari Administrative Station
- Caldari Logistics Station
- Caldari Military Station
- Caldari Mining Station
- Caldari Research Station
- Caldari Food Processing Plant Station

**Other Empires**
- Gallente stations (federal, administrative, etc.)
- Minmatar stations (republic, tribal, etc.)
- Jovian stations (ancient, rare)

#### Key Differences Between Stations and Structures

| Feature | NPC Stations | Player Structures (Upwell) |
|---------|--------------|---------------------------|
**Ownership** | NPC corporations | Player corporations/alliances |
**Anchoring** | Fixed by game developers | Anchored by players |
**Destructibility** | Indestructible | Can be destroyed |
**Asset Safety** | Not applicable | Asset safety on destruction |
**Location** | Predetermined | Player-selected (with restrictions) |
**Services** | Fixed per station type | Configurable via service modules |
**Taxation** | NPC-controlled fees | Player-controlled fees |

### Structure vs Station Database Models

**StaStations** (NPC Stations)
- station_id: Primary key
- station_name: Station name
- solar_system_id: Location
- corporation_id: Owning NPC corp
- station_type_id: References invTypes
- Various service flags (reprocessing, cloning, etc.)

**InvTypes** (Both)
- Contains both station types and structure types
- Distinguished by category field
- Stations: Various categories (Station category not in explored data)
- Structures: Categories 23, 24, 40, 65, 66

---

## Key Findings

### 1. Starbase System Complexity

The legacy POS system is highly modular with:
- **28 different module groups** for various functions
- **42 control tower variants** (12 empire + 30 pirate)
- **Size-based scaling** (Small/Medium/Large) affecting fuel and capacity
- **Race-specific bonuses** for different gameplay styles

### 2. Fuel Economy

POS fuel requirements are systematic:
- **Fuel blocks** standardized consumption (10/20/40 per hour)
- **10% fuel bonus** for pirate faction towers
- **Strontium** for reinforcement mode (100/200/400 capacity)
- **Starbase charters** required in high-sec (1 per hour)

### 3. Upwell Structure Simplification

The Upwell system simplified structures:
- **4 main structure classes** (Citadel, Engineering, Refinery, Moon Drill)
- **3 size tiers** (Medium, Large, XL)
- **Modular service system** via service modules
- **Asset safety** protects player assets on destruction

### 4. Module Proliferation

Structure modules number in the hundreds:
- **100+ module groups** for every function imaginable
- **80+ rig types** providing specialized bonuses
- **Size-restricted modules** (M/L/XL)
- **Tech variants** (Tech I and Tech II)

### 5. Sovereignty Evolution

Sovereignty structures have evolved:
- **Old system**: TCUs (now defunct)
- **New system**: Sovereignty Hubs with Entosis links
- **Infrastructure-based**: Requires multiple structure types

### 6. Reaction System Changes

The reaction system appears to have migrated:
- **Old system**: Starbase reactor arrays
- **New system**: Standup reactor service modules
- **No published reaction types** in current SDE category 24

### 7. Station vs Structure Distinction

NPC stations and player structures serve different roles:
- **Stations**: Indestructible, NPC-owned, fixed locations
- **Structures**: Destructible, player-owned, flexible locations
- **Convergence**: Structures can provide station-like services (cloning, market, etc.)

---

## Database Relationships

### Key Tables and Relationships

```
InvCategories
├── Category 23: Starbase
│   └── InvGroups → InvTypes
│       ├── Control Tower (365)
│       ├── Assembly Array (397)
│       ├── Mobile Reactor (438)
│       └── ... (25 more groups)
├── Category 24: Reaction
│   └── InvGroups → InvTypes (0 published)
├── Category 40: Sovereignty Structures
│   └── InvGroups → InvTypes
│       ├── Territorial Claim Unit (1003)
│       └── Sovereignty Hub (1012)
├── Category 65: Structure
│   └── InvGroups → InvTypes
│       ├── Citadel (1657)
│       ├── Engineering Complex (1404)
│       ├── Refinery (1406)
│       └── ... (4 more groups)
└── Category 66: Structure Module
    └── InvGroups → InvTypes
        ├── Structure Citadel Service Module (1321)
        ├── Structure Engineering Rig M (1816+)
        └── ... (100+ more groups)

InvControlTowerResources
├── control_tower_type_id → InvTypes.type_id
├── resource_type_id → InvTypes.type_id
├── purpose (1=Consumption, 4=Reinforce)
└── quantity

StaStations
├── station_type_id → InvTypes.type_id
├── solar_system_id → MapSolarSystems.solarSystemID
└── corporation_id → CrpNPCCorporations.corporationID
```

---

## Conclusion

The EVE Online SDE reveals a rich and complex structure ecosystem that has evolved over two decades:

1. **Legacy POS system** remains in the SDE with extensive modularity
2. **Upwell structures** represent a modernized, streamlined approach
3. **Sovereignty mechanics** have shifted from territorial claims to hub-based systems
4. **Industrial processes** have moved from starbases to specialized structures
5. **Player agency** has expanded with deployable structures rivaling NPC stations

The data shows CCP's ongoing effort to balance complexity with accessibility, moving from the highly modular but unforgiving POS system to the more structured and safer Upwell system, while maintaining depth through hundreds of module and rig combinations.

---

*Report generated from EVE Online Static Data Export (SDE)*
*Database: /home/genie/gt/evewire/crew/delve/db.sqlite3*
*Generated: 2025*
