# EVE Online SDE: Skills and Training System

**Date:** 2026-01-27
**Database:** EVE Static Data Export (SDE)
**Models:** `/home/genie/gt/evewire/crew/delve/core/sde/models.py`

---

## Executive Summary

The EVE Online skill system is built entirely on the item type system. Skills are items in **Category 16** (Skill), organized into 25 groups, with prerequisites defined through attribute relationships. The certificate and mastery systems provide structured skill progression pathways for ships and modules.

---

## 1. Skills as Items

### Core Concept
Skills are not a separate system - they are **items** in the EVE inventory system:

- **Category ID:** 16 (Skill)
- **Table:** `evesde_invtypes`
- **Published field:** Filters out test/internal skills

### Skill Structure
Every skill has:
- `type_id` - Unique identifier (primary key)
- `name` - Skill name (e.g., "Gunnery", "Caldari Frigate")
- `group_id` - Links to skill group (e.g., Gunnery, Spaceship Command)
- `description` - Skill description text
- `base_price` - ISK cost to purchase the skillbook
- `published` - Whether this skill is available to players
- `race_id` - Faction requirement (for some skills)

### Total Skills
- **Total skill groups:** 25
- **Total published skills:** ~580+ (varies by SDE version)

---

## 2. Skill Groups

Skills are organized into 25 groups by function:

| Group ID | Group Name | Skill Count | Description |
|----------|------------|-------------|-------------|
| 257 | Spaceship Command | 103 | All ship skills (frigates, cruisers, battleships, etc.) |
| 255 | Gunnery | 66 | Turret weapons and gunnery support |
| 1218 | Resource Processing | 55 | Mining, reprocessing, manufacturing efficiency |
| 270 | Science | 45 | Research, invention, science skills |
| 256 | Missiles | 31 | Missile launcher operation and specialization |
| 273 | Drones | 30 | Drone control and combat |
| 274 | Trade | 27 | Market, brokerage, contracting |
| 258 | Fleet Support | 20 | Command bursts, warfare links |
| 1240 | Subsystems | 20 | T3 cruiser subsystems |
| 272 | Electronic Systems | 19 | ECM, sensor dampeners, electronic warfare |
| 268 | Production | 18 | Manufacturing, industry |
| 4734 | Sequencing | 18 | Alpha clone skill sequencing |
| 1216 | Engineering | 16 | Capacitor, power grid, CPU |
| 275 | Navigation | 15 | Speed, agility, warp drive |
| 1209 | Shields | 14 | Shield tanking |
| 1210 | Armor | 14 | Armor tanking |
| 266 | Corporation Management | 13 | Corp management, POS |
| 278 | Social | 11 | NPC interactions |
| 269 | Rigging | 10 | Rig fitting and construction |
| 1220 | Neural Enhancement | 9 | Implant-related skills |
| 1213 | Targeting | 8 | Targeting range, signature resolution |
| 1217 | Scanning | 7 | D-scan, probes |
| 1545 | Structure Management | 7 | Citadel and engineering complex skills |
| 1241 | Planet Management | 5 | Planetary interaction |
| 505 | Fake Skills | 1 | Internal/testing |

---

## 3. Skill Attributes

Skills have several key attributes stored in `evesde_dgmattypeattributes`:

### Training Time Multipliers (Attributes 180-182)
These control how quickly a skill trains based on character attributes:

| Attribute ID | Attribute Name | Purpose |
|--------------|----------------|---------|
| 180 | `charismaSkillTrainingTimeMultiplierBonus` | Charisma modifier (stores attribute ID) |
| 181 | `intelligenceSkillTrainingTimeMultiplierBonus` | Intelligence modifier (stores attribute ID) |
| 182 | `memorySkillTrainingTimeMultiplierBonus` | Memory modifier **OR prerequisite skill ID** |

**Important:** Attribute 182 serves a dual purpose:
- For most skills: Stores the **prerequisite skill typeID**
- The value in these attributes is an **attribute ID** or **skill typeID**

### Skill Bonuses
Skills provide bonuses to character abilities. These are stored as type attributes:

**Example: Gunnery Skill**
```
barrageDmgMultiplier: 1
shipScanResistance: -2
```

**Example: Small Hybrid Turret**
```
barrageDmgMultiplier: 1
barrageFalloff: 1
maxActiveDroneBonus: 5
```

**Example: Caldari Frigate**
```
barrageDmgMultiplier: 2
barrageFalloff: 1
```

### Prerequisite Attributes
While not always present as explicit `requiredSkill1` attributes in this SDE version, prerequisites are encoded through the attribute system, primarily using attribute 182 to store the prerequisite skill's typeID.

---

## 4. Skill Prerequisites

### How Prerequisites Work

Prerequisites form a tree structure. A skill typically requires:
1. **A primary prerequisite skill** - stored in attribute 182
2. **Sometimes multiple prerequisites** - for advanced skills

### Example Prerequisite Chains

**Small Hybrid Turret:**
```
Small Hybrid Turret (ID: 3301)
  └─ Requires: Gunnery (ID: 3300)
       └─ Requires: None (base skill)
```

**Caldari Frigate:**
```
Caldari Frigate (ID: 3330)
  └─ Requires: Spaceship Command (ID: 3327)
       └─ Requires: None (base skill)
```

### Querying Prerequisites

```python
from core.sde.models import InvTypes
from django.db import connection

def get_skill_prerequisites(skill_id):
    """Get the prerequisite chain for a skill."""
    prereqs = []
    current_id = skill_id

    with connection.cursor() as cursor:
        while current_id:
            # Get the prerequisite from attribute 182
            cursor.execute(f"""
                SELECT valueInt FROM evesde_dgmattypeattributes
                WHERE typeID = {current_id} AND attributeID = 182
            """)
            result = cursor.fetchone()

            if result and result[0]:
                prereq_skill = InvTypes.objects.get(type_id=result[0])
                prereqs.append(prereq_skill)
                current_id = result[0]
            else:
                break

    return prereqs
```

---

## 5. Character Attributes and Training Time

### Primary Attributes
The five character attributes that affect training speed:

| Attribute ID | Attribute Name | Description |
|--------------|----------------|-------------|
| 164 | Perception | Combat, ship operation (turrets, missiles) |
| 165 | Willpower | Combat, ship operation |
| 166 | Charisma | Trade, social, corporation management |
| 167 | Intelligence | Science, industry, electronics |
| 168 | Memory | Industry, drones, learning |

### Training Time Calculation

Training time for a skill level is calculated as:

```
Time = (Skill_Rank × 2^(Level-1) × Primary_Attribute + Secondary_Attribute) / Constant
```

Where:
- **Skill Rank** is the `skillTimeConstant` (attribute 224) - not always present in this SDE
- **Level** is the skill level being trained (1-5)
- **Primary_Attribute** is the character's primary attribute score
- **Secondary_Attribute** is the character's secondary attribute score

**Note:** The SDE explored shows training time multipliers stored in attributes 180-182, but the exact formula requires character attribute data from the ESI API, not the SDE.

---

## 6. Certificate System

### Overview
Certificates represent **validated skill proficiency** in specific areas. They provide:
- Structured skill progression paths
- Proof of competence to corporations
- Prerequisite checks for ship mastery

### Certificate Tables

**`evesde_certcerts`** - Certificate definitions
- `certID` - Primary key
- `name` - Certificate name (e.g., "Small Hybrid Turret")
- `description` - What the certificate represents
- `groupID` - Groups certificates by category

**`evesde_certskills`** - Certificate skill requirements
- `certID` - Foreign key to certificate
- `skillID` - Required skill typeID
- `skillLevel` - Required skill level (1-5)
- `certLevelInt` - Certificate level (0-4)
- `certLevelText` - Text representation ("Basic", "Standard", etc.)

### Certificate Levels
Certificates have 5 levels (0-4):
- **Level 0:** Basic/Entry
- **Level 1:** Improved
- **Level 2:** Advanced
- **Level 3:** Elite
- **Level 4:** Master

### Example Certificate Structure

**Certificate: Small Hybrid Turret**

```
Level 0 (Basic):
  - Gunnery Level 3
  - Small Hybrid Turret Level 1
  - Rapid Firing Level 1
  - Sharpshooter Level 1

Level 1 (Improved):
  - Gunnery Level 4
  - Small Hybrid Turret Level 3
  - Rapid Firing Level 3
  - Sharpshooter Level 3

Level 2 (Advanced):
  - Gunnery Level 4
  - Small Hybrid Turret Level 4
  - Rapid Firing Level 4
  - Sharpshooter Level 4

Level 3 (Elite):
  - Gunnery Level 5
  - Small Hybrid Turret Level 5
  - Rapid Firing Level 4
  - Sharpshooter Level 4

Level 4 (Master):
  - Gunnery Level 5
  - Small Hybrid Turret Level 5
  - Rapid Firing Level 5
  - Sharpshooter Level 5
```

### Certificate Statistics
- **Total certificates:** 136
- **Total skill requirement entries:** 4,430
- **Average requirements per certificate:** ~32.5

### Querying Certificates

```python
from core.sde.models import CertCerts, CertSkills, InvTypes

def get_certificate_requirements(cert_id):
    """Get all skill requirements for a certificate."""
    cert = CertCerts.objects.get(cert_id=cert_id)
    requirements = []

    # Group by certificate level
    for level in range(5):  # 0-4
        level_reqs = CertSkills.objects.filter(
            cert_id=cert_id,
            cert_level_int=level
        )

        level_skills = []
        for req in level_reqs:
            skill = InvTypes.objects.get(type_id=req.skill_id)
            level_skills.append({
                'skill': skill.name,
                'level': req.skill_level
            })

        if level_skills:
            requirements.append({
                'level': level,
                'skills': level_skills
            })

    return {
        'certificate': cert.name,
        'requirements': requirements
    }
```

---

## 7. Mastery System

### Overview
The mastery system maps certificates to specific ships, showing recommended skill proficiency for flying that ship effectively.

### Mastery Tables

**`evesde_certmasteries`** - Mastery level definitions
- `typeID` - Ship typeID (foreign key to invTypes)
- `masteryLevel` - Mastery level (0-4)
- `certID` - Required certificate (foreign key to certCerts)

### Mastery Levels
Each ship has 5 mastery levels:
- **Mastery 0:** Basic capability
- **Mastery 1:** Standard operation
- **Mastery 2:** Improved effectiveness
- **Mastery 3:** Advanced capability
- **Mastery 4:** Full mastery

### Mastery Statistics
- **Ships with mastery data:** 468
- **Total mastery entries:** ~17,429
- **Average certificates per ship:** ~37 per mastery level

### Example Ship Mastery

**Abaddon (Amarr Battleship)**

```
Mastery 0:
  - Core Spaceship Operation
  - Large Energy Turret
  - Tackling
  - Medium Drones
  - Battleship Navigation
  - Core Weapon Fitting
  - Armor Tanking
  - Radar Target Management

Mastery 1:
  - Core Spaceship Operation (higher level)
  - Large Energy Turret (higher level)
  - ... (same certificates, higher requirements)

Mastery 2-4:
  - Progressive increases in certificate levels
```

### Querying Mastery

```python
from core.sde.models import CertMasteries, CertCerts, InvTypes

def get_ship_mastery(ship_type_id):
    """Get all mastery levels for a ship."""
    mastery_data = {}

    masteries = CertMasteries.objects.filter(
        type_id=ship_type_id
    ).order_by('mastery_level')

    for mastery in masteries:
        cert = CertCerts.objects.get(cert_id=mastery.cert_id)
        if mastery.mastery_level not in mastery_data:
            mastery_data[mastery.mastery_level] = []
        mastery_data[mastery.mastery_level].append(cert.name)

    return mastery_data
```

---

## 8. Database Schema Reference

### Key Tables

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `evesde_invcategories` | Item categories | categoryID=16 for Skills |
| `evesde_invgroups` | Skill groups | groupID, categoryID |
| `evesde_invtypes` | Skill items | typeID, name, groupID, published |
| `evesde_dgmattributetypes` | Attribute definitions | attributeID, attributeName |
| `evesde_dgmattypeattributes` | Skill attribute values | typeID, attributeID, valueInt/valueFloat |
| `evesde_certcerts` | Certificate definitions | certID, name, groupID |
| `evesde_certskills` | Certificate requirements | certID, skillID, skillLevel, certLevelInt |
| `evesde_certmasteries` | Ship mastery | typeID, masteryLevel, certID |

### Important Attribute IDs

| ID | Attribute Name | Usage |
|----|----------------|-------|
| 139 | primaryAttribute | Primary training attribute (not always present) |
| 140 | secondaryAttribute | Secondary training attribute (not always present) |
| 141-143 | requiredSkill1-3 | Prerequisite skill IDs (not always present) |
| 180 | charismaSkillTrainingTimeMultiplierBonus | Training modifier |
| 181 | intelligenceSkillTrainingTimeMultiplierBonus | Training modifier |
| 182 | memorySkillTrainingTimeMultiplierBonus | Training modifier OR prerequisite |
| 224 | skillTimeConstant | Skill rank (not always present) |
| 226-228 | requiredSkill1Level-3Level | Prerequisite levels (not always present) |

---

## 9. Visualization Opportunities

### Skill Tree Visualization

```python
def build_skill_tree(skill_id):
    """
    Build a tree structure of a skill and its prerequisites.
    Returns a nested dictionary suitable for graph visualization.
    """
    from core.sde.models import InvTypes
    from django.db import connection

    def get_prereqs(type_id):
        cursor = connection.cursor()
        cursor.execute(f"""
            SELECT valueInt FROM evesde_dgmattypeattributes
            WHERE typeID = {type_id} AND attributeID = 182
        """)
        result = cursor.fetchone()
        return result[0] if result and result[0] else None

    def build_node(type_id, depth=0):
        if depth > 10:  # Prevent infinite loops
            return None

        skill = InvTypes.objects.get(type_id=type_id)
        prereq_id = get_prereqs(type_id)

        node = {
            'id': type_id,
            'name': skill.name,
            'group': skill.group.group_name,
            'prerequisite': build_node(prereq_id, depth + 1) if prereq_id else None
        }

        return node

    return build_node(skill_id)
```

### Certificate Progress Visualization

```python
def get_certificate_progress(character_skills, cert_id):
    """
    Calculate progress toward a certificate based on character skills.
    character_skills: dict of {skill_id: level}
    """
    from core.sde.models import CertSkills

    requirements = CertSkills.objects.filter(cert_id=cert_id).order_by('cert_level_int')

    progress = {
        'level_0': {'required': 0, 'have': 0},
        'level_1': {'required': 0, 'have': 0},
        'level_2': {'required': 0, 'have': 0},
        'level_3': {'required': 0, 'have': 0},
        'level_4': {'required': 0, 'have': 0},
    }

    for req in requirements:
        level_key = f'level_{req.cert_level_int}'
        progress[level_key]['required'] += 1

        if character_skills.get(req.skill_id, 0) >= req.skill_level:
            progress[level_key]['have'] += 1

    return progress
```

### Mastery Visualization

```python
def get_ship_mastery_progress(ship_type_id, character_skills):
    """
    Calculate mastery progress for a ship.
    Returns completion percentage for each mastery level.
    """
    from core.sde.models import CertMasteries, CertSkills

    masteries = CertMasteries.objects.filter(type_id=ship_type_id)
    progress = {}

    for mastery in masteries:
        level_key = f'mastery_{mastery.mastery_level}'
        if level_key not in progress:
            progress[level_key] = {'total': 0, 'complete': 0}

        # Get all certificate requirements
        cert_reqs = CertSkills.objects.filter(cert_id=mastery.cert_id)

        for req in cert_reqs:
            progress[level_key]['total'] += 1
            if character_skills.get(req.skill_id, 0) >= req.skill_level:
                progress[level_key]['complete'] += 1

    # Calculate percentages
    for level in progress:
        total = progress[level]['total']
        complete = progress[level]['complete']
        progress[level]['percent'] = (complete / total * 100) if total > 0 else 0

    return progress
```

---

## 10. Query Examples

### Find All Skills in a Group

```python
from core.sde.models import InvTypes, InvGroups

gunnery_group = InvGroups.objects.get(group_name='Gunnery')
skills = InvTypes.objects.filter(
    group=gunnery_group,
    published=True
).order_by('name')

for skill in skills:
    print(f"{skill.name} (ID: {skill.type_id})")
```

### Get Skill Prerequisite Chain

```python
def get_prereq_chain(skill_name):
    from core.sde.models import InvTypes
    from django.db import connection

    skill = InvTypes.objects.get(name=skill_name)
    chain = [skill.name]
    current_id = skill.type_id

    with connection.cursor() as cursor:
        while current_id:
            cursor.execute(f"""
                SELECT valueInt FROM evesde_dgmattypeattributes
                WHERE typeID = {current_id} AND attributeID = 182
            """)
            result = cursor.fetchone()

            if result and result[0]:
                prereq = InvTypes.objects.get(type_id=result[0])
                chain.append(prereq.name)
                current_id = result[0]
            else:
                break

    return " → ".join(reversed(chain))

# Example
print(get_prereq_chain("Small Hybrid Turret"))
# Output: Gunnery → Small Hybrid Turret
```

### Find Ships Requiring a Certificate

```python
from core.sde.models import CertMasteries, InvTypes

def get_ships_for_certificate(cert_id):
    masteries = CertMasteries.objects.filter(cert_id=cert_id)
    ships = []

    for mastery in masteries:
        ship = InvTypes.objects.get(type_id=mastery.type_id)
        ships.append({
            'ship': ship.name,
            'mastery_level': mastery.mastery_level
        })

    return ships
```

### Get All Certificates for a Skill Group

```python
from core.sde.models import CertCerts, InvGroups

def get_certificates_by_group(group_name):
    gunnery_group = InvGroups.objects.get(group_name=group_name)

    # Assuming certificates use similar group IDs
    certs = CertCerts.objects.filter(
        group_id=gunnery_group.group_id
    ).order_by('name')

    return certs
```

---

## 11. Key Insights

### Skill Design Patterns

1. **Hierarchical Structure:** Skills form trees with base skills (no prerequisites) and advanced skills (require base skills)

2. **Specialization:** Most skill groups have:
   - 1-2 base skills (e.g., "Gunnery", "Spaceship Command")
   - Multiple specialized skills (e.g., "Small Hybrid Turret", "Caldari Frigate")
   - Advanced specializations (e.g., "Large Hybrid Turret", "Marauders")

3. **Cross-Group Dependencies:** Skills often require skills from other groups:
   - Ship skills require "Spaceship Command"
   - Weapon skills require weapon group base skills
   - T2 ships require racial frigate/cruiser skills

### Certificate Design Patterns

1. **Progressive Difficulty:** Each certificate level requires higher skill levels
2. **Multiple Skills:** Most certificates require 3-5 different skills
3. **Specialization:** Certificates focus on specific areas (weapon types, tank types, ship classes)

### Mastery System Patterns

1. **Core Certificates:** All ships require "Core" certificates (fitting, tanking, navigation)
2. **Role-Specific:** Certificates match ship roles (turrets, missiles, drones)
3. **Progressive Mastery:** Higher levels require higher certificate levels

---

## 12. Recommendations for Visualization

### 1. Skill Tree Graph
- **Type:** Directed acyclic graph (DAG)
- **Nodes:** Skills
- **Edges:** Prerequisite relationships
- **Color coding:** By skill group
- **Interactive:** Click to show details

### 2. Certificate Progress Bars
- **Type:** Stacked bar charts
- **Segments:** Skill requirements
- **Progress:** Character's current levels
- **Grouping:** By certificate level (0-4)

### 3. Ship Mastery Dashboard
- **Type:** Grid/matrix view
- **Rows:** Ships
- **Columns:** Mastery levels (0-4)
- **Cells:** Progress percentage
- **Color coding:** Red (0%) → Green (100%)

### 4. Skill Plan Calculator
- **Input:** Target skills/certificates/mastery
- **Output:** Training queue with times
- **Features:** Prerequisite auto-inclusion, attribute optimization

---

## 13. Data Quality Notes

### Inconsistencies Found
1. **Missing Attributes:** Some expected attributes (skillTimeConstant, primaryAttribute) are not present in this SDE version
2. **Dual-Purpose Attributes:** Attribute 182 serves as both training modifier AND prerequisite storage
3. **Implicit Prerequisites:** Some prerequisites may be encoded differently than expected

### Recommendations
1. **Cross-Reference:** Use ESI API for real-time skill data
2. **Validation:** Check prerequisite chains for completeness
3. **Caching:** Certificate/mastery data changes rarely, cache aggressively

---

## 14. References

### Database Location
- **SDE Database:** `~/data/evewire/evewire_app.sqlite3`
- **Django Models:** `/home/genie/gt/evewire/crew/delve/core/sde/models.py`

### EVE Online References
- [EVE University Skill System](https://wiki.eveuniversity.org/Skills)
- [EVE Online Skill Guide](https://www.eveonline.com/news/view/skills-to-success)
- [Fuzzwork EVE SDE](https://www.fuzzwork.co.uk/dump/)

### External APIs
- **ESI (EVE Swagger Interface):** https://esi.evetech.net/
- **Skills Endpoint:** `/v4/characters/{character_id}/skills/`
- **Skillqueue Endpoint:** `/v2/characters/{character_id}/skillqueue/`

---

## Appendix A: Complete Skill Group List

```
ID     Group Name                    Skills
-----  ----------------------------  ------
257    Spaceship Command             103
255    Gunnery                        66
1218   Resource Processing            55
270    Science                        45
256    Missiles                       31
273    Drones                         30
274    Trade                          27
258    Fleet Support                  20
1240   Subsystems                      20
272    Electronic Systems             19
268    Production                     18
4734   Sequencing                     18
1216   Engineering                    16
275    Navigation                     15
1209   Shields                        14
1210   Armor                          14
266    Corporation Management         13
278    Social                          11
269    Rigging                        10
1220   Neural Enhancement              9
1213   Targeting                       8
1217   Scanning                        7
1545   Structure Management            7
1241   Planet Management               5
505    Fake Skills                     1
```

---

## Appendix B: Attribute ID Reference

### Training-Related Attributes
```
ID   Name
---  -------------------------------------------------
139  primaryAttribute
140  secondaryAttribute
141  requiredSkill1
142  requiredSkill2
143  requiredSkill3
180  charismaSkillTrainingTimeMultiplierBonus
181  intelligenceSkillTrainingTimeMultiplierBonus
182  memorySkillTrainingTimeMultiplierBonus (also prerequisites)
224  skillTimeConstant
226  requiredSkill1Level
227  requiredSkill2Level
228  requiredSkill3Level
229  skillLevel
1100 requiredSkill4
1101 requiredSkill4Level
1102 requiredSkill5Level
1103 requiredSkill6Level
1104 requiredSkill5
1105 requiredSkill6
```

### Bonus Attribute Examples
```
ID   Name
---  -------------------------------------------------
275  barrageDmgMultiplier
277  barrageFalloff
292  maxActiveDroneBonus
280  implantness
440  shipScanFalloff
441  shipScanResistance
```

---

**End of Report**
