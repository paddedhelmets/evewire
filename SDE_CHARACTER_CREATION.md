# EVE Online Character Creation and Heritage - SDE Analysis

**Generated:** 2026-01-27
**Database:** EVE Static Data Export (SDE)
**Focus:** Character creation options, races, bloodlines, ancestries, and starting attributes

---

## Table of Contents

1. [Character Creation Flow](#character-creation-flow)
2. [The Four Main Races](#the-four-main-races)
3. [Bloodlines](#bloodlines)
4. [Ancestries](#ancestries)
5. [Attribute System](#attribute-system)
6. [Expert Systems](#expert-systems)
7. [Implants and Apparel](#implants-and-apparel)
8. [Factions](#factions)

---

## Character Creation Flow

Character creation in EVE Online follows a hierarchical structure:

```
Race (4 playable) → Bloodline (3 per race) → Ancestry (3 per bloodline) → Gender (2)
```

**Total Combinations:** 4 races × 3 bloodlines × 3 ancestries × 2 genders = **72 unique character combinations**

### Creation Steps

1. **Choose Race** - Select one of four playable races
2. **Choose Bloodline** - Select one of three ethnic/cultural groups within the race
3. **Choose Ancestry** - Select one of three family backgrounds
4. **Choose Gender** - Male or Female (affects only description/flavor text)
5. **Final Attributes** - Bloodline base attributes + Ancestry bonus attributes

---

## The Four Main Races

### 1. Caldari (Race ID: 1)

**Theme:** Corporate dictatorship, meritocracy, efficiency, patriotism

**Description:** Founded on the tenets of patriotism and hard work that carried its ancestors through hardships on an inhospitable homeworld, the Caldari State is today a corporate dictatorship, led by rulers who are determined to see it return to the meritocratic ideals of old. Ruthless and efficient in the boardroom and on the battlefield, the Caldari are living examples of the saying "the ends justify the means."

**Icon ID:** 1439

**Bloodlines:**
- Achura - Reclusive and introverted, highly intelligent
- Civire - Masters of focused aggression, highly competitive
- Deteis - Natural leaders, articulate and organized

---

### 2. Minmatar (Race ID: 2)

**Theme:** Tribal democracy, resilience, freedom, ingenuity

**Description:** Once a thriving tribal civilization, the Minmatar were enslaved by the Amarr Empire for more than 700 years until a massive rebellion freed most, but not all, of those held in servitude. The Minmatar people today are resilient, ingenious, and hard-working. Many of them believe that democracy, though slow, is the only form of government that can guarantee freedom and equality.

**Icon ID:** 1440

**Bloodlines:**
- Brutor - Martial, strong-willed, disciplined warriors
- Sebiestor - Innovative engineers and inventors
- Vherokior - Practical mystics and traders

---

### 3. Amarr (Race ID: 4)

**Theme:** Religious empire, divine right, conquest, tradition

**Description:** The largest of the five main empires, the Amarr Empire is a sprawling patch-work of feudal-like provinces held together by the might of the emperor. Religion has always played a big part in Amarr society and the Amarr people consider themselves to be the ones chosen by God to rule and civilize New Eden. Their religion is centered around the prophecies of the Amarr Emperor.

**Icon ID:** 1442

**Bloodlines:**
- Amarr - Religious reclaimers, traditional aristocracy
- Khanid - Cyber knights, influenced by Caldari culture
- Ni-Kunni - Assimilated former conquest, wealthy merchants

---

### 4. Gallente (Race ID: 8)

**Theme:** Liberal democracy, individual liberty, diversity, innovation

**Description:** Champions of liberty and defenders of the downtrodden, the Gallente play host to the only true democracy in New Eden. Some of the most progressive leaders, scientists, and businessmen of the era have emerged from its diverse peoples. A pioneer of artificial intelligence, the Federation relies heavily on automation and advanced technology.

**Icon ID:** 1441

**Bloodlines:**
- Gallente - Freedom-loving, democratic, diverse
- Intaki - Gifted communicators, spiritual and philosophical
- Jin-Mei - Hierarchical caste system, recently joined Federation

---

## Bloodlines

Bloodlines represent ethnic or cultural groups within each race. Each bloodline has:

- **Base Attributes:** Starting attribute values (total of 30 points)
- **Corporation ID:** Starting NPC corporation
- **Ship Type ID:** Historical starting ship (now unused)
- **Separate descriptions** for male and female characters

### Bloodline Structure

```
Race
├── Bloodline 1 (Base Attributes: PER X, WIL X, CHA X, MEM X, INT X)
├── Bloodline 2 (Base Attributes: PER X, WIL X, CHA X, MEM X, INT X)
└── Bloodline 3 (Base Attributes: PER X, WIL X, CHA X, MEM X, INT X)
```

---

## Ancestries

Ancestries represent a character's family background and heritage. Each ancestry provides:

- **Attribute Bonuses:** Additional +1 to +4 points in specific attributes
- **Background Story:** Flavor text describing family history
- **Career Hints:** Suggests certain playstyles or career paths

### Ancestry Bonus Structure

Every ancestry provides exactly **4 bonus attribute points** distributed as follows:

Common patterns:
- **+4 to one attribute** (specialization)
- **+2 to two attributes** (dual focus)
- **+3 +1 split** (primary/secondary focus)
- **+1 +1 +1 +1** (balanced, rare)

---

## Attribute System

### The Five Attributes

1. **Perception (PER)** - Affects gunnery, missile, spaceship command skills
2. **Willpower (WIL)** - Affects command, corporation management skills
3. **Charisma (CHA)** - Affects trade, social, corporation management skills
4. **Memory (MEM)** - Affects industry, science, learning skills
5. **Intelligence (INT)** - Affects electronics, engineering, mechanics skills

### Attribute Calculation

```
Final Attributes = Bloodline Base (30) + Ancestry Bonus (4) = Total (34)
```

**All character combinations result in exactly 34 total attribute points.**

### Attribute Distribution by Bloodline

#### Caldari

**Achura Bloodline** (INT-focused)
- Base: PER 7, WIL 6, CHA 3, MEM 6, INT 8 (Total: 30)
- Inventors: +4 INT → INT 12
- Monks: +2 PER, +2 WIL → PER 9, WIL 8
- Stargazers: +1 PER, +3 MEM → PER 8, MEM 9

**Civire Bloodline** (PER/WIL-focused)
- Base: PER 9, WIL 6, CHA 6, MEM 4, INT 5 (Total: 30)
- Dissenters: +2 WIL, +2 CHA → WIL 8, CHA 8
- Entrepreneurs: +4 MEM → MEM 8
- Mercs: +4 WIL → WIL 10

**Deteis Bloodline** (Balanced)
- Base: PER 5, WIL 5, CHA 6, MEM 7, INT 7 (Total: 30)
- Merchandisers: +4 MEM → MEM 11
- Scientists: +1 PER, +3 INT → PER 6, INT 10
- Tube Child: +4 WIL → WIL 9

#### Minmatar

**Brutor Bloodline** (PER/WIL-focused combat)
- Base: PER 9, WIL 7, CHA 6, MEM 4, INT 4 (Total: 30)
- Craftsmen: +4 MEM → MEM 8
- Liberated Children: +2 PER, +2 WIL → PER 11, WIL 9
- Tribal Traditionalists: +3 WIL, +1 CHA → WIL 10, CHA 7

**Sebiestor Bloodline** (INT/MEM-focused tech)
- Base: PER 5, WIL 6, CHA 6, MEM 6, INT 7 (Total: 30)
- Rebels: +3 PER, +1 WIL → PER 8, WIL 7
- Tinkerers: +4 INT → INT 11
- Traders: +4 CHA → CHA 10

**Vherokior Bloodline** (CHA/MEM-focused trade)
- Base: PER 4, WIL 3, CHA 8, MEM 8, INT 7 (Total: 30)
- Mystics: +3 WIL, +1 INT → WIL 6, INT 8
- Retailers: +1 CHA, +3 MEM → CHA 9, MEM 11
- Roamers: +2 PER, +2 INT → PER 6, INT 9

#### Amarr

**Amarr Bloodline** (WIL-focused religious)
- Base: PER 4, WIL 10, CHA 3, MEM 6, INT 7 (Total: 30)
- Liberal Holders: +1 WIL, +3 CHA → WIL 11, CHA 6
- Religious Reclaimers: +4 WIL → WIL 14
- Wealthy Commoners: +1 CHA, +3 MEM → CHA 4, MEM 9

**Khanid Bloodline** (PER/WIL balanced)
- Base: PER 8, WIL 8, CHA 5, MEM 4, INT 5 (Total: 30)
- Cyber Knights: +3 PER, +1 INT → PER 11, INT 6
- Unionists: +2 CHA, +2 INT → CHA 7, INT 7
- Zealots: +2 WIL, +2 MEM → WIL 10, MEM 6

**Ni-Kunni Bloodline** (CHA/PER focused)
- Base: PER 7, WIL 4, CHA 8, MEM 6, INT 5 (Total: 30)
- Border Runners: +3 PER, +1 INT → PER 10, INT 6
- Free Merchants: +4 CHA → CHA 12
- Navy Veterans: +4 WIL → WIL 8

#### Gallente

**Gallente Bloodline** (PER/CHA focused)
- Base: PER 8, WIL 4, CHA 8, MEM 4, INT 6 (Total: 30)
- Activists: +4 CHA → CHA 12
- Immigrants: +2 PER, +2 WIL → PER 10, WIL 6
- Miners: +4 MEM → MEM 8

**Intaki Bloodline** (INT/MEM balanced)
- Base: PER 3, WIL 6, CHA 6, MEM 7, INT 8 (Total: 30)
- Artists: +2 PER, +2 CHA → PER 5, CHA 8
- Diplomats: +4 CHA → CHA 10
- Reborn: +4 MEM → MEM 11

**Jin-Mei Bloodline** (CHA/WIL focused)
- Base: PER 6, WIL 7, CHA 7, MEM 5, INT 5 (Total: 30)
- Jing Ko Caste: +4 PER → PER 10
- Saan Go Caste: +2 MEM, +2 INT → MEM 7, INT 7
- Sang Do Caste: +3 WIL, +1 CHA → WIL 10, CHA 8

---

## Expert Systems

Expert Systems are temporary skill-granting items that provide access to specific ship types and career skills for a limited time.

### Expert System Categories

1. **Standard Expert Systems** (23 items)
   - Career-specific skill packages
   - Duration: 7-14 days
   - Lost on pod death: NO (persistent during rental period)

2. **Promotional Expert Systems** (14 items)
   - Event-based rewards
   - Alliance tournament prizes
   - Holiday specials

3. **QA Expert Systems** (10 items)
   - Developer testing tools
   - Not available to players

### Career Path Expert Systems

#### Core Skills
- **Core Ship Operations** - Foundational skills at Alpha clone maximum levels

#### Combat Careers
- **Enforcer** - T1 Destroyers (14 days)
- **Enforcer Operations** - Enforcer career path skills (7 days)
- **Soldier of Fortune** - T1 Cruisers (14 days)
- **Faction Warfare** - T1 and Navy Destroyers (7 days)
- **Logistics Pilot** - T1 Logistics Frigates and Cruisers (7 days)

#### Exploration Careers
- **Explorer** - Exploration Frigates with scanning/hacking (14 days)
- **Space Exploration** - General exploration skills (7 days)
- Race-specific: Amarr/Caldari/Gallente/Minmatar HS Space Exploration

#### Industry Careers
- **Industrialist** - Mining Barges and manufacturing skills (14 days)
- **Mining Barge Operations** - Mining Barges and Strip Miners (7 days)
- **Mining Destroyer Operations** - Pioneer-class mining destroyers (7 days)
- **Gas Harvesting** - Gas harvesting ships (7 days)
- **Hauler Operations** - Basic haulers (7 days)

#### Special Event Systems
- **Deathless Expert System** - Tholos and Breacher Pod Launchers
- **Crimson Harvest** - T1 Battlecruisers (7 days)
- **Capsuleer Day YC127** - T1 Battlecruisers (7 days)
- **Resplendent Coil** - Daredevil and Vigilant (7 days)
- **Kikimora Pilot** - Kikimora-class ship (7 days)

### Expert System Mechanics

- **Remote AI Access:** Expert Systems are independent from clone and capsule
- **Survival:** Not lost on pod death or clone jump
- **Duration:** Temporary skills last 7-14 days depending on system
- **Activation:** Automatic upon redemption
- **Stacking:** Multiple Expert Systems can be active simultaneously

---

## Implants and Apparel

### Implants (Category 20)

**Total Implants:** 2,130 items

#### Implant Categories

1. **Boosters** (1,250 items)
   - Temporary combat enhancements
   - Side effects and duration timers
   - Legal in various security levels

2. **Cyberimplants** (337 items)
   - General cybernetic enhancements

3. **Attribute Implants** by skill area:
   - **Cyber Gunnery** (99 items)
   - **Cyber Missile** (91 items)
   - **Cyber Navigation** (53 items)
   - **Cyber Engineering** (49 items)
   - **Cyber Electronic Systems** (36 items)
   - **Cyber Learning** (34 items) - Attribute boosters
   - **Cyber Armor** (33 items)
   - **Cyber Shields** (25 items)
   - **Cyber Social** (20 items)
   - **Cyber Resource Processing** (16 items)
   - **Cyber Drones** (16 items)
   - **Cyber Scanning** (15 items)
   - **Cyber Science** (13 items)
   - **Cyber Leadership** (13 items)
   - **Cyber Targeting** (12 items)
   - **Cyber Biology** (6 items)
   - **Cyber Production** (3 items)
   - **Cyber X Specials** (2 items)

#### Learning Implants (Attribute Boosters)

**Grades:**
- Limited (+1)
- Limited Beta (+1-2)
- Standard (+3)
- Improved (+4)
- Advanced (+5)
- Elite (+6)

**Types:**
- **Intelligence:** Cybernetic Subprocessor
- **Memory:** Memory Augmentation
- **Willpower:** Neural Boost
- **Perception:** Ocular Filter
- **Charisma:** Social Adaptation Chip

### Apparel (Category 30)

**Total Apparel Items:** 1,092 items

#### Apparel Groups

1. **Outerwear** (306 items)
   - Jackets, coats, suits
   - Armor suits
   - Corporate attire

2. **Bottoms** (183 items)
   - Pants, skirts
   - Corporate and casual styles

3. **Tops** (182 items)
   - Shirts, blouses
   - Uniform tops

4. **Headwear** (112 items)
   - Hats, helmets, caps
   - Ceremonial headpieces

5. **Footwear** (109 items)
   - Shoes, boots
   - Corporate and military styles

6. **Augmentations** (77 items)
   - Cybernetic visual enhancements
   - Face paint and body modifications
   - Makeup patterns

7. **Tattoos** (44 items)
   - Body art
   - Cultural markings

8. **Eyewear** (36 items)
   - Glasses, visors
   - Tactical eyewear

9. **Prosthetics** (32 items)
   - Cybernetic limbs
   - Mechanical replacements

10. **Masks** (11 items)
    - Face coverings
    - Respiratory equipment

#### Apparel Function

Apparel is primarily cosmetic and used for:
- Character customization in station environments
- Roleplaying and visual identity
- Display in character portrait
- Store vanity items (PLEX/AUR market)

---

## Factions

Factions represent the major political and military entities in New Eden.

### Major Empire Factions

1. **Amarr Empire** (ID: 500003)
   - Race ID: 4 (Amarr)
   - Corporation ID: 1000084
   - Militia Corporation: 1000179
   - Largest empire, feudal theocracy

2. **Caldari State** (ID: 500001)
   - Race ID: 1 (Caldari)
   - Corporation ID: 1000035
   - Militia Corporation: 1000180
   - Corporate dictatorship

3. **Gallente Federation** (ID: 500004)
   - Race ID: 8 (Gallente)
   - Corporation ID: 1000120
   - Militia Corporation: 1000181
   - Liberal democracy

4. **Minmatar Republic** (ID: 500002)
   - Race ID: 2 (Minmatar)
   - Corporation ID: 1000051
   - Militia Corporation: 1000182
   - Tribal democracy

### Minor Empire Factions

5. **Ammatar Mandate** (ID: 500007)
   - Amarr satellite state
   - Minmatar collaborators

6. **Khanid Kingdom** (ID: 500008)
   - Amarr breakaway kingdom
   - "Dark Amarr" culture

### Pirate Factions

7. **Angel Cartel** (ID: 500011)
   - Based in Curse region
   - Largest criminal organization

8. **Blood Raider Covenant** (ID: 500012)
   - Amarr religious cult
   - Sanguine cultists

9. **Guristas Pirates** (ID: 500010)
   - Founded by Caldari Navy deserters
   - Fatal and the Rabbit

10. **Sansha's Nation** (ID: 500019)
    - True Sansha's followers
    - Controlled by implants

11. **Serpentis** (ID: 500020)
    - Gallente criminal corporation
    - Drug trade and illegal tech

12. **The Syndicate** (ID: 500009)
    - Intaki exiles
    - Outer Ring region

### Special Factions

13. **CONCORD Assembly** (ID: 500006)
    - Inter-faction peacekeepers
    - DED (Directive Enforcement Division)

14. **Jove Empire** (ID: 500005)
    - Isolated, technologically superior
    - Not playable

15. **ORE** (ID: 500014)
    - Outer Ring Excavations
    - Largest mining corporation

16. **Mordu's Legion** (ID: 500018)
    - Mercenary organization
    - Caldari-Gallente war origins

17. **Thukker Tribe** (ID: 500015)
    - Nomadic Minmatar tribe
    - Great caravans

18. **Servant Sisters of EVE** (ID: 500016)
    - Humanitarian organization
    - Explorers and researchers

19. **The Society of Conscious Thought** (ID: 500017)
    - Jovian-founded
    - Philosophical and educational

### Modern Factions

20. **Drifters** (ID: 500024)
    - Jove-derived
    - Emerging from wormhole space

21. **Triglavian Collective** (ID: 500026)
    - Abyssal Deadspace civilization
    - Cladistic modification

22. **EDENCOM** (ID: 500027)
    - New Eden Common Defense Initiative
    - Anti-Triglavian coalition

23. **Deathless Circle** (ID: 500029)
    - New criminal power (YC125)
    - Emerging from underworld

---

## Summary

### Key Takeaways

1. **Balanced System:** All 72 character combinations result in exactly 34 total attribute points, ensuring balance.

2. **Career Specialization:** Bloodline base attributes determine general career aptitude, while ancestries provide further specialization.

3. **Attribute Impact:** Attributes affect skill training speed, making initial choice important for long-term progression.

4. **Expert Systems:** Provide temporary access to advanced skills, allowing new players to try different career paths without commitment.

5. **Cosmetic Customization:** Apparel and implants offer extensive character customization options for roleplay and visual identity.

6. **Faction Alignment:** Race/bloodline choices determine starting faction and corporation, affecting initial standing and location.

7. **No Wrong Choices:** While attributes matter, the difference is relatively small and can be compensated with implants and training time.

### Character Creation Quick Reference

| Race | Bloodlines | Specialization | Best For |
|------|------------|----------------|----------|
| Caldari | Achura | INT/MEM | Science, Industry, Electronics |
| Caldari | Civire | PER/WIL | Combat, Gunnery, Command |
| Caldari | Deteis | Balanced | Leadership, Management |
| Minmatar | Brutor | PER/WIL | Combat, Gunnery, Tactics |
| Minmatar | Sebiestor | INT/MEM | Engineering, Invention |
| Minmatar | Vherokior | CHA/MEM | Trade, Industry, Social |
| Amarr | Amarr | WIL/INT | Leadership, Industry, Religion |
| Amarr | Khanid | PER/WIL | Combat, Leadership |
| Amarr | Ni-Kunni | CHA/PER | Trade, Combat, Social |
| Gallente | Gallente | PER/CHA | Combat, Trade, Drones |
| Gallente | Intaki | INT/MEM | Science, Industry, Diplomacy |
| Gallente | Jin-Mei | CHA/WIL | Social, Leadership, Combat |

---

## Database Tables Referenced

- **ChrRaces** - Race definitions and descriptions
- **ChrBloodlines** - Bloodline definitions with base attributes
- **ChrAncestries** - Ancestry options with attribute bonuses
- **ChrFactions** - Faction information and relationships
- **InvTypes** - All items including Expert Systems, implants, and apparel
- **InvGroups** - Item group classifications

---

*This report was generated by exploring the EVE Online Static Data Export (SDE) database to understand character creation mechanics and heritage options.*
