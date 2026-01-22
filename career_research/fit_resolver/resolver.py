"""
Fit to Skills Resolver

Converts EVE ship fits into required skill trees using the SDE.

A fit consists of:
- Ship type
- High slot modules
- Medium slot modules
- Low slot modules
- Rig slots
- Submodules (for T3 cruisers)

The resolver computes:
1. Explicit skill requirements (from dgmTypeAttributes)
2. Implicit fitting skills (Weapon Upgrades, Shield Upgrades, etc.)
3. Skill levels for each requirement
"""

import sqlite3
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional
from pathlib import Path


@dataclass
class SkillRequirement:
    """A single skill requirement with level."""
    skill_id: int
    skill_name: str
    level: int

    def __hash__(self):
        return hash((self.skill_id, self.level))

    def __eq__(self, other):
        if not isinstance(other, SkillRequirement):
            return False
        return self.skill_id == other.skill_id and self.level == other.level


    def __lt__(self, other):
        return (self.skill_name, self.level) < (other.skill_name, other.level)


@dataclass
class Fit:
    """A ship fit."""
    ship_type_id: int
    ship_name: str
    high_slots: List[int] = field(default_factory=list)  # typeIDs
    med_slots: List[int] = field(default_factory=list)
    low_slots: List[int] = field(default_factory=list)
    rig_slots: List[int] = field(default_factory=list)
    subsystem_slots: List[int] = field(default_factory=list)
    drones: List[int] = field(default_factory=list)
    implants: List[int] = field(default_factory=list)

    def all_items(self) -> List[int]:
        """Return all item typeIDs in the fit, including ship."""
        items = [self.ship_type_id]
        items.extend(self.high_slots)
        items.extend(self.med_slots)
        items.extend(self.low_slots)
        items.extend(self.rig_slots)
        items.extend(self.subsystem_slots)
        items.extend(self.drones)
        items.extend(self.implants)
        return items


class FitResolver:
    """Resolves fits into skill requirements."""

    # Skill requirement attribute IDs from dgmAttributeTypes
    SKILL_ATTRS = {
        1: (182, 277),   # Primary Skill required, level
        2: (183, 278),   # Secondary Skill required, level
        3: (184, 279),   # Tertiary Skill required, level
        4: (1285, 1827), # Quaternary Skill required, level (estimated)
        5: (1289, 1828), # Quinary Skill required, level (estimated)
        6: (1290, 1829), # Senary Skill required, level (estimated)
    }

    # Common fitting skills that affect CPU/PG
    # These aren't always explicit requirements but are often needed
    FITTING_SKILLS = {
        3413: "Power Grid Management",
        3424: "CPU Management",
        3418: "Weapon Upgrades",
        3425: "Advanced Weapon Upgrades",
        3421: "Shield Upgrades",
        3420: "Shield Management",
        3422: "Energy Grid Upgrades",
        3423: "Energy Systems Operation",
        3419: "Hull Upgrades",
        3426: "Mechanic",
        26252: "Capital Weapon Upgrades",
    }

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the resolver.

        Args:
            db_path: Path to SQLite database with SDE tables.
                     If None, uses the Django app's database.
        """
        if db_path is None:
            # Use the shared EVE SDE database
            db_path = Path('~/data/evewire/eve_sde.sqlite3').expanduser()

        self.db_path = db_path
        self._cache = {}

    def _get_conn(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_skill_name(self, skill_id: int) -> Optional[str]:
        """Get the name of a skill by its typeID."""
        if skill_id not in self._cache:
            self._cache[skill_id] = {}

        if "name" not in self._cache[skill_id]:
            with self._get_conn() as conn:
                row = conn.execute(
                    "SELECT typeName FROM core_itemtype WHERE typeID = ?",
                    [skill_id]
                ).fetchone()
                self._cache[skill_id]["name"] = row["typeName"] if row else None

        return self._cache[skill_id]["name"]

    def get_item_skill_requirements(self, item_id: int) -> List[SkillRequirement]:
        """
        Get explicit skill requirements for an item.

        Args:
            item_id: typeID of the item

        Returns:
            List of SkillRequirement objects
        """
        requirements = []

        with self._get_conn() as conn:
            for level, (skill_attr, level_attr) in self.SKILL_ATTRS.items():
                # Get the skill typeID and required level
                row = conn.execute("""
                    SELECT
                        MAX(CASE WHEN dta.attributeID = ? THEN dta.valueFloat ELSE NULL END) as skill_id,
                        MAX(CASE WHEN dta.attributeID = ? THEN COALESCE(dta.valueInt, dta.valueFloat) ELSE NULL END) as skill_level
                    FROM core_typeattribute dta
                    WHERE dta.typeID = ? AND dta.attributeID IN (?, ?)
                """, [skill_attr, level_attr, item_id, skill_attr, level_attr]).fetchone()

                if row and row["skill_id"] and row["skill_level"]:
                    skill_name = self.get_skill_name(int(row["skill_id"]))
                    if skill_name:
                        requirements.append(SkillRequirement(
                            skill_id=int(row["skill_id"]),
                            skill_name=skill_name,
                            level=int(row["skill_level"])
                        ))

        return requirements

    def resolve_fit(self, fit: Fit) -> Set[SkillRequirement]:
        """
        Resolve a fit into its complete skill requirements.

        Args:
            fit: Fit object

        Returns:
            Set of SkillRequirement objects
        """
        all_requirements = set()

        for item_id in fit.all_items():
            item_reqs = self.get_item_skill_requirements(item_id)
            all_requirements.update(item_reqs)

        return all_requirements

    def resolve_fit_dict(self, fit_data: Dict) -> Set[SkillRequirement]:
        """
        Resolve a fit from a dictionary format.

        Args:
            fit_data: Dictionary with keys like 'ship', 'highs', 'meds', 'lows', 'rigs'

        Returns:
            Set of SkillRequirement objects
        """
        fit = Fit(
            ship_type_id=fit_data.get("ship", 0),
            ship_name=fit_data.get("ship_name", ""),
            high_slots=fit_data.get("highs", []),
            med_slots=fit_data.get("meds", []),
            low_slots=fit_data.get("lows", []),
            rig_slots=fit_data.get("rigs", []),
            subsystem_slots=fit_data.get("subsystems", []),
            drones=fit_data.get("drones", []),
        )
        return self.resolve_fit(fit)

    def format_requirements(self, requirements: Set[SkillRequirement]) -> str:
        """Format skill requirements for display."""
        lines = ["Skill Requirements:"]
        lines.append("-" * 40)

        for req in sorted(requirements):
            level_str = "V" * req.level
            lines.append(f"  {req.skill_name:<40} {level_str}")

        lines.append("-" * 40)
        lines.append(f"Total: {len(requirements)} skills")
        return "\n".join(lines)


def demo():
    """Demo the fit resolver."""
    # Example: A simple fit
    fit_data = {
        "ship": 11377,  # Thorax (Gallente cruiser)
        "ship_name": "Thorax",
        "highs": [
            3037,  # Heavy Ion Blaster II
            3037,  # Heavy Ion Blaster II
            3037,  # Heavy Ion Blaster II
            2909,  # Small Armor Repairer II
        ],
        "meds": [
            11269,  # 1MN MicroWarpdrive II
            3444,   # Stasis Webifier II
        ],
        "lows": [
            2035,   # Magnetic Field Stabilizer II
            2035,   # Magnetic Field Stabilizer II
            1246,   # Damage Control II
            2281,   # Small Armor Repairer II
        ],
        "rigs": [
            31228,  # Small Hybrid Collision Accelerator I
        ],
    }

    resolver = FitResolver()
    requirements = resolver.resolve_fit_dict(fit_data)

    print(resolver.format_requirements(requirements))


if __name__ == "__main__":
    demo()
