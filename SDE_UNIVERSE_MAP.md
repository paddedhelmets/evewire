# New Eden Universe Geography - SDE Exploration Report

This report explores the EVE Online Static Data Export (SDE) to understand how the New Eden universe is structured, organized, and can be visualized.

## Table of Contents

1. [Universe Scale](#universe-scale)
2. [Spatial Hierarchy](#spatial-hierarchy)
3. [Security Classification](#security-classification)
4. [Faction Control](#faction-control)
5. [Celestial Objects](#celestial-objects)
6. [Notable Locations](#notable-locations)
7. [Coordinate System](#coordinate-system)
8. [Data Access Patterns](#data-access-patterns)

---

## Universe Scale

New Eden is a vast universe containing:

- **113 Regions** - The largest territorial divisions
- **1,175 Constellations** - Sub-regions containing groups of systems
- **8,437 Solar Systems** - Individual star systems players can visit
- **~482,596 Celestial Objects** - All objects within systems (planets, moons, gates, stations, etc.)
- **5,154 Stations** - Player-accessible stations (note: this is NPC stations only; player structures are separate)
- **45 Landmarks** - Special points of interest with lore descriptions

### Key Insight
The universe is divided into **known space** (~5,342 systems) and **wormhole space** (~3,095 systems), with wormhole space being approximately 37% of all systems.

---

## Spatial Hierarchy

The universe follows a strict three-level hierarchy:

```
Region (113 total)
  └─ Constellation (1,175 total, ~10 per region)
      └─ Solar System (8,437 total, ~7 per constellation)
          └─ Celestial Objects (~57 per system average)
```

### Region Level
- Largest organizational unit
- Examples: The Forge, Domain, Metropolis, Delve
- Can span multiple security levels (though most are homogeneous)
- Some regions are faction-controlled, others are unowned (nullsec)

### Constellation Level
- Intermediate grouping between regions and systems
- Contains ~3-20 solar systems (average ~7)
- Used for localization and some game mechanics

### Solar System Level
- The fundamental playable unit
- Contains celestial objects: stars, planets, moons, stargates, stations, belts
- Has security status, coordinates, and faction affiliation
- Connected to other systems via stargates

---

## Security Classification

Security status in EVE ranges from **1.0 (safest)** to **-1.0 (most dangerous)**:

### High Security (Highsec) - 1,194 systems (14.1%)
- **Range:** 0.45 to 1.0
- **Characteristics:** CONCORD protection, NPC stations, faction-controlled
- **Major regions:** The Forge, Domain, Metropolis, Sinq Laison, Heimatar
- **Sample system:** Yuzier (0.91 security, Derelik region)
- **Economic activity:** Trade hubs, mission running, industry

### Low Security (Lowsec) - 674 systems (8.0%)
- **Range:** 0.05 to 0.45
- **Characteristics:** Limited CONCORD response, faction warfare, increased rewards
- **Major regions:** Black Rise, Derelik, Molden Heath (partial)
- **Sample system:** Asabona (0.32 security, Derelik region)
- **Economic activity:** Faction warfare, piracy, exploration

### Null Security (Nullsec) - 6,569 systems (77.9%)
- **Range:** 0.0 to 0.05
- **Characteristics:** No CONCORD, player-owned space, highest rewards/risk
- **Types:**
  - NPC Nullsec: Owned by pirate factions (e.g., Guristas, Angel Cartel)
  - Sovereign Nullsec: Player-owned space with territorial control
- **Sample system:** Egbinger (0.03 security, Molden Heath region)
- **Major regions:** Delve, Fountain, Branch, Tenal, Period Basis
- **Economic activity:** Sovereignty warfare, capital ship operations, high-end industry

### Triglavian Space (Pochven) - 49 systems
- **Range:** -0.90 to -0.95
- **Characteristics:** Invaded by Triglavian faction, unique mechanics
- **Region:** Pochven (plus systems scattered across other regions)
- **Sample system:** Kuharah (-1.00 security, Pochven region)
- **Economic activity:** Triglavian storyline, abyssal traces

### Wormhole Space - 3,095 systems (36.7%)
- **Range:** -1.0 (exact value)
- **Characteristics:** No stargates (only wormholes), no local chat, sleeper NPCs
- **Region naming:** Uses codes like A-R00001, B-R00002, C-R00003, etc.
- **System naming:** Uses J-code naming (e.g., J123456)
- **Classes:** C1-C6 (difficulty and mass limits)
- **Economic activity:** Sleepers, gas harvesting, wormhole daytripping

---

## Faction Control

Four major empires control highsec space:

1. **Caldari State** - The Forge, Lonetrek, The Citadel, Black Rise
2. **Minmatar Republic** - Heimatar, Metropolis, Molden Heath
3. **Amarr Empire** - Domain, Tash-Murkon, Khanid, Aridia
4. **Gallente Federation** - Sinq Laison, Essence, Verge Vendor, Placid

### Faction Influence
- Faction ID is stored on individual **solar systems**, not regions
- A region may contain systems from multiple factions (rare)
- Most highsec regions are dominated by one faction
- Nullsec and wormhole systems have `factionID = None`

### Accessing Faction Data
```python
from core.sde.models import MapSolarSystems, ChrFactions

# Systems controlled by a specific faction
caldari_systems = MapSolarSystems.objects.filter(faction_id=500001)  # Caldari State

# Get faction info
faction = ChrFactions.objects.get(faction_id=500001)
print(faction.faction_name)  # "Caldari State"
```

---

## Celestial Objects

Each solar system contains numerous celestial objects, stored in `mapDenormalize`:

### Object Distribution (Universe-wide)

| Group ID | Count | Object Type |
|----------|-------|-------------|
| 8 | 342,170 | Moon |
| 7 | 67,961 | Planet |
| 9 | 40,928 | Asteroid Belt |
| 10 | 13,776 | Stargate (Class 1) |
| 5 | 8,437 | Station (NPC) |
| 6 | 8,036 | Star |
| 4 | 1,175 | Stargate (general) |
| 151 | ~200 | Wormhole |
| 600+ | varies | Player structures (citadels, engineering complexes) |

### Key Object Types

**Stars (Group ID 6, 152)**
- Center of each solar system
- Various types: standard stars, red giants, white dwarfs, neutron stars, black holes
- Wormhole systems may have special star types

**Planets (Group ID 7)**
- Orbit stars
- Can be colonized for Planetary Industry
- Range from gas giants to temperate worlds

**Moons (Group ID 8)**
- The most numerous object type (~342k)
- Can harbor moon minerals for extraction
- Some can be anchored with structures

**Stargates (Group ID 4, 10)**
- Connect systems to form the universe topology
- Each system has 1-6+ gates depending on connectivity
- Group ID 4 = legacy stargate entries
- Group ID 10 = Class 1 stargates (primary)

**Stations (Group ID 5)**
- NPC stations where players can dock
- ~5,154 total in the SDE
- Player structures (citadels, etc.) are NOT in this table

**Asteroid Belts (Group ID 9)**
- ~40,928 belts across all systems
- Source of ore for mining
- Some systems have ice belts instead

**Wormholes (Group ID 151, 450)**
- Dynamic connections that appear/disappear
- Connect known space to wormhole space or vice versa
- Not permanent (unlike stargates)

---

## Notable Locations

### Major Trade Hubs

Top systems by NPC station count:

| System | Stations | Security | Region |
|--------|----------|----------|--------|
| Nonni | 22 | 0.51 | Lonetrek |
| Amamake | 20 | 0.44 | Heimatar |
| Penirgman | 19 | 0.86 | Domain |
| Hilaban | 18 | 0.89 | Tash-Murkon |
| Kusomonmon | 17 | 0.85 | The Citadel |
| Oursulaert | 16 | 0.89 | Essence |
| **Jita** | 15 | 0.95 | The Forge |
| Aulbres | 14 | 0.14 | Placid |

**Note:** Jita has only 15 NPC stations but is the game's primary trade hub due to player activity and market volume.

### Jita - The Premier Trade Hub

```
System: Jita
Region: The Forge
Constellation: Kimotoro
Security: 0.945913
Faction: None (historically Caldari)
Coordinates: X=-1.29e+17, Y=6.08e+16, Z=1.17e+17

Celestial Objects: 49
  - 33 Moons
  - 8 Planets
  - 7 Stargates
  - 1 Star
```

Jita is centrally located in The Forge region with excellent connectivity to other highsec regions, making it the natural trading hub of New Eden.

### Landmarks

The SDE includes 45 landmark locations with lore descriptions. These are special points of interest that add flavor to the universe. Landmarks include:

- Historical battle sites
- Mysterious anomalies
- Settlement outposts
- Pirate territories

Example landmark: **09-4XW** - A settler outpost in Guristas territory, embroiled in conflict with local racketeers.

### Famous Systems

- **Jita** - Primary trade hub
- **Amarr** - Amarr Empire capital
- **Dodixie** - Gallente trade hub
- **Rens** - Minmatar trade hub
- **Hek** - Alternative Minmatar hub
- **Oursulaert** - Gallente Federal hub

---

## Coordinate System

### 3D Space Positioning

Every solar system has X, Y, Z coordinates in meters:

```
Sample System: Tanoo
  X: -8.85e+16 meters (-88.5 quadrillion meters)
  Y: 4.24e+16 meters
  Z: -4.45e+16 meters
```

### Coordinate Scale

- **Units:** Meters
- **Range:** Approximately 1×10^17 to 1×10^18 meters
- **Origin:** (0, 0, 0) is the center of the universe
- **Spread:** Systems span roughly 100 light-years in each direction

### Visualization Implications

1. **3D Rendering:** The coordinate system supports full 3D visualization
2. **Distance Calculation:** Euclidean distance between systems:
   ```python
   import math
   distance = math.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)
   ```
3. **Regional Clustering:** Systems in the same region are spatially clustered
4. **Jump Navigation:** Coordinates help with jump bridge and capital routing

### Coordinate Display Tips

- Use scientific notation: `1.29e+17` instead of `129000000000000000`
- Normalize by dividing by 1e15 for "light-year-ish" units
- Consider logarithmic scaling for visualization

---

## Data Access Patterns

### Basic Queries

#### Count objects by type
```python
from core.sde.models import MapSolarSystems, MapDenormalize
from django.db.models import Count

# Systems per region
systems_per_region = MapSolarSystems.objects.values(
    'region__region_name'
).annotate(count=Count('system_id')).order_by('-count')

# Celestial objects in a system
celestials = MapDenormalize.objects.filter(solar_system_id=system_id)
```

#### Security classification
```python
# Highsec systems
hisec = MapSolarSystems.objects.filter(security__gte=0.45)

# Lowsec systems
lowsec = MapSolarSystems.objects.filter(security__gte=0.05, security__lt=0.45)

# Nullsec systems
nullsec = MapSolarSystems.objects.filter(security__gte=0, security__lt=0.05)

# Wormhole systems
wh = MapSolarSystems.objects.filter(security__lt=-0.99)
```

#### Spatial queries
```python
# Systems in a region
region_systems = MapSolarSystems.objects.filter(region_id=region_id)

# Systems in a constellation
const_systems = MapSolarSystems.objects.filter(constellation_id=const_id)

# Neighboring systems (via stargates)
# Requires joining mapDenormalize where group_id IN (4, 10)
```

### Performance Considerations

1. **Use `select_related()` for foreign keys:**
   ```python
   systems = MapSolarSystems.objects.select_related('region', 'constellation')
   ```

2. **Use `values()` for aggregations:**
   ```python
   MapSolarSystems.objects.values('region_id').annotate(count=Count('system_id'))
   ```

3. **Avoid N+1 queries:**
   ```python
   # BAD
   for sys in systems:
       print(sys.region.region_name)  # N+1 query

   # GOOD
   for sys in systems.select_related('region'):
       print(sys.region.region_name)
   ```

### Raw SQL for Complex Queries

Some queries may require raw SQL due to model limitations:

```python
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT s.solarSystemName, r.regionName, s.security
        FROM evesde_mapsolarsystems s
        JOIN evesde_mapregions r ON s.regionID = r.regionID
        WHERE s.security >= 0.9
        ORDER BY s.security DESC
        LIMIT 10
    """)
    results = cursor.fetchall()
```

---

## Visualization Guide

### Recommended Tools

1. **3D Visualization:**
   - Three.js (web-based)
   - Plotly (Python)
   - D3.js (2D force-directed graphs)

2. **2D Maps:**
   - Leaflet (geographic-style maps)
   - D3.js (custom projections)
   - Graphviz (topology diagrams)

3. **Data Processing:**
   - pandas (Python dataframes)
   - Django ORM (direct database access)

### Visualization Approaches

#### 1. Regional Map
- Color-code regions by security status
- Show system density
- Highlight faction territories

#### 2. Network Topology
- Nodes = solar systems
- Edges = stargate connections
- Force-directed layout to show clusters

#### 3. 3D Star Map
- Plot systems using X, Y, Z coordinates
- Size by security status or station count
- Color by region or faction

#### 4. Trade Route Analysis
- Highlight major trade hubs
- Show jump distances
- Indicate high-traffic corridors

### Sample Visualization Data Structure

```json
{
  "systems": [
    {
      "id": 30000142,
      "name": "Jita",
      "region": "The Forge",
      "security": 0.945913,
      "coordinates": {"x": -1.29e17, "y": 6.08e16, "z": 1.17e17},
      "stations": 15,
      "connections": [30000143, 30000144, ...]
    }
  ],
  "regions": [
    {
      "id": 10000002,
      "name": "The Forge",
      "faction": null,
      "system_count": 89
    }
  ]
}
```

---

## Summary

New Eden is a vast, structured universe with:

- **Hierarchical organization** (Region → Constellation → System)
- **Security-based gameplay** (Highsec → Lowsec → Nullsec → Wormhole)
- **Faction-controlled territories** in highsec
- **Player-controlled territories** in nullsec
- **3D spatial coordinates** for accurate positioning
- **Rich celestial diversity** (stars, planets, moons, gates, stations)
- **Notable landmarks** adding depth and lore

The SDE provides comprehensive data for visualization, analysis, and application development. Understanding this structure is key to building tools that help players navigate, trade, and conquer in New Eden.

---

## Further Exploration

To continue exploring the SDE:

1. **Jump connectivity:** Analyze stargate connections to map travel routes
2. **Faction warfare:** Examine lowsec faction control patterns
3. **Market hubs:** Correlate station counts with trade volumes
4. **Sovereignty:** Map player-owned nullsec territories
5. **Wormhole mapping:** Track dynamic wormhole connections
6. **Industry:** Map resource distribution (moon minerals, ore, ice)

For questions or issues with the SDE models in this project, check:
- `/home/genie/gt/evewire/crew/delve/core/sde/models.py` - Django model definitions
- EVE Online SDE documentation at https://evekit.github.io/eve-sde/
- EVE Developers forums at https://forums.eveonline.com/

---

*Report generated: 2026-01-27*
*SDE Version: Current (check database schema for version)*
*Total Systems Analyzed: 8,437*
*Total Regions Analyzed: 113*
