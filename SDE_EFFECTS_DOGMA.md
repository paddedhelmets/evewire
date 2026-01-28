# EVE Online SDE - Dogma Effect System Analysis

**Date:** 2026-01-27
**Database:** SQLite SDE (evesde_ prefix tables)
**Total Items Analyzed:** 51,134 types

---

## Executive Summary

The EVE Online Dogma (Dynamic Object Generic Management Architecture) effect system is the core mechanism that defines how items, modules, ships, and skills interact in the game. This analysis explores the structure of the Dogma system as represented in the Static Data Export (SDE).

### Key Statistics

| Metric | Count |
|--------|-------|
| Total Item Types | 51,134 |
| Total Effects | 3,354 |
| Total Type-Effect Relationships | 52,342 |
| Total Attribute Types | 2,822 |
| Total Type-Attribute Values | 612,816 |
| Total Attribute Categories | 37 |

---

## 1. Database Schema Overview

### Core Tables

#### `evesde_dgmeffects` - Effect Definitions
Defines all possible effects in the game.

**Key Fields:**
- `effectID` (INTEGER): Primary key
- `effectName` (VARCHAR): Effect name (NULL in current SDE - likely in translations)
- `effectCategory` (INTEGER): Categorizes effects (0-8)
- `isOffensive` (INTEGER): Flag for offensive effects (1=offensive)
- `isAssistance` (INTEGER): Flag for assistance effects (1=helpful)
- `durationAttributeID` (INTEGER): Links to attribute controlling duration
- `rangeAttributeID` (INTEGER): Links to attribute controlling range
- `falloffAttributeID` (INTEGER): Links to attribute controlling falloff
- `trackingSpeedAttributeID` (INTEGER): Links to tracking speed attribute
- `dischargeAttributeID` (INTEGER): Links to capacitor discharge
- `disallowAutoRepeat` (INTEGER): Flag to prevent auto-repeat
- `published` (INTEGER): Whether effect is published
- `displayName` (VARCHAR): Display name
- `isWarpSafe` (INTEGER): Can use while warping
- `modifierInfo` (TEXT): Additional modifier information

**Schema Notes:**
- All effect names are NULL in the current SDE (likely stored in translation tables)
- Effect category field exists but all values are NULL
- All 3,354 effects have NULL effectCategory

#### `evesde_dgmtypeeffects` - Type-Effect Relationships
Links item types to their effects.

**Key Fields:**
- `typeID` (INTEGER): Foreign key to invTypes
- `effectID` (INTEGER): Foreign key to dgmEffects
- `isDefault` (INTEGER): Whether this is the default effect for the item

**Composite Key:** (typeID, effectID)

#### `evesde_dgmattributetypes` - Attribute Definitions
Defines all possible attributes that items can have.

**Key Fields:**
- `attributeID` (INTEGER): Primary key
- `attributeName` (VARCHAR): Attribute name
- `defaultValue` (FLOAT): Default value for this attribute
- `published` (INTEGER): Whether attribute is published
- `displayName` (VARCHAR): Display name
- `stackable` (INTEGER): Whether multiple instances stack (1=yes)
- `highIsGood` (INTEGER): Whether higher values are better (1=yes)
- `categoryID` (INTEGER): Links to attribute categories (all NULL in current SDE)

#### `core_typeattribute` - Type-Attribute Values
Stores actual attribute values for each item type.

**Key Fields:**
- `typeID` (INTEGER): Foreign key to invTypes
- `attributeID` (INTEGER): Foreign key to dgmAttributeTypes
- `valueInt` (INTEGER): Integer value (if applicable)
- `valueFloat` (FLOAT): Float value (if applicable)
- `id` (INTEGER): Primary key

**Notes:**
- Uses `core_typeattribute` table instead of `evesde_dgmtypeattributes`
- 612,816 total type-attribute relationships
- Attributes can have either valueInt or valueFloat (not both)

#### `evesde_dgmattributecategories` - Attribute Categories
Categorizes attributes into logical groups.

**Key Fields:**
- `categoryID` (INTEGER): Primary key
- `categoryName` (VARCHAR): Category name
- `categoryDescription` (VARCHAR): Description

**37 Total Categories:**

| ID | Category | Description |
|----|----------|-------------|
| 1 | Fitting | Fitting capabilities of a ship |
| 2 | Shield | Shield attributes of ships |
| 3 | Armor | Armor attributes of ships |
| 4 | Structure | Structure attributes of ships |
| 5 | Capacitor | Capacitor attributes for ships |
| 6 | Targeting | Targeting attributes for ships |
| 7 | Miscellaneous | Misc. attributes |
| 8 | Required Skills | Skill requirements |
| 9 | NULL | Attributes not going into a category |
| 10 | Drones | All about drones |
| 12 | AI | AI configuration attributes |
| 17 | Speed and Travel | Velocity, speed attributes |
| 19 | Loot | Loot drop attributes |
| 20 | Remote Assistance | Remote transfers (shield, armor, structure) |
| 21 | EW - Target Painting | NPC Target Painting |
| 22 | EW - Energy Neutralizing | NPC Energy Neutralizing |
| 23 | EW - REM | NPC Remote ECM |
| 24 | EW - Sensor Dampening | NPC Sensor Dampening |
| 25 | EW - Target Jamming | NPC Target Jamming |
| 26 | EW - Tracking Disruption | NPC Tracking Disruption |
| 27 | EW - Warp Scrambling | NPC Warp Scrambling |
| 28 | EW - Webbing | NPC Stasis Webbing |
| 29 | Turrets | NPC Turret attributes |
| 30 | Missile | NPC Missile attributes |
| 31 | Graphics | NPC Graphic attributes |
| 32 | Entity Rewards | NPC Entity Rewards |
| 33 | Entity Extra | NPC Extra attributes |
| 34 | Fighter Abilities | Built-in fighter abilities |
| 36 | EW - Resistance | Resistance to EWar |
| 37 | Bonuses | Bonuses |
| 38 | Fighter Attributes | Fighter-related attributes |
| 39 | Superweapons | Doomsdays and Superweapons |
| 40 | Hangars & Bays | Hangar and bay attributes |
| 41 | On Death | Ship death attributes |
| 42 | Behavior Attributes | NPC Behavior |
| 51 | Mining | Mining-related attributes |
| 52 | Heat | Heat damage |

---

## 2. Effect Categories

### Theoretical Categories

Based on EVE Online knowledge and the schema, effects should fall into these categories:

| Category ID | Name | Description | Example |
|-------------|------|-------------|---------|
| 0 | Passive/None | Always-active passive effects | Ship bonus |
| 1 | Active | User-activated effects | Weapon fire |
| 2 | Overload | Overheating effects | Heat damage |
| 3 | Passive | Passive effects | Passive resist bonus |
| 4 | System | System-level effects | Module interaction |
| 5 | Online | Effects when module is online | Capacitor drain |
| 6 | Target | Targeted effects | Warp scramble |
| 7 | Area | Area-of-effect effects | Smartbomb |
| 8 | Warp | Warp-related effects | Warp speed |

**Current SDE Status:** All 3,354 effects have NULL effectCategory, suggesting either:
1. An older SDE version where categories weren't populated
2. Categories are determined dynamically by the client
3. Categories are stored in a different location

---

## 3. How Effects Work

### Effect Structure

An effect in EVE Online typically consists of:

1. **Definition** (in `dgmEffects`)
   - What the effect does
   - Whether it's offensive/defensive
   - Duration, range, tracking attributes

2. **Assignment** (in `dgmTypeEffects`)
   - Which items have which effects
   - Whether it's the default effect

3. **Modifiers** (in `modifierInfo` field)
   - Complex modifier expressions
   - References to expressions for calculation

4. **Attributes** (in `dgmAttributeTypes` + `dgmTypeAttributes`)
   - Numerical values that effects modify
   - Stackable vs non-stackable
   - High-is-good vs low-is-good

### Effect Flags

**isOffensive (1):**
- Marks effects that are considered hostile
- Triggers combat timers
- Example: Damage effects (Effect ID 16, 2179)

**isAssistance (1):**
- Marks effects that help other ships
- Affects aggression flags
- Example: Remote repair, shield transfer

**isDefault (1):**
- Marks the primary effect of an item
- Used when activating the module
- Most modules have exactly 1 default effect

---

## 4. Module Examples

### Example 1: 1MN Afterburner II (TypeID: 438)

**Effects (4 total):**
- Effect ID 13: Unknown (passive)
- Effect ID 16: Unknown (offensive)
- Effect ID 3175: Unknown
- Effect ID 6731: **[DEFAULT]** Primary activation effect

**Key Attributes:**
| Attribute ID | Attribute Name | Value | Description |
|--------------|----------------|-------|-------------|
| 6 | hp | 22.0 | Hit points |
| 9 | medSlots | 40.0 | *Appears to be corrupted data* |
| 20 | maxVelocity | 135.0 | Speed bonus |
| 30 | rechargeRate | 11.0 | Capacitor recharge |

**Analysis:**
- Afterburner has 4 effects (1 offensive, 1 default)
- Default effect (6731) is the main activation effect
- Modifies maxVelocity when activated
- Uses capacitor (rechargeRate)

### Example 2: 250mm Railgun I (TypeID: 570)

**Effects (5 total):**
- Effect ID 12: Unknown
- Effect ID 16: Unknown (offensive)
- Effect ID 34: **[DEFAULT]** Primary fire effect
- Effect ID 42: Unknown
- Effect ID 3001: Unknown

**Key Attributes:**
| Attribute ID | Attribute Name | Value |
|--------------|----------------|-------|
| 6 | hp | 7.0 |
| 30 | rechargeRate | 198.0 |
| 47 | speedBonus | 1.0 |
| 50 | structureDamageAmount | 38.0 |
| 51 | armorDamageAmount | 5825.0 |
| 54 | shieldDrainRange | 24000.0 |
| 128 | agilityMultiplier | 2.0 |

**Analysis:**
- Hybrid turret with 5 effects
- Default effect (34) handles firing
- Has separate damage amounts for structure/armor
- Optimal range (shieldDrainRange: 24000m)
- Affects ship agility when fitted

### Example 3: Magnetic Field Stabilizer I (TypeID: 9944)

**Effects (4 total):**
- Effect ID 11: Passive bonus
- Effect ID 16: Unknown
- Effect ID 93: Unknown
- Effect ID 96: Unknown

**Analysis:**
- Damage-modifying module
- No default effect (all passive)
- Increases hybrid turret damage/rate of fire

---

## 5. Ship Bonuses

### Vexor (TypeID: 626) - Gallente Cruiser

**Effects (4 total):**
- Effect ID 562: Ship bonus
- Effect ID 2179: Ship bonus (offensive)
- Effect ID 2188: Ship bonus
- Effect ID 2250: Ship bonus

**Attribute Distribution (82 total):**

The Vexor's attributes span multiple categories (though categoryID is NULL for all in current SDE):

**Key Ship Attributes:**
| Attribute ID | Attribute Name | Value | Description |
|--------------|----------------|-------|-------------|
| 3 | mass | 0.0 | *Should be non-zero* |
| 9 | medSlots | 2000.0 | *Appears corrupted* |
| 11 | powerLoad | 700.0 | Power grid usage |
| 12 | charge | 5.0 | Medium slots |
| 13 | powerToSpeed | 4.0 | Mass/agility factor |

**Ship Bonus System:**
- Ships have multiple effects (562, 2179, 2188, 2250)
- These effects apply bonuses to specific modules
- Bonuses are typically per-skill-level
- Role bonuses are always active

---

## 6. Common Effect Patterns

### Most Common Effects

| Rank | Effect ID | Usage Count | Type |
|------|-----------|-------------|------|
| 1 | 10 | 4,932 | Universal passive |
| 2 | 16 | 4,017 | Offensive/Damage |
| 3 | 569 | 1,860 | Module operation |
| 4 | 12 | 1,522 | Module operation |
| 5 | 11 | 1,325 | Passive bonus |
| 6 | 13 | 1,142 | Module operation |
| 7 | 2663 | 1,002 | Skill bonus |
| 8 | 42 | 683 | Turret operation |
| 9 | 308 | 651 | Drone operation |
| 10 | 310 | 650 | Drone operation |

**Analysis:**
- Effect ID 10 is the most common (likely a generic passive effect)
- Effect ID 16 appears on 4,017 items (likely generic damage)
- Module operation effects (11, 12, 13) are very common
- Drone-related effects (308, 310) appear frequently

---

## 7. Module Types by Group

### Published Module Distribution

| Group Name | Count | Category |
|------------|-------|----------|
| Hybrid Weapon | 223 | Turrets |
| Energy Weapon | 216 | Turrets |
| Armor Coating | 184 | Armor resist |
| Energized Armor Membrane | 169 | Armor resist |
| Projectile Weapon | 167 | Turrets |
| Armor Hardener | 148 | Active resist |
| Propulsion Module | 147 | Movement |
| Smart Bomb | 137 | AOE damage |
| Armor Repair Unit | 105 | Repair |
| Shield Hardener | 103 | Active resist |
| Shield Booster | 94 | Shield repair |
| Shield Resistance Amplifier | 84 | Passive resist |
| Rig Shield | 72 | Rigs |
| Rig Armor | 72 | Rigs |
| Rig Navigation | 64 | Rigs |

**Analysis:**
- Weapon systems are most numerous (Hybrid: 223, Energy: 216, Projectile: 167)
- Armor modules are very common (Coating, Energized, Hardener, Repair)
- Shield modules are less common than armor
- Rigs are well-distributed across categories

---

## 8. Attribute Types

### Total Attribute Types: 2,822

**Sample Key Attributes (first 20):**

| ID | Name | Default | Stackable | HighIsGood | Published | Category |
|----|------|---------|----------|------------|-----------|----------|
| 1 | isOnline | 0.00 | Yes | Good | No | NULL |
| 2 | damage | 0.00 | Yes | Bad | Yes | NULL |
| 3 | mass | 0.00 | No | Good | Yes | NULL |
| 4 | capacitorNeed | 0.00 | Yes | Bad | Yes | NULL |
| 5 | minRange | 0.00 | Yes | Good | No | NULL |
| 6 | hp | 0.00 | Yes | Good | Yes | NULL |
| 7 | powerOutput | 0.00 | Yes | Good | Yes | NULL |
| 8 | lowSlots | 0.00 | Yes | Good | Yes | NULL |
| 9 | medSlots | 0.00 | Yes | Good | Yes | NULL |
| 10 | hiSlots | 0.00 | Yes | Good | Yes | NULL |
| 11 | powerLoad | 0.00 | Yes | Good | Yes | NULL |
| 12 | charge | 0.00 | Yes | Good | No | NULL |
| 13 | powerToSpeed | 0.00 | Yes | Good | No | NULL |
| 14 | speedFactor | 1.00 | No | Good | Yes | NULL |
| 15 | warpFactor | 0.00 | Yes | Good | No | NULL |
| 16 | warpInhibitor | 0.00 | Yes | Good | No | NULL |
| 17 | power | 0.00 | Yes | Bad | Yes | NULL |
| 18 | maxArmor | 0.00 | Yes | Good | No | NULL |
| 19 | breakPoint | 0.00 | Yes | Good | No | NULL |
| 20 | maxVelocity | 0.00 | No | Good | Yes | NULL |

**Key Observations:**
- All attributes have NULL categoryID in current SDE
- Stackable flag determines if multiple items stack
- highIsGood flag indicates direction of bonus
- Published vs unpublished attributes for UI display

---

## 9. Effect-Attribute Relationship

### How Effects Modify Attributes

Effects in EVE Online modify attributes through:

1. **Direct Modification**
   - Effect applies a flat bonus/penalty
   - Example: +10% to maxVelocity

2. **Skill-Based Modification**
   - Effect magnitude scales with skill level
   - Example: +5% per level to hybrid damage

3. **Stacking Penalty**
   - Non-stackable effects are penalized when multiple modules are used
   - Stackable effects have no penalty

4. **Attribute References**
   - Effects reference attributes via IDs (durationAttributeID, rangeAttributeID, etc.)
   - Creates flexible system where same effect can have different values

### Duration and Range Attributes

Effects reference other attributes for their properties:

| Effect Property | Attribute Type | Example |
|-----------------|----------------|---------|
| Duration | durationAttributeID | 73 (10 seconds) |
| Range | rangeAttributeID | 54 (optimal range) |
| Falloff | falloffAttributeID | 158 (falloff) |
| Tracking | trackingSpeedAttributeID | 160 (tracking speed) |
| Capacitor | dischargeAttributeID | 50 (capacitor need) |

---

## 10. Data Quality Issues

### Observed Issues

1. **NULL Effect Names**
   - All 3,354 effects have NULL effectName
   - Likely stored in translation tables (trnTranslations)

2. **NULL Effect Categories**
   - All effects have NULL effectCategory
   - Categories may be client-side or in separate table

3. **NULL Attribute Categories**
   - All 2,822 attributes have NULL categoryID
   - Category table exists but not linked

4. **Corrupted Slot Data**
   - medSlots = 40.0 for modules (should be 0 or 1)
   - May be data import issue or different schema version

5. **Table Name Inconsistency**
   - Some tables use `evesde_` prefix
   - Others use no prefix (dgmTypeAttributes)
   - Type-attribute data in `core_typeattribute` not `evesde_dgmtypeattributes`

---

## 11. Summary of Dogma System

### Architecture

The EVE Dogma system is a **component-based effect system**:

1. **Items** (invTypes) are the base entities
2. **Effects** (dgmEffects) define behaviors
3. **Attributes** (dgmAttributeTypes) define properties
4. **Type-Effects** (dgmTypeEffects) link items to behaviors
5. **Type-Attributes** (dgmTypeAttributes) store actual values

### Key Principles

1. **Composability**
   - Items can have multiple effects
   - Effects can modify multiple attributes
   - Skills add additional effects

2. **Stacking**
   - Stackable effects: linear stacking
   - Non-stackable: exponential penalty
   - Determined by stackable flag

3. **Categories**
   - Attributes grouped by category
   - Effects grouped by category
   - UI organizes by category

4. **References**
   - Effects reference attributes for properties
   - Creates flexible, reusable system
   - Same effect can have different durations/ranges

---

## 12. Practical Applications

### For Fitting Tools

1. **Calculate Ship Stats**
   - Start with base ship attributes
   - Add module effects
   - Apply skill bonuses
   - Apply stacking penalties

2. **Determine Slot Usage**
   - Check lowSlots, medSlots, hiSlots attributes
   - Sum module powerLoad/power requirements
   - Verify CPU/power fit

3. **Calculate Damage**
   - Sum damage bonuses from skills
   - Apply module multipliers
   - Calculate optimal/falloff from attributes

### For Industry Tools

1. **Manufacturing Requirements**
   - Required skills (category 8)
   - Material requirements (invTypeMaterials)
   - Production time (industryActivity)

2. **Invention**
   - Base item probability
   - Skill modifiers
   - Decryptor bonuses

---

## 13. SQL Queries for Exploration

### Find All Effects for an Item

```sql
SELECT e.effectID, e.effectName, e.isOffensive, e.isAssistance,
       e.durationAttributeID, e.rangeAttributeID,
       te.isDefault
FROM evesde_dgmtypeeffects te
JOIN evesde_dgmeffects e ON te.effectID = e.effectID
WHERE te.typeID = 626  -- Vexor
ORDER BY te.effectID;
```

### Find All Attributes for an Item

```sql
SELECT ta.attributeID, at.attributeName,
       ta.valueInt, ta.valueFloat,
       at.stackable, at.highIsGood
FROM core_typeattribute ta
JOIN evesde_dgmattributetypes at ON ta.attributeID = at.attributeID
WHERE ta.typeID = 626  -- Vexor
ORDER BY ta.attributeID;
```

### Find Items with Specific Effect

```sql
SELECT t.typeID, t.typeName, g.groupName
FROM evesde_invtypes t
JOIN evesde_invgroups g ON t.groupID = g.groupID
JOIN evesde_dgmtypeeffects te ON t.typeID = te.typeID
WHERE te.effectID = 16  -- Damage effect
  AND t.published = 1
ORDER BY g.groupName, t.typeName;
```

### Find Modules by Slot Type

```sql
SELECT t.typeName, g.groupName
FROM evesde_invtypes t
JOIN evesde_invgroups g ON t.groupID = g.groupID
JOIN core_typeattribute ta ON t.typeID = ta.typeID
WHERE ta.attributeID = 12  -- lowSlots
  AND ta.valueInt > 0
  AND t.published = 1
ORDER BY g.groupName, t.typeName;
```

---

## 14. Recommendations

### For Developers

1. **Use Published Flag**
   - Filter by `published = 1` for player-visible items
   - Unpublished items may be test/NP content

2. **Handle NULL Values**
   - Many fields are NULL (names, categories)
   - Provide defaults or look up in translations

3. **Check Both Value Types**
   - Attributes can have valueInt OR valueFloat
   - Always check both, use non-NULL value

4. **Use Composite Keys**
   - Type-effects and type-attributes use composite keys
   - Django ORM doesn't handle these well - use raw SQL

5. **Consider Stacking**
   - Always check stackable flag
   - Apply stacking penalty for non-stackable effects

### For Further Research

1. **Translation Tables**
   - Explore `evesde_trntranslations` for effect/attribute names
   - May contain localized names

2. **Expression System**
   - Effects reference `preExpression` and `postExpression`
   - These IDs link to expression definitions
   - Critical for understanding effect calculations

3. **Modifier Information**
   - The `modifierInfo` field contains JSON/XML
   - Defines complex modification patterns
   - Key to understanding effect behavior

4. **Skill System**
   - Skills add effects via type-effects
   - Per-level bonuses use skill level in calculations
   - Need to map skill → bonus → affected attribute

---

## Conclusion

The EVE Online Dogma effect system is a sophisticated, data-driven architecture that enables:

- **Flexible item composition** through effect-attribute relationships
- **Complex bonus calculations** via skill and module stacking
- **Balanced gameplay** through stacking penalties and categories
- **Extensive content** with 51K+ items, 3K+ effects, and 2K+ attributes

The SDE provides the raw data, but understanding the relationships between effects, attributes, and item types requires:
1. Knowledge of EVE game mechanics
2. Understanding of the expression/ modifier system
3. Careful handling of NULL values and table inconsistencies
4. Awareness of stacking and bonus application rules

**File:** `/home/genie/gt/evewire/crew/delve/SDE_EFFECTS_DOGMA.md`
**Generated:** 2026-01-27
**Database:** EVE SDE (SQLite format)
