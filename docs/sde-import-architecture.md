# EVE SDE Import Architecture

This document explains the two separate SDE import systems used by evewire.

## Overview

Evewire uses **two separate import pipelines** for EVE SDE (Static Data Export) data:

1. **App Importer** (`import_sde.py`) - For Django app models
2. **Browser Importer** (`import_sde_browser.py`) - For SDE browser models

Both importers source from the same raw SDE file but target different tables with different purposes.

## Source: Raw SDE Database

**Location**: `~/data/evewire/eve_sde.sqlite3`

**Source**: [garveen/eve-sde-converter](https://github.com/garveen/eve-sde-converter) releases

**Format**: SQLite database with NO table prefixes (raw SDE schema from CCP)

**Tables**: `invTypes`, `mapSolarSystems`, `chrFactions`, `staStations`, etc.

**Updating**:
```bash
# Download latest SDE from garveen
cd ~/data/evewire
wget -qO sde.sqlite.bz2 https://github.com/garveen/eve-sde-converter/releases/download/sde-3171578-01ec212/sde.sqlite.bz2
python3 -c "import bz2; bz2.open('sde.sqlite.bz2', 'rb').read(), open('eve_sde.sqlite3', 'wb').write(bz2.open('sde.sqlite.bz2').read())"
rm sde.sqlite.bz2
```

**IMPORTANT**: The `eve_sde.sqlite3` file must remain **read-only** and **unmodified**. Never write app data to it.

---

## Importer 1: App SDE Import (`import_sde.py`)

**File**: `core/management/commands/import_sde.py`

**Purpose**: Import SDE data into Django **app models** for application logic

**Destination tables**: `core_*` prefix (e.g., `core_itemtype`, `core_solarsystem`, `core_faction`)

**Django models**: `core.eve.models` (managed models, migrations track schema)

**Usage**:
```bash
python manage.py import_sde                    # Import all required tables
python manage.py import_sde --tables=invTypes  # Import specific table
python manage.py import_sde --force             # Re-import even if exists
python manage.py import_sde --init             # Download full SDE to shared location
```

**Tables Imported**:
| SDE Table | Django Table | Model | Purpose |
|-----------|--------------|-------|---------|
| `invTypes` | `core_itemtype` | `ItemType` | Item catalog for skill plans, fittings |
| `invGroups` | `core_itemgroup` | `ItemGroup` | Item grouping |
| `invCategories` | `core_itemcategory` | `ItemCategory` | Item categories |
| `dgmAttributeTypes` | `core_attributetype` | `AttributeType` | Type attributes |
| `dgmTypeAttributes` | `core_typeattribute` | `TypeAttribute` | Item attribute values |
| `chrFactions` | `core_faction` | `Faction` | Faction info |
| `mapSolarSystems` | `core_solarsystem` | `SolarSystem` | System locations |
| `mapRegions` | `core_region` | `Region` | Region info |
| `staStations` | `core_station` | `Station` | Station info |

**Characteristics**:
- **Managed models**: Django migrations track schema changes
- **Selective import**: Only imports tables needed for app logic
- **Modified schema**: May have Django-specific modifications (e.g., `id` column for TypeAttribute)
- **Mixed data**: Can contain both SDE data and app-generated data
- **Used by**: Application logic, skill plans, fittings, assets, etc.

---

## Importer 2: SDE Browser Import (`import_sde_browser.py`)

**File**: `core/management/commands/import_sde_browser.py`

**Purpose**: Create complete 1:1 copy of SDE for read-only browsing

**Destination tables**: `evesde_*` prefix (e.g., `evesde_invtypes`, `evesde_mapsolarsystems`)

**Django models**: `core.sde.models` (unmanaged models, `managed=False`)

**Usage**:
```bash
python manage.py import_sde_browser              # Import all browser tables
python manage.py import_sde_browser --tables=invTypes,invGroups  # Specific tables
python manage.py import_sde_browser --list       # List available tables
python manage.py import_sde_browser --force      # Re-import even if exists
```

**Tables Imported** (100+ tables):
- **Items**: `invTypes`, `invGroups`, `invCategories`, `invMarketGroups`, `invMetaGroups`, etc.
- **Attributes**: `dgmAttributeTypes`, `dgmTypeAttributes`, `dgmEffects`, etc.
- **Universe**: `mapRegions`, `mapConstellations`, `mapSolarSystems`, `mapDenormalize`, etc.
- **Stations**: `staStations`
- **Corporations/Factions**: `crpNPCCorporations`, `chrFactions`, `chrRaces`, etc.
- **Agents**: `agtAgents`, `agtAgentTypes`, etc.
- **Certificates**: `certCerts`, `certSkills`, etc.
- **Blueprints**: `industryBlueprints`
- **And more**: See `AVAILABLE_TABLES` in `import_sde_browser.py`

**Characteristics**:
- **Unmanaged models**: Django does NOT track schema (`managed=False`)
- **Complete SDE**: Imports ALL available SDE tables
- **Exact 1:1 copy**: No schema modifications, mirrors raw SDE structure
- **Read-only**: Used for browsing and display, not app logic
- **Used by**: SDE Browser (`/sde/` routes), live data enrichment (`/live/` routes)

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    EVE SDE (CCP)                                    │
│                     JSON/YAML                                       │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│          garveen/eve-sde-converter                                 │
│          (node CLI tool: npm run build)                           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│          ~/data/evewire/eve_sde.sqlite3                            │
│          (Raw SDE - NO PREFIXES)                                    │
│          Tables: invTypes, mapSolarSystems, chrFactions, etc.      │
│          READ-ONLY SOURCE - DO NOT MODIFY                          │
└───────────┬──────────────────────────────────────────┬───────────────┘
            │                                          │
            │ import_sde.py                           │ import_sde_browser.py
            │ (selective)                              │ (complete 1:1)
            ▼                                          ▼
┌───────────────────────────────┐    ┌──────────────────────────────────┐
│   Django App Database          │    │   Django App Database             │
│   ~/data/evewire/              │    │   ~/data/evewire/                │
│   evewire_app.sqlite3          │    │   evewire_app.sqlite3            │
├───────────────────────────────┤    ├──────────────────────────────────┤
│   core_* tables (app models)   │    │   evesde_* tables (browser models) │
│   ───────────────────────      │    │   ──────────────────────────────  │
│   • core_itemtype              │    │   • evesde_invtypes               │
│   • core_solarsystem            │    │   • evesde_mapsolarsystems       │
│   • core_faction               │    │   • evesde_chrfactions            │
│   • core_station               │    │   • evesde_stastations            │
│   • core_region                │    │   • evesde_mapregions             │
│   • core_constellation (X)     │    │   • evesde_mapconstellations       │
│   ───────────────────────      │    │   • evesde_crpnpccorporations     │
│   Used by:                     │    │   • ... (100+ tables)             │
│   • Skill plans                │    │                                    │
│   • Fittings                   │    │   Used by:                         │
│   • Assets                     │    │   • SDE Browser (/sde/)           │
│   • Market orders              │    │   • Live data (/live/)           │
│   • Character management       │    │   • Template rendering            │
│                               │    │                                    │
│   Models: core.eve.models      │    │   Models: core.sde.models          │
│   Managed: Yes (migrations)    │    │   Managed: No (unmanaged)          │
└───────────────────────────────┘    └──────────────────────────────────┘
```

---

## When to Use Which Models

### Use `core.eve.models` (App Models) for:
- Application logic and business rules
- Skill plans (using `ItemType`, `ItemGroup`, etc.)
- Fittings (using `ItemType` for ship/module lookups)
- User character data associations
- Models that may be extended with app-specific fields

### Use `core.sde.models` (SDE Browser Models) for:
- Read-only SDE data browsing
- Enriching ESI live data with static SDE context
- Displaying SDE information in templates
- Looking up constellation/region/faction names for live data
- Any scenario requiring complete SDE coverage

### Example: Live Incursions View

```python
# ✅ CORRECT - Using SDE browser models for enrichment
from core.eve.models import ActiveIncursion  # Live ESI data
from core.sde.models import MapConstellations, ChrFactions  # Static SDE data

incursions = ActiveIncursion.objects.filter(last_sync_status='ok')
constellations = MapConstellations.objects.filter(
    constellation_id__in=[i.constellation_id for i in incursions]
)
factions = ChrFactions.objects.filter(
    faction_id__in=[i.faction_id for i in incursions]
)
```

---

## Common Issues

### Issue: `cannot import name 'Constellation' from 'core.eve.models'`

**Cause**: Trying to use `core.eve.models.Constellation` which doesn't exist.

**Solution**: Use `core.sde.models.MapConstellations` instead:
```python
# ❌ Wrong
from core.eve.models import Constellation

# ✅ Correct
from core.sde.models import MapConstellations
```

### Issue: Import errors about missing tables

**Cause**: The raw SDE file is missing or corrupted.

**Solution**: Re-download from garveen:
```bash
cd ~/data/evewire
wget -qO sde.sqlite.bz2 https://github.com/garveen/eve-sde-converter/releases/download/sde-3171578-01ec212/sde.sqlite.bz2
python3 -c "import bz2; bz2.open('sde.sqlite.bz2', 'rb').read(), open('eve_sde.sqlite3', 'wb').write(bz2.open('sde.sqlite.bz2').read())"
rm sde.sqlite.bz2
```

### Issue: Table `core_constellation` does not exist

**Cause**: Trying to use `core.eve.models.Constellation` which was never imported.

**Solution**: Use SDE browser models (`core.sde.models.MapConstellations`) which point to `evesde_mapconstellations`.

---

## File Locations

| Component | Location |
|-----------|----------|
| Raw SDE source | `~/data/evewire/eve_sde.sqlite3` |
| Django app database | `~/data/evewire/evewire_app.sqlite3` |
| App importer | `core/management/commands/import_sde.py` |
| Browser importer | `core/management/commands/import_sde_browser.py` |
| App models | `core/eve/models.py` |
| Browser models | `core/sde/models.py` |
| Live views (use browser models) | `core/live/views.py` |
| SDE browser views | `core/sde/views.py` |

---

## Related Documentation

- **Live Data Cron Schedule**: `docs/live-data-cron-schedule.md`
- **ESI Client**: `core/services/__init__.py` (ESIClient class)
- **Live Tasks**: `core/eve/tasks.py` (background refresh tasks)
