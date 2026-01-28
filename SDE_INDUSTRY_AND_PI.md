# EVE Online SDE: Industry and Planetary Interaction Systems

A comprehensive exploration of industry, manufacturing, reprocessing, and planetary interaction systems in the EVE Online Static Data Export (SDE).

## Table of Contents

1. [Blueprint System](#blueprint-system)
2. [Planetary Interaction (PI)](#planetary-interaction-pi)
3. [Reprocessing System](#reprocessing-system)
4. [POS Fuel Requirements](#pos-fuel-requirements)
5. [Station Services](#station-services)
6. [Data Model Reference](#data-model-reference)

---

## Blueprint System

### Overview

The blueprint system in EVE Online enables manufacturing of almost all items in the game. Blueprints are stored in Category 9 and contain the data needed to produce items.

### Key Statistics

- **Total Blueprint Types**: 5,072
- **Total Blueprint Groups**: 209
- **Blueprints in industryBlueprints table**: 5,059

### Blueprint Categories

Blueprints are organized into groups covering all manufacturing areas:

#### Ship Blueprints
- **Battleship Blueprint**: 42 types (e.g., Abaddon Blueprint)
- **Battlecruiser Blueprint**: 33 types
- **Capital Industrial Ship Blueprint**: 1 type (e.g., Rorqual Blueprint)
- **Industrial Command Ship Blueprint**: 1 type (e.g., Orca Blueprint)
- **Expedition Command Ship Blueprint**: 1 type (e.g., Odysseus Blueprint)

#### Module Blueprints
- **Armor Coating Blueprint**: 80 types
- **Armor Hardener Blueprint**: 28 types
- **Armor Repair Unit Blueprint**: 20 types
- **Capacitor Booster Blueprint**: 23 types
- **Ballistic Control System Blueprint**: 7 types

#### Ammunition & Charges
- **Advanced Projectile Ammo Blueprint**: 16 types
- **Advanced Hybrid Charge Blueprint**: 16 types
- **Advanced Frequency Crystal Blueprint**: 16 types
- **Capacitor Booster Charge Blueprint**: 9 types

#### Advanced Components
- **Advanced Capital Construction Component Blueprints**: 40 types
- **Capital Construction Blueprints**: 25 types
- **Biochemical Reaction Formulas**: 32 types

### Blueprint Data Structure

Each blueprint contains:
- `type_id`: Unique identifier
- `max_production_limit`: Maximum runs per blueprint copy (from industryBlueprints table)
- `portion_size`: Quantity produced per manufacturing run
- `volume`: Blueprint volume (typically 0.01 m³)
- `published`: Whether the blueprint is available on the market
- `base_price`: NPC price (if applicable)

### Blueprint Properties Example

```
ID: 23784
Name: 'Abatis' 100mm Steel Plates I Blueprint
Published: True
Volume: 0.01 m³
Portion Size: 1
Base Price: None
```

---

## Planetary Interaction (PI)

### Overview

Planetary Interaction allows players to extract resources from planets, process them into commodities, and manufacture advanced materials. The PI system spans three main categories:

- **Category 42**: Planetary Resources (raw materials, T0)
- **Category 41**: Planetary Industry (structures and equipment)
- **Category 43**: Planetary Commodities (processed goods, T1-T4)

### T0 Resources (Raw Materials)

There are **15 basic planetary resources** extracted directly from planets:

| ID | Resource Name | Volume |
|----|---------------|--------|
| 2268 | Aqueous Liquids | 0.005 m³ |
| 2305 | Autotrophs | 0.005 m³ |
| 2267 | Base Metals | 0.005 m³ |
| 2288 | Carbon Compounds | 0.005 m³ |
| 2287 | Complex Organisms | 0.005 m³ |
| 2307 | Felsic Magma | 0.005 m³ |
| 2272 | Heavy Metals | 0.005 m³ |
| 2309 | Ionic Solutions | 0.005 m³ |
| 2073 | Microorganisms | 0.005 m³ |
| 2310 | Noble Gas | 0.005 m³ |
| 2270 | Noble Metals | 0.005 m³ |
| 2306 | Non-CS Crystals | 0.005 m³ |
| 2286 | Planktic Colonies | 0.005 m³ |
| 2311 | Reactive Gas | 0.005 m³ |
| 2308 | Suspended Plasma | 0.005 m³ |

### PI Structures (Category 41)

Total published PI commodities: **91 types**

#### Command Centers (8 types)
- Barren Command Center (2524)
- Gas Command Center (2534)
- Ice Command Center (2533)
- Lava Command Center (2549)
- Oceanic Command Center (2525)
- Plasma Command Center (2551)
- Storm Command Center (2550)
- Temperate Command Center (2254)

Each command center has a volume of 1,000 m³ and a base price of 90,000 ISK.

#### Extractor Control Units (8 types)
One for each planet type, enabling resource extraction.

#### Extractors (40+ types)
Specialized extractors for each resource type on each planet type:
- Barren Aqueous Liquid Extractor (2409)
- Gas Ionic Solutions Extractor (2424)
- Lava Suspended Plasma Extractor (2418)
- And many more...

#### Industry Facilities
- Basic Industry Facility (75,000 ISK)
- Advanced Industry Facility (250,000 ISK)
- High-Tech Production Plant (525,000 ISK)

#### Storage & Export
- Storage Facility (250,000 ISK)
- Launchpad (900,000 ISK)

### PI Schematics (Category 43)

Total schematics: **68**

Schematics define production recipes, including:
- **Inputs**: Required materials
- **Outputs**: Produced materials
- **Cycle Time**: Production time per run

#### Schematic Cycle Times

Most schematics have one of two cycle times:
- **1,800 seconds** (30 minutes): Basic processing (T1-T2)
- **3,600 seconds** (1 hour): Advanced processing (T2-T4)

### Production Tiers

#### T1 Products (Basic Processing)
Examples:
- **Water** (121): 1,800s cycle
- **Oxygen** (124): 1,800s cycle
- **Silicon** (130): 1,800s cycle
- **Oxides** (69): 3,600s cycle

#### T2 Products (Intermediate Processing)
Examples:
- **Toxic Metals** (128): 1,800s cycle
  - Input: Heavy Metals x 3,000
  - Output: Toxic Metals x 20

- **Precious Metals** (127): 1,800s cycle
- **Reactive Metals** (126): 1,800s cycle

#### T3 Products (Advanced Processing)
Examples:
- **Mechanical Parts** (73): 3,600s cycle
- **Consumer Electronics** (76): 3,600s cycle
- **Robotics** (97): 3,600s cycle
  - Input: Mechanical Parts x 10
  - Input: Consumer Electronics x 10
  - Output: Robotics x 3

#### T4 Products (High-Tech)
Examples:
- **Guidance Systems** (100): 3,600s cycle
- **Supercomputers** (96): 3,600s cycle
- **Self-Harmonizing Power Core** (115): 3,600s cycle

### Complete Schematic List

1. **Bacteria** (131) - 1,800s
2. **Biocells** (79) - 3,600s
3. **Biofuels** (134) - 1,800s
4. **Biomass** (132) - 1,800s
5. **Biotech Research Reports** (104) - 3,600s
6. **Broadcast Node** (117) - 3,600s
7. **Camera Drones** (91) - 3,600s
8. **Chiral Structures** (129) - 1,800s
9. **Condensates** (90) - 3,600s
10. **Construction Blocks** (74) - 3,600s
11. **Consumer Electronics** (76) - 3,600s
12. **Coolant** (66) - 3,600s
    - Input: Electrolytes x 40
    - Input: Water x 40
    - Output: Coolant x 5
13. **Cryoprotectant Solution** (111) - 3,600s
14. **Data Chips** (109) - 3,600s
15. **Electrolytes** (123) - 1,800s
16. **Enriched Uranium** (75) - 3,600s
17. **Fertilizer** (82) - 3,600s
18. **Gel-Matrix Biopaste** (95) - 3,600s
19. **Genetically Enhanced Livestock** (83) - 3,600s
20. **Guidance Systems** (100) - 3,600s
21. **Hazmat Detection Systems** (110) - 3,600s
22. **Hermetic Membranes** (107) - 3,600s
23. **High-Tech Transmitter** (94) - 3,600s
24. **Industrial Explosives** (106) - 3,600s
25. **Industrial Fibers** (135) - 1,800s
26. **Integrity Response Drones** (118) - 3,600s
27. **Livestock** (84) - 3,600s
28. **Mechanical Parts** (73) - 3,600s
29. **Microfiber Shielding** (80) - 3,600s
30. **Miniature Electronics** (77) - 3,600s
31. **Nanites** (78) - 3,600s
32. **Nano-Factory** (114) - 3,600s
33. **Neocoms** (102) - 3,600s
34. **Nuclear Reactors** (99) - 3,600s
35. **Organic Mortar Applicators** (112) - 3,600s
36. **Oxides** (69) - 3,600s
37. **Oxidizing Compound** (125) - 1,800s
38. **Oxygen** (124) - 1,800s
39. **Planetary Vehicles** (103) - 3,600s
40. **Plasmoids** (122) - 1,800s
41. **Polyaramids** (88) - 3,600s
42. **Polytextiles** (85) - 3,600s
43. **Precious Metals** (127) - 1,800s
44. **Proteins** (133) - 1,800s
45. **Reactive Metals** (126) - 1,800s
46. **Recursive Computing Module** (116) - 3,600s
47. **Robotics** (97) - 3,600s
48. **Rocket Fuel** (67) - 3,600s
49. **Self-Harmonizing Power Core** (115) - 3,600s
50. **Silicate Glass** (70) - 3,600s
51. **Silicon** (130) - 1,800s
52. **Smartfab Units** (98) - 3,600s
53. **Sterile Conduits** (113) - 3,600s
54. **Supercomputers** (96) - 3,600s
55. **Superconductors** (65) - 3,600s
56. **Supertensile Plastics** (87) - 3,600s
57. **Synthetic Oil** (68) - 3,600s
58. **Synthetic Synapses** (92) - 3,600s
59. **Test Cultures** (86) - 3,600s
60. **Toxic Metals** (128) - 1,800s
61. **Transcranial Microcontroller** (108) - 3,600s
62. **Transmitter** (71) - 3,600s
63. **Ukomi Superconductor** (89) - 3,600s
64. **Vaccines** (105) - 3,600s
65. **Viral Agent** (81) - 3,600s
66. **Water** (121) - 1,800s
67. **Water-Cooled CPU** (72) - 3,600s
68. **Wetware Mainframe** (119) - 3,600s

### PI Production Chain Example

**Coolant Production** (T2 Product):
```
Electrolytes (T1) x 40 + Water (T1) x 40 → Coolant (T2) x 5
Cycle Time: 3,600 seconds (1 hour)
```

**Robotics Production** (T3 Product):
```
Mechanical Parts (T2) x 10 + Consumer Electronics (T2) x 10 → Robotics (T3) x 3
Cycle Time: 3,600 seconds (1 hour)
```

---

## Reprocessing System

### Overview

Reprocessing (also called refining) converts items, modules, ships, and ore into their base materials. The `invTypeMaterials` table defines what materials are recovered from each item.

### Key Tables

- **invTypeMaterials**: Maps items to their reprocessing materials
  - `type_id`: The item being reprocessed
  - `material_type_id`: The material recovered
  - `quantity`: Amount recovered per unit

### Common Minerals

The basic minerals from ore reprocessing (Category 4, Group "Mineral"):

| ID | Mineral Name | Usage |
|----|--------------|-------|
| 34 | Tritanium | Most common, basic construction |
| 35 | Pyerite | Common mineral |
| 36 | Mexallon | Standard mineral |
| 37 | Isogen | Advanced mineral |
| 38 | Nocxium | Specialized mineral |
| 39 | Zydrine | Rare mineral |
| 40 | Megacyte | Very rare mineral |
| 11399 | Morphite | Advanced technology mineral |

### Reprocessing Examples

#### Vexor Reprocessing

The Vexor (ID 23757, a Gallente cruiser) reprocesses into capital components:

```
Capital Propulsion Engine: 4 units
Capital Sensor Cluster: 4 units
Capital Armor Plates: 6 units
Capital Capacitor Battery: 3 units
Capital Power Generator: 3 units
Capital Shield Emitter: 3 units
Capital Jump Drive: 4 units
Capital Drone Bay: 12 units
Capital Computer System: 3 units
Capital Construction Parts: 4 units
Capital Ship Maintenance Bay: 6 units
Capital Corporate Hangar Bay: 3 units
```

*Note: This appears to be an SDE anomaly - Vexors should reprocess into standard minerals, not capital components.*

#### Tritanium Sources

Items that reprocess into Tritanium (ID 34):

- **Plagioclase** (Ore): 175 units
- **Spodumain** (Ore): 48,000 units
- **Credits**: 4,096 units
- **Various ammunition**: 17-204 units

#### Pyerite Sources

Items that reprocess into Pyerite (ID 35):

- **Hedbergite** (Ore): 450 units
- **Arkonor** (Ore): 3,200 units
- **Credits**: 1,024 units
- **Various ammunition**: 3-64 units

### Reprocessing Efficiency

The actual materials recovered depend on:
- Station reprocessing efficiency (typically 50% base)
- Player skills (Reprocessing, Reprocessing Efficiency, Ore Processing skills)
- Station "take" percentage (tax on reprocessing)

---

## POS Fuel Requirements

### Overview

Player-Owned Starbases (POS) require fuel to operate. The `invControlTowerResources` table defines fuel requirements for each control tower type.

### Fuel Types

#### Fuel Blocks (Purpose: 1)
- **Nitrogen Fuel Block** (4051): Used by Amarr towers
- **Helium Fuel Block** (4247): Used by Caldari towers
- **Oxygen Fuel Block** (4312): Used by Gallente towers
- **Hydrogen Fuel Block** (4246): Used by Minmatar towers

#### Starbase Charters (Purpose: 1, High-Sec Only)
Required in high-security space (0.45 security+):
- **Amarr Empire Starbase Charter** (24592)
- **Caldari State Starbase Charter** (24593)
- **Gallente Federation Starbase Charter** (24594)
- **Minmatar Republic Starbase Charter** (24595)
- **Khanid Kingdom Starbase Charter** (24596)
- **Ammatar Mandate Starbase Charter** (24597)

#### Strontium Clathrates (Purpose: 4)
Used for reinforced mode (shield reinforcement)

### Amarr Control Tower Example

**Amarr Control Tower** (ID 20062) fuel requirements:

| Fuel | Purpose | Quantity | Min Security |
|------|---------|----------|--------------|
| Nitrogen Fuel Block | Fuel | 10 | None |
| Amarr Empire Starbase Charter | Fuel | 1 | 0.45+ |
| Caldari State Starbase Charter | Fuel | 1 | 0.45+ |
| Gallente Federation Starbase Charter | Fuel | 1 | 0.45+ |
| Minmatar Republic Starbase Charter | Fuel | 1 | 0.45+ |
| Khanid Kingdom Starbase Charter | Fuel | 1 | 0.45+ |
| Ammatar Mandate Starbase Charter | Fuel | 1 | 0.45+ |
| Strontium Clathrates | Shield Reinforcement | 100 | None |

*Note: Multiple charter types are listed in the SDE, but in practice only the faction charter matching the tower's faction is used in high-security space.*

### POS Fuel Consumption

- **Fuel Blocks**: 10 per hour (240 per day)
- **Strontium Clathrates**: 100 during reinforcement activation
- **Starbase Charters**: 1 per hour in high-sec (24 per day)

---

## Station Services

### Overview

Stations provide various services including reprocessing, manufacturing, research, and more. The `staStations` table contains station information including service capabilities.

### Station Statistics

- **Total Stations**: 5,154
- **Available Columns**:
  - stationID, stationName
  - solarSystemID, constellationID, regionID
  - stationTypeID, corporationID
  - reprocessingEfficiency
  - reprocessingStationsTake
  - dockingCostPerVolume
  - maxShipVolumeDockable
  - officeRentalCost

### Reprocessing Services

Station reprocessing capabilities are defined by:
- **reprocessingEfficiency**: Base efficiency (typically 0.5 = 50%)
- **reprocessingStationsTake**: Station tax on reprocessing (typically 0.05 = 5%)

### Station Types

Stations are categorized by type (from InvTypes):

Common station types include:
- **Amarr Factory Station**
- **Caldari Administrative Station**
- **Gallente Federal Station**
- **Minmatar Service Station**
- **Convention Centers**
- **Trading Hubs**
- **Research Centers**

Each station type may offer different services and have different reprocessing efficiencies.

---

## Data Model Reference

### Key Tables

#### Item Hierarchy
- **invCategories**: Top-level categories (e.g., Blueprint, Material, Ship)
- **invGroups**: Item groups within categories (e.g., Battleship Blueprint)
- **invTypes**: Individual item types

#### Industry
- **industryBlueprints**: Blueprint metadata (max production limit)
- **invTypeMaterials**: Reprocessing materials (what items yield)

#### Planetary Interaction
- **planetSchematics**: PI schematic definitions (cycle time, name)
- **planetSchematicsTypeMap**: Schematic inputs/outputs (materials, quantities)
- **planetSchematicsPinMap**: Pin types required for schematics

#### Stations & POS
- **staStations**: Station information and services
- **invControlTowerResources**: POS fuel requirements

### Category IDs

| ID | Category |
|----|----------|
| 4 | Material |
| 6 | Ship |
| 9 | Blueprint |
| 41 | Planetary Industry (structures) |
| 42 | Planetary Resources (raw T0) |
| 43 | Planetary Commodities (processed T1-T4) |

### Important PI Category Notes

- **Category 41 (Planetary Industry)**: Contains structures and equipment (91 types)
  - Command Centers (8 types)
  - Extractors (40+ types)
  - Industry Facilities
  - Storage Facilities

- **Category 42 (Planetary Resources)**: Raw materials extracted from planets (15 types)
  - All T0 resources like Aqueous Liquids, Base Metals, etc.

- **Category 43 (Planetary Commodities)**: Processed materials (68 types)
  - These are the **schematics**, not the commodities themselves
  - Each schematic produces a commodity
  - Example: "Coolant" schematic produces Coolant commodity

### Query Examples

#### Get All PI Resources
```sql
SELECT t.typeID, t.typeName, t.volume
FROM evesde_invtypes t
JOIN evesde_invgroups g ON t.groupID = g.groupID
WHERE g.categoryID = 42 AND t.published = 1
ORDER BY t.typeName
```

#### Get Schematic Inputs/Outputs
```sql
SELECT
    ps.schematicName,
    ps.cycleTime,
    it.typeName,
    pstm.quantity,
    pstm.isInput
FROM evesde_planetschematicstypemap pstm
JOIN evesde_planetschematics ps ON pstm.schematicID = ps.schematicID
JOIN evesde_invtypes it ON pstm.typeID = it.typeID
WHERE ps.schematicID = 66
ORDER BY pstm.isInput DESC
```

#### Get Reprocessing Materials
```sql
SELECT
    it.typeName AS item,
    material.typeName AS material,
    itm.quantity
FROM evesde_invtypematerials itm
JOIN evesde_invtypes it ON itm.typeID = it.typeID
JOIN evesde_invtypes material ON itm.materialTypeID = material.typeID
WHERE itm.typeID = 23757  -- Vexor
```

#### Get POS Fuel Requirements
```sql
SELECT
    it.typeName AS fuel,
    ictr.purpose,
    ictr.quantity,
    ictr.minSecurityLevel
FROM evesde_invcontroltowerresources ictr
JOIN evesde_invtypes it ON ictr.resourceTypeID = it.typeID
WHERE ictr.controlTowerTypeID = 20062  -- Amarr Control Tower
ORDER BY ictr.purpose
```

---

## Summary

The EVE Online SDE provides comprehensive data for:

1. **Blueprints**: 5,072 blueprint types across 209 groups covering all manufacturing
2. **Planetary Interaction**: 15 raw resources, 68 schematics, 91 structure types
3. **Reprocessing**: Complete material breakdown for all items
4. **POS Fuel**: Detailed fuel requirements for all control towers
5. **Stations**: Service capabilities and reprocessing efficiency

This data enables:
- Industry calculators and profit analysis tools
- PI production chain optimizers
- Reprocessing yield calculators
- POS fuel cost trackers
- Market analysis tools for industry materials

The SDE is maintained by CCP and updated with each game expansion to reflect new items, balance changes, and mechanics updates.
