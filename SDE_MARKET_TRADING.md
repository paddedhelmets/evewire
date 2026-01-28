# EVE Online SDE: Market and Trading Systems Analysis

**Overview**: This document explores the EVE Online Static Data Export (SDE) to understand how the market, trading, and item systems are structured.

**Data Source**: Django models in `/home/genie/gt/evewire/crew/delve/core/sde/models.py`

**Analysis Date**: 2026-01-27

---

## Table of Contents

1. [Market Organization](#1-market-organization)
2. [Marketable vs Non-Marketable Items](#2-marketable-vs-non-marketable-items)
3. [Meta Groups (Quality Levels)](#3-meta-groups-quality-levels)
4. [Variant Relationships](#4-variant-relationships)
5. [Item Flags](#5-item-flags)
6. [Contraband System](#6-contraband-system)
7. [Groups and Categories](#7-groups-and-categories)

---

## 1. Market Organization

### Market Group Hierarchy

EVE's market is organized into a hierarchical tree structure with **2,092 market groups** organized across up to **5 levels of depth**.

#### Root-Level Market Categories (19 top-level groups)

| ID | Category | Subgroups |
|----|----------|-----------|
| 11 | Ammunition & Charges | 16 |
| 1396 | Apparel | 3 |
| 2 | Blueprints & Reactions | 10 |
| 157 | Drones | 7 |
| 24 | Implants & Boosters | 3 |
| 475 | Manufacture & Research | 3 |
| 3628 | Personalization | 2 |
| 1922 | Pilot's Services | 5 |
| 1320 | Planetary Infrastructure | 2 |
| 9 | Ship Equipment | 13 |
| 1954 | Ship SKINs | 12 |
| 955 | Ship and Module Modifications | 3 |
| 4 | Ships | 11 |
| 150 | Skills | 24 |
| 1659 | Special Edition Assets | 5 |
| 2202 | Structure Equipment | 6 |
| 2203 | Structure Modifications | 3 |
| 477 | Structures | 7 |
| 19 | Trade Goods | 24 |

### Market Groups with Most Items

The largest market groups by item count include apparel (SKINs, patterns, clothing) and ship variants:

1. **Trinkets and misc.** (315 items) - Special Edition Commodities
2. **Patterns** (261 items) - Design Elements
3. **Outerwear** (147 items) - Women's Clothing
4. **Gloss** (133 items) - Basic Nanocoatings
5. **Metallic Nanocoatings** (129 items) - Design Elements

---

## 2. Marketable vs Non-Marketable Items

### Overview

- **Total item types in SDE**: 51,134
- **Published item types**: 26,403
- **Marketable on market**: 18,883 (71.5%)
- **Non-marketable (contracts only)**: 7,520 (28.5%)

### What Makes an Item Marketable?

An item is marketable if:
1. `published = True` (it exists in the game)
2. `market_group_id` is not NULL (assigned to a market category)

### Marketable Items

Items that can be traded on the open market include:
- Ships and modules
- Ammunition and charges
- Blueprints (copies and originals)
- Trade goods
- Minerals and materials
- Skillbooks
- Most standard equipment

Examples:
- 'Abatis' 100mm Steel Plates
- 'Accord' Core Compensation
- 'Anguis' Ice Harvester Upgrade

### Non-Marketable Items

Items that can **only** be traded via contracts include:
- **Blueprints** (most original blueprints)
- **Augmented drone blueprints**
- **Special edition assets**
- **Limited-time offerings**
- Certain faction items

Examples:
- 'Abatis' 100mm Steel Plates I Blueprint
- 'Augmented' Acolyte Blueprint
- 'Augmented' Berserker Blueprint

---

## 3. Meta Groups (Quality Levels)

Meta groups define the **quality tier** of items in EVE. There are **13 meta groups** with varying item counts:

### Meta Group Distribution

| Meta ID | Name | Item Count | Description |
|---------|------|------------|-------------|
| 1 | Tech I | 2,626 | Standard baseline modules |
| 2 | Tech II | 2,198 | Advanced technology, higher performance |
| 3 | Storyline | 440 | Mission reward variants, intermediate quality |
| 4 | Faction | 2,838 | Navy and pirate faction items |
| 5 | Officer | 612 | Unique officer drops, highest quality |
| 6 | Deadspace | 362 | Deadspace complex drops |
| 14 | Tech III | 273 | Strategic cruiser subsystems |
| 15 | Abyssal | 260 | Abyssal deadspace modules |
| 17 | Premium | 1,388 | Apparel and cosmetic items |
| 19 | Limited Time | 1,461 | Time-limited offerings |
| 52 | Structure Faction | 122 | Faction structure rigs |
| 53 | Structure Tech II | 304 | Tech II structure rigs |
| 54 | Structure Tech I | 492 | Tech I structure rigs |

### Quality Hierarchy (lowest to highest)

1. **Tech I** - Base modules
2. **Storyline** - Slightly better than Tech I
3. **Tech II** - Significant improvement
4. **Faction** - Navy/pirate variants
5. **Deadspace** - High-end deadspace loot
6. **Officer** - Rare officer drops, best-in-slot

---

## 4. Variant Relationships

### Parent-Child System

The `invMetaTypes` table defines variant relationships through a **parent-child** system:

- **Parent type**: The base item (usually Tech I)
- **Child types**: Variants derived from the parent (Tech II, faction, etc.)

### Example: 1MN Afterburner Variants

**Base Item**: 1MN Afterburner I

**Variants**:
- Tech II: 1MN Afterburner II
- Tech I (named): 1MN Y-S8 Compact, 1MN Monopropellant Enduring
- Faction: Domination, Shadow Serpentis, Republic Fleet, Federation Navy, True Sansha
- Deadspace: Gistii A/B/C-Type, Coreli A/B/C-Type
- Storyline: 1MN Analog Booster
- Officer: Asine's Modified, Ramaku's Modified, Usaras' Modified

### Example: Shield Extender Variants

**Base Item**: Capital Shield Extender I

**Variants**:
- Tech I (restricted): Azeotropic Restrained, F-S9 Regolith Compact
- Tech II: Capital Shield Extender II
- Faction: CONCORD, True Sansha, Dread Guristas, Domination

### Key Relationships

1. **Tech I items** serve as the foundation
2. **Tech II items** require the Tech I as a prerequisite for manufacturing
3. **Faction/Deadspace/Officer** items are loot drops, not manufactured
4. **Meta level** affects manufacturing requirements and market pricing

---

## 5. Item Flags

### Overview

**141 flags** define where items are located and their state. Flags are used throughout EVE's asset system to track item positions.

### Flag Categories

#### Slot Flags (65 flags)
Range: IDs 11-171

- **LoSlot0-7** (IDs 11-18): Low slots
- **MedSlot0-7** (IDs 19-26): Medium slots
- **HiSlot0-7** (IDs 27-34): High slots
- **RigSlot0-7** (IDs 92-99): Rig slots
- **SubSystem0-7** (IDs 125-132): Tech III subsystem slots
- **ServiceSlot0-7** (IDs 159-166): Structure service slots

#### Bay/Hangar Flags (19 flags)
Range: IDs 4-186

Inventory locations for items:

| Flag ID | Name | Description |
|---------|------|-------------|
| 4 | Hangar | Corporate hangar |
| 5 | Cargo | Ship cargo hold |
| 87 | DroneBay | Drone bay |
| 90 | ShipHangar | Ship maintenance bay |
| 133 | SpecializedFuelBay | Fuel bay (capital ships) |
| 135 | SpecializedGasHold | Gas hold (industrial) |
| 137 | SpecializedSalvageHold | Salvage hold (Noctis) |
| 142 | SpecializedIndustrialShipHold | Industrial ship hold |
| 155 | FleetHangar | Fleet hangar |
| 158 | FighterBay | Fighter bay (carriers) |
| 172 | StructureFuel | Structure fuel bay |
| 176 | BoosterBay | Booster bay |
| 186 | CorpProjectsHangar | Corporation projects hangar |

#### State Flags (5 flags)

| Flag ID | Name | Description |
|---------|------|-------------|
| 63 | Locked | Item is locked down |
| 64 | Unlocked | Item is unlocked |
| 91 | ShipOffline | Module is offline |
| 144 | StructureActive | Structure is active |
| 157 | StructureOffline | Structure is offline |

#### Special Location Flags (24 flags)

| Flag ID | Name | Description |
|---------|------|-------------|
| 0 | None | No specific location |
| 1 | Wallet | ISK in wallet |
| 2 | Offices | Corporate office rental |
| 3 | Wardrobe | Character clothing |
| 6 | OfficeImpound | Impounded office |
| 7 | Skill | Skill in training |
| 8 | Reward | Mission reward |
| 36 | AssetSafety | Items under asset safety |
| 56 | Capsule | Capsule location |
| 57 | Pilot | Pilot (character) |
| 61 | Skill In Training | Currently training skill |
| 62 | CorpMarket | Corporation market |
| 86 | Bonus | Bonus items |
| 88 | Booster | Active booster |
| 89 | Implant | Installed implant |

---

## 6. Contraband System

### Overview

The contraband system defines **50 specific item-faction pairs** where certain items are illegal in specific faction territories. These restrictions apply to **14 different factions**.

### How It Works

When caught with contraband in restricted space:
- **Standing loss**: Faction standing penalty
- **Fine**: Percentage of item's estimated value
- **Confiscation**: Item removed at certain security levels
- **Attack**: Faction navy may attack in low security

### Common Contraband Items

#### Slaves (Illegal in Amarr Empire territories)
- **Faction 500001** (Amarr Empire): 0.2 standing loss, 500% fine, always confiscated
- **Faction 500002** (Amarr Consortium): 0.5 standing loss, 1000% fine
- **Faction 500004** (Ammatar Mandate): 0.3 standing loss, 800% fine
- **Faction 500005** (Khanid Kingdom): 0.2 standing loss, 500% fine

#### Vitoc (Illegal in Minmatar Republic territories)
- **Faction 500005** (Khanid Kingdom): 0.2 standing loss, 450% fine, confiscate at 0.4 sec
- **Faction 500017** (Thukker Tribe): 0.05 standing loss, 150% fine, confiscate at 0.5 sec

#### Radioactive Materials
- **Plutonium**: Illegal in Gallente Federation, Minmatar Republic
- **Toxic Waste**: Illegal in multiple factions
- Fines range from 110% to 300% of value
- Confiscation thresholds vary by faction (0.4 to 0.8 security status)

### Faction Enforcement

**Factions with most contraband restrictions**:
- Multiple items banned across empire factions
- Fines can exceed 1000% of item value
- Standing losses up to 0.5 per offense

---

## 7. Groups and Categories

### Overview

The **InvGroups** table organizes items within categories. There are **1,578 groups** that provide a secondary level of organization beyond market groups.

### Groups with Most Items

| Group | Category | Item Count | Marketable |
|-------|----------|------------|------------|
| Permanent SKIN | 91 | 5,780 | No |
| Ship Emblems | 2118 | 816 | No |
| Ship SKIN Design Element | 2118 | 770 | Yes |
| Miscellaneous | 17 | 659 | Yes |
| Rig Blueprint | 9 | 642 | Yes |
| Special Edition Commodities | 63 | 546 | Yes |
| Commodities | 17 | 423 | Yes |
| Mutaplasmids | 17 | 413 | Yes |
| Booster | 20 | 428 | Yes |
| Cyberimplant | 20 | 330 | Yes |

### Category Structure

Items are organized into categories (InvCategories), with groups within categories:

**Example: Ships Category (ID 6)**
- Assault Frigate (15 items)
- Attack Battlecruiser (5 items)
- Battleship (35 items)
- Black Ops (6 items)
- Blockade Runner (5 items)
- Capital Industrial Ship (1 item)
- Carrier (4 items)
- Combat Battlecruiser (21 items)

### Relationship to Market Groups

- **Category**: Broad classification (e.g., Ships, Modules, Charges)
- **Group**: Specific type within category (e.g., Assault Frigate, Shield Extender)
- **Market Group**: Browseable market hierarchy (may differ from technical categories)

---

## Key Findings Summary

### Market Structure

1. **Hierarchical Organization**: 5-level deep tree with 2,092 market groups
2. **Broad Coverage**: 71.5% of published items are marketable
3. **Category Separation**: Technical categories (InvCategories) vs. market browse structure (InvMarketGroups)

### Item Quality System

1. **13 Meta Groups**: From basic Tech I to rare Officer modules
2. **Parent-Child Variants**: Clear lineage from base items to variants
3. **Performance Scaling**: Quality levels correspond to performance improvements

### Trading Restrictions

1. **Contract-Only Items**: 28.5% of items bypass the market
2. **Contraband System**: 50 specific restrictions across 14 factions
3. **Penalties**: Standing loss, fines, confiscation, and attack

### Asset Management

1. **141 Flags**: Comprehensive location and state tracking
2. **Slot System**: Modular fitting with clear slot types
3. **Specialized Bays**: Industrial ships have purpose-specific holds

### Data Relationships

1. **InvTypes** → **InvGroups** → **InvCategories**: Technical classification
2. **InvTypes** → **InvMarketGroups** (self-referencing): Market browse structure
3. **InvTypes** → **InvMetaTypes** → **InvMetaGroups**: Quality hierarchy
4. **InvTypes** ← **InvContrabandTypes**: Faction-specific restrictions

---

## Database Schema Summary

### Key Tables

| Table | Records | Purpose |
|-------|---------|---------|
| invMarketGroups | 2,092 | Market browse hierarchy |
| invTypes | 51,134 | All item types |
| invGroups | 1,578 | Item groups within categories |
| invMetaGroups | 13 | Quality tier definitions |
| invMetaTypes | 13,376 | Variant relationships |
| invFlags | 141 | Item location/state flags |
| invContrabandTypes | 50 | Faction restrictions |

### Key Relationships

1. **market_group_id** (invTypes) → **market_group_id** (invMarketGroups)
2. **group_id** (invTypes) → **group_id** (invGroups)
3. **parent_group_id** (invMarketGroups) → **market_group_id** (invMarketGroups)
4. **parent_type_id** (invMetaTypes) → **type_id** (invTypes)
5. **meta_group_id** (invMetaTypes) → **meta_group_id** (invMetaGroups)

---

## Practical Applications

This analysis enables:

1. **Market Analysis**: Understanding item categorization for pricing and volume analysis
2. **Trading Tools**: Building applications that browse and compare items
3. **Asset Management**: Tracking item locations and states across characters/corporations
4. **Manufacturing**: Identifying parent-child relationships for production chains
5. **Risk Assessment**: Understanding contraband restrictions for hauling operations
6. **Fitting Tools**: Properly slotting modules based on flag system

---

**Generated**: 2026-01-27
**SDE Version**: Current EVE Online Static Data Export
**Analysis Tool**: Django ORM with Python shell
