# EVE Online SDE: NPC, Factions, and Agents Ecosystem

**Generated:** 2026-01-27
**Database:** ~/data/evewire/evewire_app.sqlite3
**SDE Tables Analyzed:**
- chrFactions (27 factions)
- chrRaces (11 races)
- crpNPCCorporations (283 NPC corporations)
- agtAgents (10,879 agents)
- agtAgentTypes (13 agent types)
- agtAgentsInSpace (360 in-space agents)
- staStations (5,154 stations)

---

## Executive Summary

EVE Online's NPC ecosystem is built on a hierarchical structure: **Factions** control territories, **Races** provide the playable lineages, **Corporations** conduct business and maintain infrastructure, and **Agents** serve as the primary interface for player interactions. The universe contains 27 major factions ranging from the four empire factions to pirate factions, emerging threats, and neutral organizations.

---

## 1. Major Factions and Their Control

### The Four Empires

#### **Caldari State** (Faction ID: 500001)
- **Capital System:** 30000145
- **Representative Corporation:** 1000035
- **Description:** A corporate dictatorship ruled by several mega-corporations with no central government. All territories are owned and ruled by corporations. Duty, discipline, and loyalty to one's corporation are paramount.
- **Race:** Caldari
- **Key Features:** Highly capitalistic, aggressive corporate competition, militaristic society

#### **Minmatar Republic** (Faction ID: 500002)
- **Capital System:** 30002544
- **Representative Corporation:** 1000051
- **Description:** Formed after the Minmatar Rebellion threw out Amarrian overlords. Only a quarter of Minmatar people reside within the Republic; the rest are scattered or enslaved.
- **Race:** Minmatar
- **Key Features:** Tribal traditions, independent spirit, strong alliance with Gallente Federation

#### **Amarr Empire** (Faction ID: 500003)
- **Capital System:** 30002187
- **Representative Corporation:** 1000084
- **Description:** The largest empire, a feudal-like theocracy ruled by an Emperor. Religion plays a major role, and they embrace slavery.
- **Race:** Amarr
- **Key Features:** Religious fundamentalism, slave labor, largest territorial holdings

#### **Gallente Federation** (Faction ID: 500004)
- **Capital System:** 30004993
- **Representative Corporation:** 1000120
- **Description:** A democratic and liberal society encompassing several races. Formerly included the Caldari State until a severe dispute led to war.
- **Race:** Gallente
- **Key Features:** Democracy, champions of liberty, masters of entertainment and pleasure

---

## 2. Special Factions

### Major Powers

#### **Jove Empire** (Faction ID: 500005)
- **Capital System:** 30001642
- **Representative Corporation:** 1000149
- **Description:** Isolated, mysterious, and technologically superior. Jovians number only a fraction of other races but possess technology eons ahead.
- **Status:** Generally inaccessible to players

#### **CONCORD Assembly** (Faction ID: 500006)
- **Capital System:** 30005204
- **Representative Corporation:** 1000137
- **Description:** Independent organization founded to facilitate negotiations between races and police space. Funds itself through customs and contraband confiscation.
- **Role:** Law enforcement, diplomatic mediation

#### **EDENCOM** (Faction ID: 500027)
- **Capital System:** 30005204
- **Representative Corporation:** 1000297
- **Description:** New Eden Common Defense Initiative, semi-autonomous military command set up by CONCORD and empires to fight Triglavian invasions.
- **Role:** Defense against Triglavian Collective

### Minor Factions

#### **Ammatar Mandate** (Faction ID: 500007)
- Amarr-aligned Minmatar descendants (Nefantar tribe)
- Semi-autonomous, still at war with Minmatar Republic

#### **Khanid Kingdom** (Faction ID: 500008)
- "Dark Amarr" - founded by Khanid who refused ritual suicide
- Mix of Amarr traditions and Caldari customs

#### **The Syndicate** (Faction ID: 500009)
- Pirate haven formed by Intaki exiles
- Autonomous stations, illegal goods hub
- Leader: Silphy en Diabel

#### **Thukker Tribe** (Faction ID: 500015)
- Nomadic Minmatar tribe
- Roams space in huge caravans
- Base in Great Wildlands region

#### **Servant Sisters of EVE** (Faction ID: 500016)
- Humanitarian aid organization
- Religious: believe EVE gate is gateway to heaven
- Scientific research around EVE gate

#### **The Society of Conscious Thought** (Faction ID: 500017)
- Three-century-old organization founded by Jovian Ior Labron
- Operates prestigious schools in remote "kitz" strongholds
- Combines spiritual and scientific pursuits

#### **Mordu's Legion Command** (Faction ID: 500018)
- Mercenary force formed by Intaki military personnel who sided with Caldari
- Loosely associated with Caldari Navy
- Hired to protect assets (e.g., Outer Ring Excavations)

#### **ORE** (Faction ID: 500014)
- Outer Ring Excavations - largest independent mining corporation
- Originally Gallentean, now operates independently in Outer Ring
- Wealthy enough to buy protection from pirate factions

#### **EverMore** (Faction ID: 500013)
- Holding company for InterBus
- Diversified interests from space habitats to AI
- Operates independently of empires

---

## 3. Pirate Factions

### Major Pirate Cartels

#### **Guristas Pirates** (Faction ID: 500010)
- **Capital System:** 30001290
- **Representative Corporation:** 1000127
- **Leaders:** Fatal and the Rabbit (former Caldari Navy members)
- **Operations:** Bases close to Caldari space, raids into State itself
- **Reputation:** More honorable than most, but extremely dangerous
- **Key Corporations:**
  - Guristas (S|R) - main cartel, well-organized and disciplined
  - Guristas Production (T|C) - maintains fleets and stations, missile research
  - Tronhadar Free Guard (T|L) - Guristas-aligned mercenary outfit

#### **Angel Cartel** (Faction ID: 500011)
- **Capital System:** 30001045
- **Representative Corporation:** 1000138
- **Operations:** Based in Curse region, operates almost everywhere
- **Structure:** Multiple specialized groups
- **Key Corporations:**
  - The Dominations (T|G) - command division, elusive leaders
  - Archangels (M|G) - main arm, pirates/scavengers/smugglers
  - Guardian Angels (S|G) - protects Serpentis assets exclusively
  - Salvation Angels (S|G) - non-combat, builds/maintains stations and ships
  - Malakim Zealots (S|G) - tech heist specialists, part of Deathless Circle alliance

#### **Blood Raider Covenant** (Faction ID: 500012)
- **Capital System:** 30003088
- **Representative Corporation:** 1000134
- **Leader:** Omir Sarikausa (top of DED most wanted list)
- **Operations:** Bases in Bleak Lands region
- **Activities:** Attack space farers, drain bodies of blood for rituals
- **Beliefs:** Sani Sabik cult, cloned bodies have "purer" blood
- **Key Corporations:**
  - Blood Raiders (S|R) - main cult, extremely dangerous

#### **Sansha's Nation** (Faction ID: 500019)
- **Capital System:** 30001868
- **Representative Corporation:** 1000162
- **Founder:** Sansha (Caldari tycoon)
- **History:** Once a utopian state, now scattered remnants in outer regions
- **Technology:** Capsule tech combined with human minds, zombie-like creatures
- **Key Corporations:**
  - True Creations (M|G) - operates shipyards, increasing Nation's ship numbers
  - True Power (S|G) - military arm, also mining and manufacturing

#### **Serpentis** (Faction ID: 500020)
- **Capital System:** 30004623
- **Representative Corporation:** 1000135
- **Founder:** V. Salvador Sarpati
- **Operations:** Home in Phoenix constellation, Fountain region
- **Activities:** Illegal neural boosters, protected by Guardian Angels
- **Key Corporations:**
  - Serpentis Corporation (M|G) - main research/drug cartel
  - Serpentis Inquest (T|C) - researches black cyber implants and cloning

### Minor/Regional Powers

#### **Deathless Circle** (Faction ID: 500029)
- **Capital System:** 30100000 (Zarzakh)
- **Representative Corporation:** 1000441
- **Emergence:** YC125, major new pirate faction
- **Operations:** Occupied abandoned Jovian outpost "Zarzakh" (The Fulcrum)
- **Composition:** Coalition of Caldari crime families, Thukker gangsters, renegades
- **Alliances:** Loose alliance with Angel Cartel and other criminal organizations

---

## 4. Emerging Threats

#### **Drifters** (Faction ID: 500024)
- **Capital System:** 30005286
- **Representative Corporation:** 1000274
- **Origin:** Emerged from Sleeper civilization ruins in Anoikis (W-space)
- **Technology:** Inheritors of ancient Jove legacy
- **Threat Level:** Tremendous challenge and dire threat to empires and capsuleers
- **Behavior:** Unafraid to wield tremendous power

#### **Rogue Drones** (Faction ID: 500025)
- **Capital System:** 30005286
- **Representative Corporation:** 1000287
- **Race:** Rogue Drones (134)
- **Nature:** Not a unified collective
- **Structure:** Local cooperation and "hive minds" that compete with each other
- **Behavior:** Readily attack and recycle competing hives

#### **Triglavian Collective** (Faction ID: 500026)
- **Capital System:** 30005286
- **Representative Corporation:** 1000298
- **Race:** Triglavian (135)
- **Origin:** Secluded in Abyssal Deadspace for centuries/millennia
- **Technology:** Advanced space-time mechanics, bioadaptive technology
- **Invasion:** YC122 invasion led to EDENCOM formation

---

## 5. Playable Races

### Primary Races (Empire Factions)

| Race ID | Race Name | Faction | Description Summary |
|---------|-----------|---------|-------------------|
| 1 | Caldari | Caldari State | Corporate dictatorship, patriotism, hard work, efficient and ruthless |
| 2 | Minmatar | Minmatar Republic | Tribal civilization, former slaves, resilient and ingenious |
| 4 | Amarr | Amarr Empire | Largest/oldest empire, theocratic, slave labor, highly educated |
| 8 | Gallente | Gallente Federation | Only true democracy, champions of liberty, pioneers of AI/drones |

### Special Races

| Race ID | Race Name | Description |
|---------|-----------|-------------|
| 16 | Jove | Most mysterious, technologically superior, small population |
| 32 | Pirate | Generic pirate race (no description) |
| 64 | Sleepers | Ancient civilization (no description) |
| 128 | ORE | Mining corporation group |
| 134 | Rogue Drones | Rogue Drones |
| 135 | Triglavian | Triglavian |
| 168 | Upwell | Upwell Consortium (structure builders) |

---

## 6. NPC Corporation Structure

### Corporation Size Codes

| Code | Meaning | Description |
|------|---------|-------------|
| T | Titan | Largest corporations (e.g., Dominations, CBD Corporation) |
| H | Huge | Very large corporations (e.g., Kaalakiota, Hyasyoda, Quafe) |
| L | Large | Major corporations (e.g., Ishukone, Wiyrkomi, Perkone) |
| M | Medium | Mid-sized corporations (e.g., Archangels, Core Complexion) |
| S | Small | Smaller corporations (e.g., Guristas, Guardian Angels) |

### Corporation Extent Codes

| Code | Meaning |
|------|---------|
| G | Global - operations throughout New Eden |
| L | Local - regional operations |
| N | National - operates within faction space |
| R | Regional - multi-system but not global |
| C | Constellation - limited to constellation |

### Corporation Statistics

**Total NPC Corporations:** 283
**Corporations with Stations:** 185
**Total Stations:** 5,154

### Top Station-Owning Corporations

| Corporation | Stations | Name | Description |
|-------------|----------|------|-------------|
| 1000010 | 92 | Kaalakiota (KK) | Largest Caldari mega corp, fingers in everything |
| 1000100 | 91 | Quafe Company | Popular drink, massive political clout |
| 1000074 | 90 | Joint Harvesting | Giant raw material company (Amarr) |
| 1000056 | 90 | Core Complexion | Minmatar success story, cost-effective equipment |
| 1000002 | 90 | CBD Corporation | Major Caldari exporter/importer |
| 1000125 | 89 | CONCORD | Joint empire organization |
| 1000094 | 89 | TransStellar Shipping | Largest shipping company |
| 1000033 | 89 | Caldari Business Tribunal | Corporate dispute resolution |

### Corporation Examples by Faction

#### Caldari Mega Corporations
- **Kaalakiota (1000010)** - Largest, rivals Sukuuvestaa
- **Ishukone (1000019)** - Jovian trade relations, advanced tech
- **Lai Dai (1000020)** - Quality focus, energetic research
- **Hyasyoda (1000005)** - Oldest, conservative, "Only paranoid survive"
- **Wiyrkomi (1000011)** - Family-owned (Seituoda), honor and trustworthiness
- **NOH (1000017)** - Entertainment industry, suspected criminal ties

#### Amarr Corporations
- **Joint Harvesting (1000074)** - Agricultural and mining giant
- **Multiple theological and slave-trading corporations**

#### Gallente Corporations
- **Quafe Company (1000100)** - Beverage empire with political power
- **Federal defense and manufacturing corporations**

#### Minmatar Corporations
- **Core Complexion (1000056)** - Innovative, cost-effective
- **Freedom Extension (1000061)** - Courier/shipping, Gallente-influenced

---

## 7. Agent System

### Agent Types

| Type ID | Type Name | Count | Description |
|---------|-----------|-------|-------------|
| 1 | NonAgent | 0 | Not used |
| 2 | BasicAgent | 8,734 | Standard mission agents |
| 3 | TutorialAgent | 14 | New player tutorials |
| 4 | ResearchAgent | 244 | Research and invention missions |
| 5 | CONCORDAgent | 143 | CONCORD-specific missions |
| 6 | GenericStorylineMissionAgent | 651 | Important storyline missions |
| 7 | StorylineMissionAgent | 7 | Specific storyline arcs |
| 8 | EventMissionAgent | 696 | Limited-time events |
| 9 | FactionalWarfareAgent | 260 | FW PvP missions |
| 10 | EpicArcAgent | 47 | Epic mission arcs |
| 11 | AuraAgent | 12 | Tutorial/Aura system |
| 12 | CareerAgent | 60 | Career advancement missions |
| 13 | HeraldryAgent | 11 | Corporation/alliance logo creation |

**Total Agents:** 10,879

### Agent Distribution by Level

| Level | Count | Percentage |
|-------|-------|------------|
| 1 | 3,731 | 34.3% |
| 2 | 2,928 | 26.9% |
| 3 | 2,214 | 20.4% |
| 4 | 1,826 | 16.8% |
| 5 | 180 | 1.7% |

**Note:** Quality field exists but is NULL for all agents (legacy mechanic removed)

### Agent Divisions

| Division ID | Agent Count | Likely Focus |
|-------------|-------------|--------------|
| 22 | 4,387 | Distribution/Trade |
| 24 | 4,636 | Unknown (popular) |
| 23 | 1,535 | Advisory/Consulting |
| 18 | 250 | Unknown |
| Other | 62 | Various specialized divisions |

### Locator Agents

- **Total with locator capability:** 1,757 (16.2%)
- **Total without:** 9,122 (83.8%)
- Locator agents can find players for a fee

### Top Agent-Heavy Corporations

| Corporation ID | Agent Count | Name |
|----------------|-------------|------|
| 1000023 | 162 | Expert Distribution (Caldari retail) |
| 1000010 | 162 | Kaalakiota (Caldari mega) |
| 1000125 | 161 | CONCORD |
| 1000094 | 159 | TransStellar Shipping |
| 1000100 | 157 | Quafe Company |
| 1000056 | 157 | Core Complexion (Minmatar) |

---

## 8. Agent Locations

### Station-Based Agents
- **Primary location:** Most agents (10,879) are at stations
- **Format:** locationID = stationID (6xxxxx format)
- **Coverage:** Agents distributed across 5,154 stations
- **Corporations:** 185 corporations have stations with agents

### In-Space Agents

**Total In-Space Agents:** 360
**Unique Solar Systems:** 128
**Unique Dungeons:** 169

**Top Systems by In-Space Agent Count:**
- 30001406: 12 agents
- 30003501: 11 agents
- 30003056: 11 agents
- 30002548: 11 agents
- 30001709: 11 agents

**Structure:**
- **agentID:** Unique identifier
- **dungeonID:** Instance/encounter identifier (169 unique)
- **solarSystemID:** Location system
- **spawnPointID:** Specific spawn location
- **typeID:** Agent type/shiptype

---

## 9. Corporation Activities

**Note:** The `crpActivities` table exists but is empty in this SDE. Historically, activities included:

1. Agriculture
2. Construction
3. Mining
4. Chemical
5. Military
6. Biotech
7. Hi-Tech
8. Entertainment
9. Shipyard
10. Warehouse
11. Retail
12. Trading
13. Bureaucratic
14. Political
15. Legal
16. Security
17. Financial
18. Education
19. Manufacture
20. Disputed

These activities determined what types of goods and services a corporation would offer and what missions they would give.

---

## 10. Faction-Corporation Relationships

### Key Observations

1. **No explicit factionID in crpNPCCorporations table** - The SDE does not directly link corporations to factions through a foreign key in this table
2. **Corporations are faction-aligned through:**
   - Description text (mentions of "Caldari space", "Amarr Empire", etc.)
   - Station locations in faction-controlled space
   - Agent distribution
   - Historical naming conventions

3. **Faction Representative Corporations:** Each faction has a `corporationID` field pointing to its main corporation

### Examples of Alignment

**Caldari-Aligned Corporations:**
- CBD Corporation (1000002) - "biggest exporters/importers in Caldari space"
- Kaalakiota (1000010) - "formidable voice in Caldari politics"
- Hyasyoda (1000005) - "Caldari mega corporations"
- Ishukone (1000019) - "advanced technology outside Jove space"

**Pirate Corporations:**
- Guristas (1000127) - "harassed the Caldari for some years"
- Angel Cartel corporations (1000124, 1000133, 1000136, 1000138)
- Sansha's Nation (1000161, 1000162)
- Serpentis (1000135, 1000157)

**Neutral/Independent:**
- CONCORD (1000125) - "independent organization"
- ORE (1000129) - "largest independent mining corporation"
- Sisters of EVE (1000130) - humanitarian aid
- InterBus/EverMore (1000148)

---

## 11. Key Insights

### Empire Structure
- **Caldari:** Corporate oligarchy, mega-corps control everything
- **Gallente:** Democracy with powerful corporations
- **Amarr:** Theocracy with religious corporations
- **Minmatar:** Tribal republic with growing corporations

### Pirate Ecosystem
- **Major Cartels:** Angel Cartel, Guristas, Serpentis, Sansha's Nation, Blood Raiders
- **Regional Powers:** Syndicate, Thukker Tribe
- **Emerging Threats:** Drifters, Triglavians, Rogue Drones
- **New Power:** Deathless Circle (YC125)

### Agent System
- **Heavily station-based:** Most agents accessible in stations
- **Level 1-4:** Common, distributed across highsec
- **Level 5:** Rare (180), typically in lowsec/nullsec
- **Specialized:** Tutorial, career, research, FW, epic arc agents

### Infrastructure
- **5,154 stations** across New Eden
- **Top corporations** own 60-90 stations each
- **185 corporations** maintain station networks
- **360 in-space agents** provide dungeon/encounter content

---

## 12. Data Quality Notes

### Missing/Null Fields
- **factionID** in crpNPCCorporations: All NULL (alignment inferred from descriptions)
- **quality** in agtAgents: All NULL (mechanic removed from game)
- **solarSystemID** in crpNPCCorporations: All NULL (corps HQ not specified)

### Table Discrepancies
- Empty `crpActivities` table (20 defined but unused)
- Duplicate table naming (e.g., `agtAgents` vs `evesde_agtagents`)
- Station names are empty in SDE (populated by client/server)

### Active vs Legacy Tables
- `evesde_*` prefix tables contain the actual SDE data
- Non-prefixed tables appear to be legacy or unused

---

## Conclusion

EVE Online's NPC ecosystem is a complex web of 27 factions, 11 races, 283 corporations, and nearly 11,000 agents. The four empire factions (Caldari, Gallente, Minmatar, Amarr) form the core of civilized space, while pirate factions operate from the fringes. Major pirate cartels like the Angel Cartel and Guristas have sophisticated corporate structures rivaling the empires. Emerging threats like Drifters and the Triglavian Collective represent new challenges to the established order.

The agent system provides the primary interface for players, with 10,879 agents offering missions across 5 levels and 13 specializations. Station-based infrastructure is extensive, with 185 corporations maintaining networks of 5,154 stations throughout New Eden.

This ecosystem supports EVE's player-driven economy and conflict, providing both opportunities and obstacles for capsuleers navigating the complex political and corporate landscape of New Eden.
