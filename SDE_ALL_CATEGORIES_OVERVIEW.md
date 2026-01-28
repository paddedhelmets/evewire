# EVE Online SDE - Complete Categories Overview

**Generated:** 2026-01-27
**Total Categories:** 48 (33 published)
**Total Groups:** 1,578 (954 published)
**Total Types:** 51,134 (26,403 published)

This document provides a comprehensive overview of all item categories in the EVE Online Static Data Export (SDE), including their purpose, key groups, important attributes, and browser display considerations.

---

## Executive Summary

The EVE SDE contains 48 categories spanning the entire spectrum of in-game items, from ships and modules to cosmetic items and structural components. This overview focuses on the 33 published categories that players interact with, totaling 26,403 item types across 954 groups.

### Top Categories by Item Count
1. **SKINs** (91) - 11,645 items - Cosmetic ship customizations
2. **Celestial** (2) - 5,650 items - Space objects and containers
3. **Blueprint** (9) - 5,072 items - Manufacturing blueprints
4. **Module** (7) - 4,623 items - Ship fittings and equipment
5. **Commodity** (17) - 4,028 items - Trade goods and materials

---

## Category Details

### Category 0: #System
**Status:** Unpublished
**Groups:** 1 (0 published)
**Items:** 0

**Purpose:** Internal system category for game engine objects.

**Display:** Not displayed in browser - internal use only.

---

### Category 1: Owner
**Status:** Unpublished
**Groups:** 4 (0 published)
**Items:** 0

**Purpose:** Defines ownership entities (corporations, factions, etc.).

**Display:** Not displayed as items - referenced by other objects.

---

### Category 2: Celestial
**Status:** Published
**Groups:** 80 (15 published)
**Items:** 223

**Purpose:** All objects found in space that are not ships or structures.

**Key Groups:**
- Station Improvement Platform (30 items) - Outpost upgrades
- Harvestable Cloud (28 items) - Gas clouds for harvesting
- Compressed Gas (27 items) - Compressed gas forms
- Audit Log Secure Container (6 items) - Special containers
- Freight Container (6 items) - Large cargo containers
- Secure Cargo Container (5 items) - Anchorable containers
- Cargo Container (3 items) - Basic containers
- Biomass (2 items) - Player corpses

**Important Attributes:**
- `volume` - Size for cargo calculations
- `capacity` - Internal storage space
- `mass` - Physical mass

**Browser Display Considerations:**
- **Special container viewer** - Show capacity, anchoring requirements
- **Gas cloud visualization** - Show harvestable types and yield
- **Container security info** - Password protection, audit logs
- **3D model viewer** - Celestial objects are visually distinctive

**Sample Items:**
- Gallente Advanced Outpost Factory Platform
- Amber Cytoserocin
- Giant Secure Container
- Corpse Female

---

### Category 3: Station
**Status:** Unpublished
**Groups:** 2 (0 published)
**Items:** 0

**Purpose:** Station type definitions (NPC stations).

**Display:** Not displayed as items - referenced by station services.

---

### Category 4: Material
**Status:** Published
**Groups:** 20 (17 published)
**Items:** 265

**Purpose:** Raw and processed materials used in manufacturing and research.

**Key Groups:**
- Intermediate Materials (41 items) - T2 component materials
- Salvaged Materials (41 items) - Items from salvaging wrecks
- Biochemical Material (32 items) - Booster components
- Moon Materials (20 items) - Moon mining products
- Ancient Salvage (19 items) - Sleeper/Tech 3 salvage
- Named Components (19 items) - Specialized components
- Composite (17 items) - Advanced materials
- Abyssal Materials (15 items) - Abyssal deadspace mutaplasmids
- Molecular-Forged Materials (12 items) - High-tech components
- Mineral (11 items) - Standard minerals
- Hybrid Polymers (9 items) - Reaction products
- Rogue Drone Components (8 items) - Drone alloy components
- Unrefined Mineral (8 items) - Raw ore forms
- Ice Product (7 items) - Ice refining products
- Fuel Block (4 items) - Structure/starbase fuel

**Important Attributes:**
- `volume` - Critical for logistics planning
- `base_price` - Market valuation
- `portion_size` - Minimum tradable unit

**Browser Display Considerations:**
- **Material tier visualization** - Show tech level and refinement chain
- **Market price integration** - Real-time pricing
- **Usage calculator** - What can be built with this material
- **Source information** - Where to obtain (mine, salvage, buy)
- **Batch size indicators** - Portion size for manufacturing
- **Material groups** - Color-code by material type (mineral, salvage, etc.)

**Sample Items:**
- Caesarium Cadmide
- Alloyed Tritanium Bar
- Pure Improved Blue Pill Booster
- Atmospheric Gases
- Ancient Radar Decorrelator
- Crystalline Carbonide
- Armor Mutaplasmid Residue
- Heavy Water
- Helium Fuel Block

---

### Category 5: Accessories
**Status:** Published
**Groups:** 9 (7 published)
**Items:** 77

**Purpose:** Special items that don't fit other categories - primarily account services.

**Key Groups:**
- Outpost Improvements (60 items) - Nullsec station upgrades
- Skill Injectors (5 items) - Skill point injection
- Legacy Currency (4 items) - Old currency tokens
- Services (4 items) - Account services
- Outpost Upgrades (3 items) - Station expansion modules
- PLEX (1 item) - Game time token

**Important Attributes:**
- `description` - Detailed effect explanation
- `base_price` - Store value

**Browser Display Considerations:**
- **Service effect display** - Show what the item does
- **Usage instructions** - How to activate/use
- **Account binding info** - Character vs account bound
- **Historical info** - For legacy items

**Sample Items:**
- Amarr Advanced Outpost Factory
- Daily Alpha Injector
- 100 Aurum Token
- Multiple Pilot Training Certificate
- PLEX

---

### Category 6: Ship
**Status:** Published
**Groups:** 48 (46 published)
**Items:** 412

**Purpose:** All flyable spacecraft in EVE.

**Key Groups:**
- Frigate (51 items) - Small, fast ships
- Cruiser (38 items) - Medium-sized combat ships
- Battleship (35 items) - Large combat vessels
- Combat Battlecruiser (21 items) - Heavy hitters
- Destroyer (20 items) - Anti-frigate vessels
- Hauler (18 items) - Cargo transport ships
- Assault Frigate (15 items) - Tech 2 frigates
- Heavy Assault Cruiser (14 items) - Tech 2 cruisers
- Dreadnought (13 items) - Capital siege ships
- Shuttle (11 items) - Basic transport
- Interceptor (10 items) - Fast tackle ships
- Force Recon Ship (10 items) - Covert ops cruisers
- Corvette (9 items) - Rookie ships
- Covert Ops (9 items) - Stealth frigates
- Titan (8 items) - Super-capital command ships
- Command Ship (8 items) - Fleet boosters
- Logistics (7 items) - Repair ships
- Freighter (6 items) - Massive cargo haulers
- Supercarrier (6 items) - Fighter carriers
- Heavy Interdiction Cruiser (6 items) - Heavy dictors

**Important Attributes:**
- `volume` - Ship size (packaged vs assembled)
- `capacity` - Cargo bay size
- `mass` - Affects agility and warp speed
- `base_price` - Insurance value

**Browser Display Considerations:**
- **3D ship viewer** - Rotate and inspect models
- **Fitting display** - Show slots, CPU, PG, calibration
- **Ship stats panel** - Speed, signature, tank, dps
- **Skill requirements** - Prerequisite tree visualization
- **Variants gallery** - Show all skins and faction variants
- **Tech level indicator** - T1/T2/T3/faction/pirate
- **Bonuses display** - Role and racial bonuses
- **Drone bandwidth** - Drone capacity
- **Flight time** - Warp speed calibration

**Sample Items:**
- Astero (Faction exploration frigate)
- Arbitrator (Drone cruiser)
- Abaddon (Amarr battleship)
- Caiman (Amarr dreadnought)
- Avatar (Amarr titan)

---

### Category 7: Module
**Status:** Published
**Groups:** 187 (158 published)
**Items:** 3,941

**Purpose:** Equipment that can be fitted to ships to modify their capabilities.

**Key Groups:**
- Hybrid Weapon (223 items) - Blasters and railguns
- Energy Weapon (216 items) - Lasers
- Armor Coating (184 items) - Passive armor resists
- Energized Armor Membrane (169 items) - Active armor resists
- Projectile Weapon (167 items) - Artillery and autocannons
- Armor Hardener (148 items) - Active armor hardeners
- Propulsion Module (147 items) - Afterburners and MWDs
- Smart Bomb (137 items) - Area effect weapons
- Armor Repair Unit (105 items) - Armor repairers
- Shield Hardener (103 items) - Active shield hardeners
- Shield Booster (94 items) - Shield repairers
- Shield Resistance Amplifier (84 items) - Passive shield resists
- Rig Armor (72 items) - Armor rig modifications
- Rig Shield (72 items) - Shield rig modifications
- Rig Drones (64 items) - Drone rig modifications
- Rig Navigation (64 items) - Navigation rig modifications
- Rig Core (60 items) - Core rig modifications
- Energy Nosferatu (58 items) - Capacitor draining
- Warp Scrambler (57 items) - Warp disruption
- Energy Neutralizer (57 items) - Capacitor destruction

**Important Attributes:**
- `volume` - Size for cargo
- `mass` - For smartbombs
- `meta_group` - Tech level (T1/T2/faction/dead/officer)
- `base_price` - Market value

**Browser Display Considerations:**
- **Module slot visualization** - High/med/low/rig slots
- **Fitting requirements** - CPU, Powergrid, Capacitor
- **Attribute comparison** - Compare with fitted module
- **Meta level indicator** - Visual tech level distinction
- **Skill requirements** - Prerequisite skills
- **Bonus/malus display** - Show tradeoffs (e.g., +CPU, -speed)
- **Stacking penalties** - Warning for similar modules
- **Variants listing** - All meta levels side by side
- **Damage type breakdown** - For weapons
- **Optimal range visualization** - Range/falloff graphs

**Sample Items:**
- 'Corporate' Light Electron Blaster I
- 'Arquebus' Heavy Beam Laser I
- Ahremen's Modified EM Armor Hardener
- 10000MN Abyssal Afterburner
- Capital Auxiliary Nano Pump I

---

### Category 8: Charge
**Status:** Published
**Groups:** 79 (68 published)
**Items:** 1,015

**Purpose:** Ammunition, crystals, and consumable charges for weapons and systems.

**Key Groups:**
- Hybrid Charge (208 items) - Blaster/railgun ammo
- Frequency Crystal (184 items) - Laser crystals
- Projectile Ammo (128 items) - Artillery/autocannon ammo
- Mining Crystal (66 items) - Mining laser crystals
- Festival Charges (40 items) - Fireworks and celebration items
- Capacitor Booster Charge (18 items) - Cap booster charges
- Light Missile (17 items) - Standard light missiles
- Torpedo (16 items) - Anti-capital missiles
- Heavy Missile (16 items) - Standard heavy missiles
- Cruise Missile (16 items) - Long-range missiles
- Rocket (16 items) - Short-range missiles
- Heavy Assault Missile (16 items) - HAM ammo
- Exotic Plasma Charge (12 items) - EDENCOM weapons
- Condenser Pack (12 items) - Triglavian weapons
- Advanced Ammo types (8 items each) - T2 ammunition variants

**Important Attributes:**
- `volume` - Magazine size
- `portion_size` - Stack size
- `mass` - For missile calculations

**Browser Display Considerations:**
- **Damage type breakdown** - EM/Thermal/Kinetic/Explosive ratios
- **Size class indicator** - S/M/L/XL/XXL
- **Tech level badge** - T1/T2/faction
- **Range visualization** - Optimal/falloff for guns, flight time for missiles
- **Weapon compatibility** - Which weapons use this charge
- **Stacking visualization** - Magazine capacity
- **Comparative stats** - Compare with other charge types
- **Bonus effects** - Special properties (tracking, cap use, etc.)

**Sample Items:**
- Antimatter Charge L
- Blood Gamma L
- Arch Angel Carbonized Lead L
- Caldari Navy Inferno Light Missile
- Cap Booster 100

---

### Category 9: Blueprint
**Status:** Published
**Groups:** 209 (204 published)
**Items:** 4,136

**Purpose:** Manufacturing blueprints for all producible items in EVE.

**Key Groups:**
- Rig Blueprint (642 items) - Ship rig blueprints
- Structure Rig Blueprint (175 items) - Structure rig blueprints
- Mutaplasmid Blueprint (170 items) - Abyssal mutaplasmid blueprints
- Missile Blueprint (117 items) - Missile blueprints
- Implant Blueprints (114 items) - Implant manufacturing
- Frigate Blueprint (93 items) - Frigate blueprints
- Armor Coating Blueprint (80 items) - Resistance module blueprints
- Hybrid Weapon Blueprint (77 items) - Hybrid weapon blueprints
- Cruiser Blueprint (74 items) - Cruiser blueprints
- Construction Component Blueprints (74 items) - Component parts
- Mining Crystal Blueprint (72 items) - Mining crystal blueprints
- Energy Weapon Blueprint (68 items) - Laser weapon blueprints
- Composite Reaction Formulas (66 items) - Reaction blueprints
- Projectile Weapon Blueprint (65 items) - Projectile weapon blueprints
- Structure Module Blueprint (63 items) - Structure module blueprints
- Missile Launcher Blueprint (59 items) - Launcher blueprints
- Combat Drone Blueprint (59 items) - Drone blueprints
- Smart Bomb Blueprint (55 items) - Smartbomb blueprints
- Subsystem Blueprints (48 items) - T3 subsystem blueprints
- Propulsion Module Blueprint (44 items) - Propulsion blueprints

**Important Attributes:**
- `volume` - Blueprint size
- `base_price` - Blueprint value

**Browser Display Considerations:**
- **Manufacturing requirements** - Materials, skills, time
- **ME/TE levels** - Material/Time efficiency
- **Produced item link** - Link to what it makes
- **Invention info** - For T2 blueprints
- **Copy vs Original** - BPO vs BPC distinction
- **Activity tabs** - Manufacturing, copying, invention, ME/TE research
- **Material calculator** - Total cost analysis
- **Profit calculator** - Build cost vs market price
- **Skill requirements** - Industry skills needed
- **Facility requirements** - Required station/structure

**Sample Items:**
- Capital Algid Energy Administrations Unit I Blueprint
- Standup L-Set Advanced Component Manufacturing Efficiency I Blueprint
- Anathema Blueprint
- Inferno Auto-Targeting Cruise Missile I Blueprint

---

### Category 10: Trading
**Status:** Unpublished
**Groups:** 2 (0 published)
**Items:** 0

**Purpose:** Market trading mechanics.

**Display:** Not displayed as items.

---

### Category 11: Entity
**Status:** Unpublished
**Groups:** 392 (0 published)
**Items:** 0

**Purpose:** NPC, faction, and organization definitions.

**Display:** Referenced by other objects, not displayed directly.

---

### Category 14: Bonus
**Status:** Unpublished
**Groups:** 10 (0 published)
**Items:** 0

**Purpose:** Bonus and reward definitions.

**Display:** Not displayed as items.

---

### Category 16: Skill
**Status:** Published
**Groups:** 25 (24 published)
**Items:** 505

**Purpose:** Character skills that enable abilities and improve performance.

**Key Groups:**
- Spaceship Command (90 items) - Ship operation skills
- Gunnery (65 items) - Weapon operation skills
- Science (43 items) - Research and industry skills
- Resource Processing (35 items) - Mining and refining skills
- Missiles (31 items) - Missile operation skills
- Drones (28 items) - Drone operation skills
- Fleet Support (20 items) - Leadership and warfare skills
- Subsystems (16 items) - T3 subsystem skills
- Sequencing (16 items) - Industry efficiency skills
- Electronic Systems (15 items) - Electronic warfare skills
- Trade (15 items) - Market and trading skills
- Navigation (15 items) - Movement and piloting skills
- Engineering (15 items) - Capacitor and fitting skills
- Armor (14 items) - Armor tanking skills
- Production (13 items) - Manufacturing skills
- Shields (13 items) - Shield tanking skills
- Rigging (10 items) - Rig installation skills
- Social (10 items) - NPC interaction skills
- Neural Enhancement (9 items) - Implant and booster skills
- Targeting (8 items) - Targeting and tracking skills

**Important Attributes:**
- `description` - Detailed effect explanation
- `base_price` - Skill book cost

**Browser Display Considerations:**
- **Skill tree visualization** - Prerequisite relationships
- **Training time calculator** - Based on attributes
- **Level effects** - What each level unlocks
- **Bonus breakdown** - Per-level benefits
- **Required for** - List of items/ships that need this skill
- **Training queue integration** - Add to queue
- **Attribute modifiers** - Primary/secondary attributes
- **Skill book cost** - ISK price
- **Mastery info** - Certificate/mastery requirements

**Sample Items:**
- Advanced Spaceship Command
- Advanced Doomsday Operation
- Advanced Laboratory Operation
- Abyssal Ore Processing
- Auto-Targeting Missiles

---

### Category 17: Commodity
**Status:** Published
**Groups:** 69 (63 published)
**Items:** 2,834

**Purpose:** Trade goods, mission items, and miscellany.

**Key Groups:**
- Miscellaneous (659 items) - Diverse items
- Commodities (423 items) - Standard trade goods
- Mutaplasmids (413 items) - Abyssal mutation items
- Livestock (198 items) - Live cargo and NPCs
- Empire Insignia Drops (140 items) - Faction dog tags
- Criminal Tags (138 items) - Pirate tags
- Acceleration Gate Keys (104 items) - Exploration access keys
- Construction Components (72 items) - Building materials
- Strong Boxes (45 items) - Reward containers
- Artifacts and Prototypes (41 items) - Special items
- Materials and Compounds (41 items) - Manufacturing materials
- Advanced Capital Construction Components (40 items) - Capital building parts
- Abyssal Filaments (35 items) - Abyssal entry keys
- Research Data (34 items) - Research items
- Triglavian Datastreams (27 items) - Triglavian data items
- Capital Construction Components (25 items) - Capital ship parts
- Unknown Components (24 items) - Mystery items
- Datacores (23 items) - Invention components
- Overseer Personal Effects (23 items) - Boss loot
- Tool (21 items) - Manufacturing tools

**Important Attributes:**
- `volume` - Often oversized for value
- `base_price` - Variable

**Browser Display Considerations:**
- **Usage information** - What is this for?
- **Source location** - Where to find/buy
- **Mission info** - If mission-related
- **Loot drop tables** - What drops this
- **Faction standing** - Required/rewarded by which factions
- **Stack visualization** - Show quantity
- **Special properties** - Consumable, reusable, etc.
- **Market history** - Price trends
- **Quick sell** - NPC buy orders if applicable

**Sample Items:**
- A Lot of Money
- 17 Successful Torture Techniques
- Decayed 10000MN Afterburner Mutaplasmid
- A Really REALLY Clueless Tourist
- 'Buck' Turgidson's Insignia

---

### Category 18: Drone
**Status:** Published
**Groups:** 13 (7 published)
**Items:** 133

**Purpose:** Autonomous and semi-autonomous drone units.

**Key Groups:**
- Combat Drone (80 items) - Attack drones
- Logistic Drone (18 items) - Repair drones
- Mining Drone (14 items) - Mining drones
- Electronic Warfare Drone (12 items) - EWAR drones
- Energy Neutralizer Drone (3 items) - Capacitor draining drones
- Stasis Webifying Drone (3 items) - Speed reducing drones
- Salvage Drone (3 items) - Salvaging drones

**Important Attributes:**
- `volume` - Drone bay capacity
- `mass` - Affects speed
- `base_price` - Replacement cost

**Browser Display Considerations:**
- **Drone stats panel** - Damage, tank, speed
- **Bandwidth usage** - Drone bandwidth required
- **Skill requirements** - Drone operation skills
- **Damage type breakdown** - For combat drones
- **Optimal range** - Engagement range
- **Mining yield** - For mining drones
- **Repair amount** - For logistic drones
- **EWAR strength** - For EWAR drones
- **Variant comparison** - Compare all drone types
- **Swarm tactics** - Recommended swarm sizes

**Sample Items:**
- 'Augmented' Acolyte
- Heavy Armor Maintenance Bot I
- 'Augmented' Ice Harvesting Drone
- Acolyte TD-300

---

### Category 20: Implant
**Status:** Published
**Groups:** 24 (22 published)
**Items:** 1,265

**Purpose:** Character attribute and skill boosters via cybernetic implants.

**Key Groups:**
- Booster (428 items) - Temporary boosters (consumable)
- Cyberimplant (330 items) - Permanent attribute implants
- Cyber Gunnery (99 items) - Turret bonuses
- Cyber Missile (91 items) - Missile bonuses
- Cyber Navigation (51 items) - Movement bonuses
- Cyber Engineering (48 items) - Fitting bonuses
- Cyber Electronic Systems (36 items) - EWAR bonuses
- Cyber Armor (33 items) - Armor tanking bonuses
- Cyber Learning (25 items) - Attribute bonuses
- Cyber Shields (25 items) - Shield tanking bonuses
- Cyber Drones (16 items) - Drone bonuses
- Cyber Resource Processing (16 items) - Mining/industry bonuses
- Cyber Scanning (15 items) - Scanning bonuses
- Cyber Leadership (13 items) - Command bonuses
- Cyber Targeting (12 items) - Targeting bonuses
- Cyber Science (9 items) - Research bonuses
- Special Edition Implant (7 items) - Limited edition implants
- Cyber Biology (6 items) - Booster/planet bonuses
- Cyber Production (3 items) - Industry bonuses
- Cyber X Specials (2 items) - Special implants

**Important Attributes:**
- `base_price` - Implant cost
- `volume` - Always 1.0

**Browser Display Considerations:**
- **Implant slot display** - Slot 1-10 indicator
- **Bonus breakdown** - Exact bonus amounts
- **Skill requirements** - Cybernetics skill level
- **Attribute bonuses** - For attribute implants
- **Set bonuses** - Complete implant sets
- **Variants comparison** - Compare all grades
- **Mutual exclusivity** - Cannot be used with X
- **Booster duration** - For booster group
- **Side effects** - For boosters
- **Character preview** - Show on character model

**Sample Items:**
- Advanced 'Boost' Cerebral Accelerator
- High-grade Amulet Alpha
- Eifyr and Co. 'Gunslinger' Large Projectile Turret LP-1001
- Hardwiring - Zainou 'Sharpshooter' ZMX10

---

### Category 22: Deployable
**Status:** Published
**Groups:** 20 (18 published)
**Items:** 43

**Purpose:** Anchorable space structures that can be deployed by players.

**Key Groups:**
- Mobile Warp Disruptor (9 items) - Anchorable bubbles
- Mobile Tractor Unit (5 items) - Wreck collection
- Encounter Surveillance System (4 items) - DED tracking
- FW Propaganda Broadcast Structure (4 items) - Faction warfare
- FW Listening Outpost (4 items) - Faction warfare
- Mobile Depot (3 items) - Mobile fitting
- Mobile Siphon Unit (3 items) - Moon theft
- Mobile Micro Jump Unit (2 items) - Jump deployment
- Mobile Cynosural Beacon (2 items) - Jump beacons
- Mercenary Den (2 items) - Abyssal support
- Mobile Cyno Inhibitor (1 item) - Cyno blocking
- Mobile Scan Inhibitor (1 item) - Scan blocking
- Mobile Observatory (1 item) - Data collection
- Mobile Analysis Beacon (1 item) - CONCORD tool
- Mobile Phase Anchor (1 item) - movement blocking

**Important Attributes:**
- `volume` - Deployment size
- `mass` - Anchoring mass
- `capacity` - Storage capacity

**Browser Display Considerations:**
- **Deployment requirements** - Skills, security status
- **Anchoring time** - How long to deploy
- **Hit points** - Structure HP
- **Effect radius** - Area of effect
- **Fuel consumption** - If applicable
- **Scoop-to-cargo** - Can be picked up
- **Reinforcement mode** - How it survives attacks
- **Access control** - Who can use
- **3D placement preview** - Show in space
- **Activation requirements** - What's needed to activate

**Sample Items:**
- Mobile Large Warp Disruptor I
- 'Magpie' Mobile Tractor Unit
- 'Wetu' Mobile Depot
- Small Mobile 'Hybrid' Siphon Unit

---

### Category 23: Starbase
**Status:** Published
**Groups:** 34 (26 published)
**Items:** 195

**Purpose:** Player-owned starbase (POS) structures and modules.

**Key Groups:**
- Control Tower (42 items) - POS central structures
- Mobile Laser Sentry (30 items) - Laser batteries
- Mobile Projectile Sentry (18 items) - Projectile batteries
- Mobile Hybrid Sentry (18 items) - Hybrid batteries
- Assembly Array (16 items) - Manufacturing modules
- Electronic Warfare Battery (12 items) - EWAR batteries
- Mobile Missile Sentry (9 items) - Missile batteries
- Silo (7 items) - Storage silos
- Warp Scrambling Battery (6 items) - Point batteries
- Mobile Reactor (5 items) - Reaction modules
- Energy Neutralizing Battery (5 items) - Neut batteries
- Laboratory (4 items) - Research labs
- Shield Hardening Array (4 items) - Resistance modules
- Sensor Dampening Battery (3 items) - Dampening batteries
- Stasis Webification Battery (3 items) - Web batteries
- Reprocessing Array (2 items) - Refining arrays
- Ship Maintenance Array (2 items) - Ship storage
- Moon Mining (1 item) - Moon harvesters
- Corporate Hangar Array (1 item) - Corp storage
- Tracking Array (1 item) - Tracking enhancement

**Important Attributes:**
- `volume` - Size for transport
- `mass` - Anchored mass
- `capacity` - Storage capacity

**Browser Display Considerations:**
- **POS grid layout** - Visual positioning tool
- **Powergrid/CPU usage** - Tower resource consumption
- **Anchoring requirements** - Skills, standings
- **Shield radius** - Protection area
- **Reinforcement timer** - How long it survives
- **Fuel consumption** - Strontium/fuel block usage
- **Password protection** - Access control
- **Online state** - On/off/anchoring
- **Module linking** - Show what connects to what
- **Moon compatibility** - Which moons can anchor

**Sample Items:**
- Amarr Control Tower
- Blood Large Beam Laser Battery
- Advanced Large Ship Assembly Array
- Biochemical Reactor Array
- Moon Harvesting Array

---

### Category 24: Reaction
**Status:** Published
**Groups:** 7 (5 published)
**Items:** 1

**Purpose:** Chemical and material reactions for advanced manufacturing.

**Key Groups:**
- Simple Reaction - Basic reactions
- Complex Reactions - Advanced reactions
- Simple Biochemical Reactions - Booster materials
- Complex Biochemical Reactions - Advanced booster materials
- Hybrid Reactions - Polymer reactions

**Important Attributes:**
- `volume` - Reaction product size

**Browser Display Considerations:**
- **Reaction calculator** - Inputs and outputs
- **Facility requirements** - Where reactions can occur
- **Cycle time** - How long each reaction takes
- **Yield calculation** - Output quantities
- **Profit analysis** - Cost vs value
- **Required skills** - Reaction operation skills
- **Flow chart** - Multi-step reaction chains
- **Tower optimization** - Best tower setup

**Note:** This category primarily defines reaction types rather than items.

---

### Category 25: Asteroid
**Status:** Published
**Groups:** 45 (36 published)
**Items:** 447

**Purpose:** All types of ore and ice found in asteroid belts and anomalies.

**Key Groups:**
- Ice (26 items) - Ice formations
- Ubiquitous Moon Asteroids (24 items) - Common moon goo
- Common Moon Asteroids (24 items) - Standard moon goo
- Uncommon Moon Asteroids (24 items) - Uncommon moon goo
- Rare Moon Asteroids (24 items) - Rare moon goo
- Exceptional Moon Asteroids (24 items) - Excellent moon goo
- Arkonor (13 items) - Highest-grade lowsec ore
- Crokite (13 items) - High-value ore
- Dark Ochre (13 items) - Nullsec ore
- Jaspet (13 items) - Mid-grade ore
- Kernite (13 items) - Mid-grade ore
- Pyroxeres (13 items) - Common ore variants
- Veldspar (13 items) - Most common ore
- Gneiss (13 items) - High-value ore
- Omber (13 items) - Common ore
- Bistot (12 items) - High-grade ore
- Hedbergite (12 items) - Mid-grade ore
- Hemorphite (12 items) - Mid-grade ore
- Plagioclase (12 items) - Common ore
- Scordite (12 items) - Very common ore

**Important Attributes:**
- `volume` - Ore volume (m³ per unit)
- `portion_size` - Minimum mining amount

**Browser Display Considerations:**
- **Ore composition** - Mineral breakdown per refine
- **Mining yield calculator** - Based on skills/ship
- **Security status** - Where ore is found
- **Refining calculator** - Output with skills/standing
- **Compression** - Compressed vs uncompressed
- **Market value** - Per m³ calculation
- **Mining crystals** - Required crystals
- **Visual comparison** - Ore appearance
- **Rarity indicator** - Common vs rare
- **Special variants** - +5%/+10% variants

**Sample Items:**
- Azure Ice
- Bitumens (Moon goo)
- Cobaltite (Moon goo)
- Arkonor
- Compressed Veldspar

---

### Category 26: WorldSpace
**Status:** Unpublished
**Groups:** 3 (0 published)
**Items:** 0

**Purpose:** 3D space environment definitions.

**Display:** Not displayed as items.

---

### Category 29: Abstract
**Status:** Unpublished
**Groups:** 5 (0 published)
**Items:** 0

**Purpose:** Abstract game mechanics and concepts.

**Display:** Not displayed as items.

---

### Category 30: Apparel
**Status:** Published
**Groups:** 14 (10 published)
**Items:** 970

**Purpose:** Clothing and accessories for character customization (New Eden Store).

**Key Groups:**
- Outer (278 items) - Coats, jackets, outerwear
- Tops (180 items) - Shirts, tops
- Bottoms (165 items) - Pants, skirts
- Footwear (99 items) - Shoes, boots
- Headwear (90 items) - Hats, caps, helmets
- Augmentations (64 items) - Facial modifications
- Prosthetics (32 items) - Cybernetic limbs
- Eyewear (30 items) - Glasses, goggles
- Tattoos (24 items) - Body art
- Masks (8 items) - Face coverings

**Important Attributes:**
- `volume` - Always 1.0
- `base_price** - Aurum/PLEX cost

**Browser Display Considerations:**
- **Character preview** - Show on character model
- **360° rotation** - View from all angles
- **Color variants** - All available colors
- **Store pricing** - PLEX/Aurum cost
- **Gender compatibility** - Male/female/unisex
- **Bundling info** - Part of any bundles
- **Limited availability** - Seasonal/event items
- **Wardrobe integration** - Add to character wardrobe
- **Screenshots** - In-game preview images
- **Unpackaging animation** - Opening effect

**Sample Items:**
- 'Silvershore' Greatcoat
- Men's 'Crimson Harvest' T-Shirt
- Men's 'Commando' Pants (black wax)
- Boots.ini
- Men's 'Boarder' Cap (Digital Camo)

---

### Category 32: Subsystem
**Status:** Published
**Groups:** 4 (4 published)
**Items:** 48

**Purpose:** Tech 3 cruiser subsystems that define ship capabilities.

**Key Groups:**
- Defensive Subsystem (12 items) - Tank and defensive capabilities
- Offensive Subsystem (12 items) - Weapon systems
- Propulsion Subsystem (12 items) - Movement and speed
- Core Subsystem (12 items) - Core ship systems

**Important Attributes:**
- `volume` - Subsystem size
- `mass` - Affects ship mass

**Browser Display Considerations:**
- **Slot display** - 5 subsystem slots
- **Ship compatibility** - Which T3 ship (Loki/Tengu/Proté/Legion)
- **Bonus breakdown** - What this subsystem provides
- **Skill requirements** - Subsystem skills
- **Configuration calculator** - Show full ship stats with this subsystem
- **Variant comparison** - Compare all options for slot
- **Racial styling** - Visual appearance changes
- **Rig slots** - How many rig slots provided
- **Slot layout** - Hardpoints provided

**Sample Items:**
- Legion Defensive - Augmented Plating
- Legion Offensive - Assault Optimization
- Legion Propulsion - Intercalated Nanofibers
- Legion Core - Augmented Antimatter Reactor

---

### Category 34: Ancient Relics
**Status:** Published
**Groups:** 6 (6 published)
**Items:** 18

**Purpose:** Sleeper technology relics for Tech 3 manufacturing.

**Key Groups:**
- Sleeper Hull Relics (6 items) - Ship hull components
- Sleeper Propulsion Relics (3 items) - Movement systems
- Sleeper Offensive Relics (3 items) - Weapon systems
- Sleeper Engineering Relics (3 items) - Engineering components
- Sleeper Defensive Relics (3 items) - Defensive components
- Sleeper Electronics Relics (0 items) - Electronic components

**Important Attributes:**
- `volume` - Relic size
- `base_price` - Market value

**Browser Display Considerations:**
- **Relic quality** - Intact/Malfunction/Wrecked
- **Usage information** - What subsystems it builds
- **Drop locations** - Where to find (wormhole classes)
- **Salvage skill** - Required salvaging level
- **Manufacturing calculator** - What you can build
- **Market data** - Buy/sell orders
- **Loot table** - Drop rates from sites
- **Visual distinction** - Quality level appearance

**Sample Items:**
- Intact Hull Section
- Intact Thruster Sections
- Intact Weapon Subroutines
- Intact Power Cores

---

### Category 35: Decryptors
**Status:** Published
**Groups:** 6 (6 published)
**Items:** 44

**Purpose:** Invention modifiers that affect blueprint copy outcomes.

**Key Groups:**
- Decryptors - Amarr (8 items) - Amarr-specific decryptors
- Decryptors - Minmatar (8 items) - Minmatar-specific decryptors
- Decryptors - Gallente (8 items) - Gallente-specific decryptors
- Decryptors - Caldari (8 items) - Caldari-specific decryptors
- Generic Decryptor (8 items) - Universal decryptors
- Decryptors - Hybrid (4 items) - T3 subsystem decryptors

**Important Attributes:**
- `volume` - Decryptor size
- `base_price` - Market cost

**Browser Display Considerations:**
- **Invention bonuses** - ME/TE/runs modifier
- **Probability bonus** - Success chance increase
- **Usage guide** - Which blueprints benefit
- **Cost analysis** - Is it worth using?
- **Racial restrictions** - Which blueprint types
- **Run modifier** - Max runs affected
- **ME/TE modifier** - Material/time efficiency
- **Comparative table** - All decryptors compared
- **Best use cases** - When to use each type

**Sample Items:**
- Occult Accelerant
- Cryptic Accelerant
- Incognito Accelerant
- Esoteric Accelerant

---

### Category 39: Infrastructure Upgrades
**Status:** Published
**Groups:** 7 (7 published)
**Items:** 73

**Purpose:** Nullsec system upgrades for infrastructure hubs.

**Key Groups:**
- Sovereignty Hub Site Detection Upgrades (30 items) - Exploration upgrades
- Infrastructure Hub Military Upgrades (15 items) - Combat anomalies
- Infrastructure Hub Industrial Upgrades (10 items) - Mining/industry
- Sovereignty Hub Colony Resources Management Upgrades (6 items) - Planet management
- Infrastructure Hub Strategic Upgrades (4 items) - Strategic upgrades
- Sovereignty Hub Service Infrastructure Upgrade (4 items) - Service upgrades
- Sovereignty Hub System Effect Generator Upgrades (4 items) - System effects

**Important Attributes:**
- `volume` - Upgrade module size
- `base_price` - Upgrade cost

**Browser Display Considerations:**
- **Upgrade tier** - Level 1-5
- **Effect description** - What this upgrade does
- **Installation requirements** - IHUB slots
- **System impact** - What changes in system
- **Cost vs benefit** - Is it worth it?
- **Prerequisites** - Required lower levels
- **Spawn rates** - Anomaly frequency
- **Military/Industrial index** - Required indices
- **Territory benefits** - Alliance-wide effects
- **Upgrade calculator** - Plan full system development

**Sample Items:**
- Exploration Detector 1
- Deprecated Entrapment Array 1
- Deprecated Ore Prospecting Array 1
- Power Monitoring Division 1

---

### Category 40: Sovereignty Structures
**Status:** Published
**Groups:** 4 (2 published)
**Items:** 2

**Purpose:** Nullsec sovereignty claim structures.

**Key Groups:**
- Territorial Claim Unit (1 item) - Old sov structure
- Sovereignty Hub (1 item) - Current sov hub

**Important Attributes:**
- `volume` - Structure size
- `mass` - Anchored mass

**Browser Display Considerations:**
- **Deployment requirements** - Skills, standings
- **Anchoring restrictions** - Where can be placed
- **Vulnerability window** - When can be attacked
- **Reinforcement mode** - How it survives attacks
- **Upgrade slots** - What upgrades can be installed
- **Territory map** - Show controlled systems
- **Fuel requirements** - If applicable
- **Access control** - Who can use
- **Online status** - Current state
- **Benefit visualization** - What territory provides

**Sample Items:**
- Defunct Territorial Claim Unit
- Sovereignty Hub

---

### Category 41: Planetary Industry
**Status:** Published
**Groups:** 9 (9 published)
**Items:** 91

**Purpose:** Planetary interaction (PI) structures for colony management.

**Key Groups:**
- Extractors (40 items) - Resource extraction heads
- Processors (18 items) - Manufacturing facilities
- Command Centers (8 items) - Colony central hub
- Storage Facilities (8 items) - Resource storage
- Spaceports (8 items) - Orbit launch facilities
- Extractor Control Units (8 items) - Advanced extraction
- Planetary Links (1 item) - Connection links

**Important Attributes:**
- `volume` - Structure size
- `capacity` - Storage capacity
- `mass` - Structure mass

**Browser Display Considerations:**
- **Planet type compatibility** - Which planets can use
- **Powergrid/CPU usage** - Resource consumption
- **Storage capacity** - How much it holds
- **Cycle time** - How fast it operates
- **Output calculator** - Production rates
- **Link visualization** - Show colony layout
- **Upgrade levels** - What can be upgraded
- **Tax implications** - Export/import costs
- **Colony planner** - Interactive colony designer
- **Efficiency calculator** - Optimal setups

**Sample Items:**
- Barren Aqueous Liquid Extractor
- Barren Advanced Industry Facility
- Barren Command Center
- Barren Storage Facility

---

### Category 42: Planetary Resources
**Status:** Published
**Groups:** 3 (3 published)
**Items:** 15

**Purpose:** Raw planetary materials that can be extracted.

**Key Groups:**
- Planet Solid - Raw Resource (5 items) - Solid materials
- Planet Liquid-Gas - Raw Resource (5 items) - Liquid/gas materials
- Planet Organic - Raw Resource (5 items) - Organic materials

**Important Attributes:**
- `volume` - Resource volume
- `portion_size` - Minimum extractable amount

**Browser Display Considerations:**
- **Planet type distribution** - Where found
- **Extraction rate** - Base yield
- **Richness map** - Abundance by planet
- **Usage information** - What can be made
- **Market value** - Per unit cost
- **Processing chain** - What it becomes
- **Depletion rate** - How fast it runs out
- **Quality indicator** - Purity levels

**Sample Items:**
- Base Metals
- Aqueous Liquids
- Autotrophs

---

### Category 43: Planetary Commodities
**Status:** Published
**Groups:** 4 (4 published)
**Items:** 68

**Purpose:** Processed planetary materials at various refinement tiers.

**Key Groups:**
- Refined Commodities - Tier 2 (24 items) - Second-tier products
- Specialized Commodities - Tier 3 (21 items) - Third-tier products
- Basic Commodities - Tier 1 (15 items) - First-tier products
- Advanced Commodities - Tier 4 (8 items) - Fourth-tier products

**Important Attributes:**
- `volume` - Product volume
- `portion_size` - Stack size

**Browser Display Considerations:**
- **Tier indicator** - T1/T2/T3/T4 badge
- **Production chain** - How to make
- **Input requirements** - What goes in
- **Processing time** - How long to make
- **Market data** - Buy/sell orders
- **Profit calculator** - Cost vs revenue
- **Facility requirements** - What can produce
- **Usage tree** - What it's used for
- **Import/export costs** - Tax implications
- **Supply chain map** - Full production tree

**Sample Items:**
- Biocells (Tier 2)
- Biotech Research Reports (Tier 3)
- Bacteria (Tier 1)
- Broadcast Node (Tier 4)

---

### Category 46: Orbitals
**Status:** Published
**Groups:** 4 (2 published)
**Items:** 2

**Purpose:** Orbital space structures for planet interaction.

**Key Groups:**
- Orbital Construction Platform (1 item) - Custom office platform
- Skyhook (1 item) - Orbital extraction structure

**Important Attributes:**
- `volume` - Structure size
- `mass` - Anchored mass
- `capacity` - Storage capacity

**Browser Display Considerations:**
- **Deployment requirements** - Skills, standings
- **Planet compatibility** - Which planet types
- **Tax settings** - Import/export tax rates
- **Access control** - Who can use
- **Reinforcement mode** - How it survives attacks
- **Vulnerability window** - When can be attacked
- **Customs office interface** - Tax configuration UI
- **Shield/armor HP** - Defense values
- **Orbit visualization** - Position around planet

**Sample Items:**
- Customs Office Gantry
- Orbital Skyhook

---

### Category 49: Placeables
**Status:** Unpublished
**Groups:** 2 (0 published)
**Items:** 0

**Purpose:** Placeable objects in environments.

**Display:** Not displayed as standard items.

---

### Category 53: Effects
**Status:** Unpublished
**Groups:** 3 (0 published)
**Items:** 0

**Purpose:** Visual and gameplay effect definitions.

**Display:** Not displayed as items.

---

### Category 54: Lights
**Status:** Unpublished
**Groups:** 3 (0 published)
**Items:** 0

**Purpose:** Lighting definitions for 3D environments.

**Display:** Not displayed as items.

---

### Category 59: Cells
**Status:** Unpublished
**Groups:** 1 (0 published)
**Items:** 0

**Purpose:** Cellular automata or grid definitions.

**Display:** Not displayed as items.

---

### Category 63: Special Edition Assets
**Status:** Published
**Groups:** 4 (4 published)
**Items:** 597

**Purpose:** Limited edition and special event items.

**Key Groups:**
- Special Edition Commodities (546 items) - Event-specific items
- Tournament Cards: New Eden Open YC 114 (27 items) - Tournament collectibles
- Tournament Cards: Alliance Tournament All Stars (20 items) - Historical tournament items
- Festival Charges Expired (4 items) - Expired festival items

**Important Attributes:**
- `volume` - Item size
- `base_price` - Variable (often high)

**Browser Display Considerations:**
- **Rarity indicator** - One-of-a-kind items
- **Event source** - How it was obtained
- **Historical data** - When/why it was released
- **Market status** - Can it be traded?
- **Collection tracking** - For completionists
- **Visual gallery** - Show item appearance
- **Lore background** - Story behind the item
- **Value trends** - Historical pricing
- **Unboxing animation** - If applicable
- **Special effects** - Unique properties

**Sample Items:**
- 'Bitwave Glacier' Augmentation Crate
- NEO YC 114: 8 CAS
- Alliance Tournament I: Band of Brothers
- Melted Snowball

---

### Category 65: Structure
**Status:** Published
**Groups:** 15 (7 published)
**Items:** 18

**Purpose:** Large player-owned structures (Upwell Consortium structures).

**Key Groups:**
- Citadel (9 items) - Defensive structures
- Engineering Complex (3 items) - Manufacturing structures
- Refinery (2 items) - Moon mining and refining
- Upwell Jump Bridge (1 item) - Alliance jump bridges
- Upwell Cyno Jammer (1 item) - Cynosural jamming
- Upwell Cyno Beacon (1 item) - Capital jump beacons
- Upwell Moon Drill (1 item) - Moon extraction

**Important Attributes:**
- `volume` - Structure size (packaged)
- `capacity** - Assembly capacity
- `mass` - Structure mass

**Browser Display Considerations:**
- **Structure size class** - S/M/L/X
- **Service slots** - What can be fitted
- **Rig slots** - Rig configuration
- **Hit points** - Shield/armor/structure HP
- **Vulnerability window** - When can be attacked
- **Reinforcement mode** - How it survives
- **Fuel consumption** - Fuel block usage
- **Deployment requirements** - Skills, standings
- **Access control** - ACL configuration
- **3D model viewer** - Rotate and inspect
- **Service modules** - Compatible services
- **Fitting simulator** - Configure structure fit
- **Market data** - Component costs
- **Location map** - Where structures are deployed

**Sample Items:**
- 'Draccous' Fortizar
- Azbel
- Athanor
- Ansiblex Jump Bridge
- Tenebrex Cyno Jammer
- Metenox Moon Drill

---

### Category 66: Structure Module
**Status:** Published
**Groups:** 162 (109 published)
**Items:** 356

**Purpose:** Modules and services that can be fitted to structures.

**Key Groups:**
- Outpost Conversion Rigs (104 items) - Legacy outpost rigs
- Quantum Cores (9 items) - Structure cores
- Structure Burst Projector (7 items) - Area effect modules
- Structure Engineering Service Module (6 items) - Manufacturing services
- Structure Disruption Battery (6 items) - EWAR batteries
- Structure Energy Neutralizer (5 items) - Cap warfare
- Structure Resource Processing Service Module (4 items) - Reaction services
- Structure Weapon Upgrade (4 items) - Damage upgrades
- Structure Fitting Module (4 items) - CPU/PG upgrades
- Structure ECM Battery (3 items) - ECM jamming
- Structure Engineering Rig variants (3 items each) - Various rig sizes
- Structure Citadel Service Module (2 items) - Basic services
- Structure XL Missile Launcher (2 items) - Anti-capital missiles
- Structure Guided Bomb Launcher (2 items) - Area bombardment
- Structure Area Denial Module (2 items) - Point defense
- Structure Stasis Webifier (2 items) - Speed reduction

**Important Attributes:**
- `volume` - Module size
- `mass` - Module mass

**Browser Display Considerations:**
- **Structure compatibility** - Which structures can fit
- **Service type** - What it provides
- **Resource consumption** - Power/CPU/Fuel
- **Effect description** - What it does
- **Skill requirements** - Operating skills
- **Fitting requirements** - Slot types
- **Upgrade paths** - Better versions
- **Cost analysis** - Operating cost
- **Range/effect** - Area of influence
- **Variants comparison** - Compare all options
- **Market data** - Buy/sell orders
- **Damage profile** - For weapon modules

**Sample Items:**
- Upwell A1F Outpost Rig
- Astrahus Upwell Quantum Core
- Standup ECM Jammer Burst Projector
- Standup Capital Shipyard I

---

### Category 87: Fighter
**Status:** Published
**Groups:** 6 (6 published)
**Items:** 94

**Purpose:** Carrier and supercarrier-launched combat units.

**Key Groups:**
- Light Fighter (24 items) - Standard fighters
- Heavy Fighter (17 items) - Anti-capital fighters
- Structure Heavy Fighter (17 items) - Structure heavy fighters
- Structure Light Fighter (16 items) - Structure light fighters
- Support Fighter (12 items) - Logistic/ECM fighters
- Structure Support Fighter (8 items) - Structure support fighters

**Important Attributes:**
- `volume` - Fighter hangar space
- `mass` - Fighter mass
- `capacity` - Squadron size

**Browser Display Considerations:**
- **Fighter stats** - DPS, tank, speed
- **Squadron size** - How many in wing
- **Launch bay** - Which tube type
- **Ability breakdown** - Special abilities
- **Skill requirements** - Fighter skills
- **Ammunition** - If applicable
- **Damage type** - Primary damage profile
- **Role indicator** - Attack/support/heavy
- **Comparison table** - All fighters compared
- **Ability preview** - Show special attacks
- **Consumption rate** - How fast they die
- **Recovery rate** - How fast they respawn

**Sample Items:**
- Caldari Navy Dragonfly
- Ametat I
- Standup Ametat I
- Standup Dragonfly I
- Caldari Navy Scarab

---

### Category 91: SKINs
**Status:** Published
**Groups:** 7 (7 published)
**Items:** 6,884

**Purpose:** Cosmetic ship customizations (licenses).

**Key Groups:**
- Permanent SKIN (5,780 items) - Forever skins
- 7-Day SKIN (272 items) - Week-long skins
- 30-Day SKIN (272 items) - Month-long skins
- 90-Day SKIN (272 items) - Quarter-long skins
- 1-Year SKIN (272 items) - Year-long skins
- Volatile SKIN (16 items) - Single-use skins
- 180-Day SKIN (0 items) - Half-year skins (unpublished)

**Important Attributes:**
- `volume` - Always 1.0
- `description` - Skin duration and applicability

**Browser Display Considerations:**
- **Ship preview** - Show skin on ship model
- **Duration indicator** - Time remaining
- **Applicability** - Which ships can use
- **3D viewer** - Rotate and inspect
- **Collection tracking** - Which skins owned
- **Store pricing** - PLEX/Aurum cost
- **Rarity indicator** - Common/limited/rare
- **Unboxing animation** - Opening effect
- **Wardrobe integration** - Skin collection
- **Expiration warning** - When skin expires
- **Ship filter** - Show only skins for owned ships
- **Screenshots** - In-game previews
- **Skin variants** - All available skins for ship type

**Sample Items:**
- Abaddon Aurora Universalis SKIN
- Abaddon Kador SKIN (7 Days)
- Apocalypse War Reserves Lieutenant SKIN (Volatile)

---

### Category 2100: Expert Systems
**Status:** Published
**Groups:** 3 (2 published)
**Items:** 29

**Purpose:** Temporary skill grants for new players.

**Key Groups:**
- Standard Expert Systems (16 items) - Regular skill packages
- Promotional Expert Systems (13 items) - Event-based systems

**Important Attributes:**
- `volume` - Always 1.0
- `description` - Duration and skills granted

**Browser Display Considerations:**
- **Skills granted** - What skills it provides
- **Duration** - How long it lasts
- **Expiration warning** - When it expires
- **Activation guide** - How to use
- **Skill level** - What level of skills
- **Account binding** - Character-specific
- **Unboxing animation** - Opening effect
- **Progress tracking** - Time remaining
- **Replacement info** - How to get more
- **Usage restrictions** - Alpha vs Omega

**Sample Items:**
- Amarr HS Space Exploration Expert System
- Amarr Foundation Day Expert System

---

### Category 2107: Mining
**Status:** Published
**Groups:** 0 (0 published)
**Items:** 0

**Purpose:** Mining-specific category (currently unused).

---

### Category 2118: Personalization
**Status:** Published
**Groups:** 3 (3 published)
**Items:** 1,589

**Purpose:** Ship customization and personalization items.

**Key Groups:**
- Ship Emblems (816 items) - Hull decals
- Ship SKIN Design Element (770 items) - SKIN components
- Sequence Binders (3 items) - Item modifiers

**Important Attributes:**
- `volume` - Always 1.0
- `description` - Placement and applicability

**Browser Display Considerations:**
- **Ship preview** - Show emblem on ship
- **Placement guide** - Where it goes
- **Applicability** - Which ships can use
- **Collection tracking** - Owned emblems
- **Rarity indicator** - Common/limited
- **3D viewer** - Rotate and inspect
- **Screenshots** - In-game previews
- **Store pricing** - PLEX cost
- **Unboxing animation** - Opening effect
- **Combination preview** - Multiple emblems

**Sample Items:**
- Abaddon Alliance Emblem
- AT XXI Mega-Victory - Limited
- Alignment Sequencer

---

### Category 2143: Colony Resources
**Status:** Published
**Groups:** 1 (1 published)
**Items:** 2

**Purpose:** Special colony management resources.

**Key Groups:**
- Colony Reagents (2 items) - Special colony materials

**Important Attributes:**
- `volume` - Resource volume
- `base_price` - Market value

**Browser Display Considerations:**
- **Usage information** - What it's for
- **Source location** - Where to find
- **Processing chain** - What it becomes
- **Market data** - Buy/sell orders
- **Rarity indicator** - How common

**Sample Items:**
- Magmatic Gas

---

### Category 2152: QA and Dev Groups
**Status:** Unpublished
**Groups:** 2 (0 published)
**Items:** 0

**Purpose:** Quality assurance and developer testing items.

**Display:** Not displayed in production.

---

### Category 350001: Infantry
**Status:** Unpublished
**Groups:** 17 (0 published)
**Items:** 0

**Purpose:** DUST 514 / Project Nova infantry items (cancelled project).

**Display:** Legacy category, not displayed.

---

## Browser Display Templates by Category Type

### 1. Physical Objects (Ships, Modules, Structures)
**Required Elements:**
- 3D model viewer with rotation
- Technical specifications panel
- Fitting/requirements display
- Skill prerequisite tree
- Market data integration
- Variants gallery

### 2. Consumables (Charges, Boosters, Fuel)
**Required Elements:**
- Stack visualization
- Usage calculator
- Damage/attribute breakdown
- Weapon compatibility
- Consumption rate
- Cost per use

### 3. Manufacturing Materials (Ore, Minerals, Components)
**Required Elements:**
- Volume/size display
- Composition breakdown
- Source locations
- Refining calculator
- Market price trends
- Usage tree (what uses this)

### 4. Blueprints
**Required Elements:**
- Manufacturing requirements
- ME/TE display
- Activity tabs (build, copy, research)
- Material calculator
- Profit analysis
- Invention info
- Produced item link

### 5. Skills
**Required Elements:**
- Skill tree visualization
- Training time calculator
- Level effects
- Prerequisite chains
- Required for (ships/modules)
- Mastery info
- Training queue integration

### 6. Cosmetic Items (SKINs, Apparel)
**Required Elements:**
- Character/ship preview
- 360° rotation
- Wardrobe/collection tracking
- Duration indicator
- Store pricing
- Rarity indicator
- Screenshots gallery

### 7. Structures and Deployables
**Required Elements:**
- Deployment requirements
- Reinforcement info
- Vulnerability window
- Access control
- Fuel consumption
- Effect radius
- Hit points
- 3D placement preview

### 8. Trade Goods and Commodities
**Required Elements:**
- Usage description
- Source information
- Mission info
- Market data
- NPC buy orders
- Loot drop tables
- Faction standing

### 9. Drones and Fighters
**Required Elements:**
- Stats panel (DPS, tank, speed)
- Bandwidth usage
- Skill requirements
- Damage type
- Squadron size
- Ability breakdown
- Comparison table

### 10. Implants and Boosters
**Required Elements:**
- Slot indicator
- Bonus breakdown
- Skill requirements
- Duration (for boosters)
- Side effects
- Set bonuses
- Character preview

---

## Common Attribute Patterns

### Volume-Based Display
Items with significant volume differences need special handling:
- **Ore**: Show per m³ calculations
- **Containers**: Show capacity vs volume
- **Ships**: Show packaged vs assembled

### Price-Based Display
Items with economic significance:
- **Materials**: Show market history
- **Blueprints**: Show cost analysis
- **Special Edition**: Show collector value

### Skill-Based Display
Items requiring skills:
- **Skills**: Show prerequisite tree
- **Modules**: Show fitting requirements
- **Ships**: Show mastery certificate

### Time-Based Display
Items with duration:
- **SKINs**: Show expiration countdown
- **Boosters**: Show active duration
- **Expert Systems**: Show time remaining

---

## Data Visualization Recommendations

### Interactive Elements
1. **Skill Tree Explorer** - Interactive prerequisite visualization
2. **Manufacturing Calculator** - Real-time cost/profit analysis
3. **Fitting Simulator** - Live fitting stats
4. **Market History Graphs** - Price trends over time
5. **3D Model Viewer** - Rotate, zoom, inspect items
6. **Comparison Tool** - Side-by-side item comparison

### Static Elements
1. **Attribute Tables** - Technical specifications
2. **Requirement Lists** - Skills, standings, etc.
3. **Usage Descriptions** - What items are for
4. **Lore/Flavor Text** - Background information
5. **Sample Images** - In-game screenshots

### Responsive Design
1. **Mobile-First** - Prioritize key information
2. **Progressive Enhancement** - Add details for larger screens
3. **Touch Gestures** - Swipe for variants, pinch for 3D
4. **Offline Support** - Cache common item data

---

## Conclusion

This overview covers all 33 published categories in the EVE Online SDE, providing a comprehensive reference for building an SDE browser UI. Each category has unique display requirements based on the nature of its items and how players interact with them.

**Key Takeaways:**
1. **Categories vary wildly** - From 2 items (Orbitals) to 11,645 items (SKINs)
2. **Display needs vary** - Some need 3D viewers, others need calculators
3. **Context matters** - Mining ore needs different info than fitting modules
4. **Templates can be shared** - Similar categories can use display templates
5. **Integration is key** - Market data, skills, and fittings should be integrated

**Next Steps for UI Development:**
1. Prioritize high-volume categories (SKINs, Modules, Ships)
2. Build reusable display templates
3. Integrate with ESI for real-time data
4. Implement 3D viewers for visual items
5. Create calculators for industrial items
6. Add market data integration
7. Build skill tree visualizations
8. Create comparison tools

---

**Document Version:** 1.0
**Last Updated:** 2026-01-27
**SDE Version:** Current (based on exploration)
**Total Items Documented:** 26,403 published types across 33 categories
