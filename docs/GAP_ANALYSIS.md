# Gap Analysis: Assets, Contracts, and Industry Features

**Analysis Date:** 2026-01-21
**Scope:** Assets, Contracts, and Industry features in evewire

## Executive Summary

| Feature | Status | Completion |
|---------|--------|------------|
| Assets | MOSTLY COMPLETE | ~80% |
| Contracts | COMPLETE | ~90% |
| Industry | DATA MODEL ONLY | ~20% |

**Critical Finding:** Industry has comprehensive data models but **zero UI implementation**.

---

## Assets (80% Complete)

### What Exists

**Model:** `CharacterAsset` (core/character/models.py:276)
- MPTT hierarchical tree support
- Fields: item_id, type_id, quantity, location_id, location_type, location_flag, is_singleton, is_blueprint_copy
- Methods: type_name, total_quantity, location_name, is_blueprint(), blueprint_type(), get_value()

**Views:**
- `assets_list` - Hierarchical tree display by location (views.py:1627)
- `assets_summary` - Per-location aggregates (views.py:1683)
- `fitted_ships` - Extracted ship fits from assets (views.py:1819)

**Templates:**
- assets_list.html
- assets_summary.html
- fitted_ships.html
- asset_row.html

**URL Routes:**
- /assets/ - List all assets by location
- /assets/summary/ - Aggregated view by location
- /assets/ships/ - Fitted ships extracted from assets

### Identified Gaps

1. **No filtering/search** on assets list (cannot find specific items)
2. **No blueprint-specific view** (BPO vs BPC separation)
3. **No asset value aggregation** by item type (what items are most valuable?)
4. **No asset export** functionality (CSV/XLSX)
5. **No reprocessing calculator** (what will I get if I reprocess?)

### Enhancement Opportunities

1. Add search bar to assets list (filter by name, type, location)
2. Create dedicated blueprints view (BPO list, BPC list with runs remaining)
3. Create "Top Items by Value" summary
4. Add export button to assets views
5. Add reprocessing yield calculator based on character skills

---

## Contracts (90% Complete)

### What Exists

**Models:** `Contract`, `ContractItem` (core/character/models.py:1007)
- Contract: type, status, title, availability, dates, parties, price, reward, collateral, buyout, volume
- ContractItem: item_id, type_id, quantity, is_included, is_singleton, raw_quantity
- Comprehensive properties: is_active, is_completed, is_failed, is_expired, expires_soon, total_value, items_count

**Views:**
- `contracts_list` - List with filtering (views.py:1544)
- `contract_detail` - Single contract with items (views.py:1785)

**Templates:**
- contracts.html
- contract_detail.html

**URL Routes:**
- /contracts/ - List all contracts with filters
- /contracts/<id>/ - Contract detail

**Filters Available:**
- Contract type (item_exchange, auction, courier, loan)
- Status (outstanding, in_progress, finished, etc.)
- Availability (public, personal, corporation, alliance)

### Identified Gaps

1. **No contract creation UI** (ESI scope is read-only, but could be added)
2. **No contract profitability analysis** (for completed buy/sell contracts)
3. **No contract export** functionality
4. **No bulk contract actions** (e.g., accept multiple outstanding contracts)

### Enhancement Opportunities

1. Add profitability indicator for completed contracts (compare item values to price paid)
2. Add contract export (CSV for accounting)
3. Add "Quick Accept" buttons for outstanding contracts
4. Add contract history search/filter by date range

---

## Industry (20% Complete - DATA MODEL ONLY)

### What Exists

**Model:** `IndustryJob` (core/character/models.py:829) - **Comprehensive but NO UI**
- Fields: job_id, activity_id, status, blueprint_id, blueprint_type_id, product_type_id, station_id, solar_system_id, start_date, end_date, runs, cost, probability, attempts, success
- Properties: activity_name, status_name, blueprint_type_name, product_name, is_active, is_completed, progress_percent, time_remaining, is_expiring_soon

**Character Model Industry Utilities** (core/models.py:277-356):
- `manufacturing_slots` - Calculate max slots from Industry skill
- `research_slots` - Calculate max slots from Advanced Industry skill
- `active_manufacturing_jobs` - Count active manufacturing jobs
- `active_research_jobs` - Count active research jobs
- `manufacturing_utilization` - Manufacturing slot utilization %
- `research_utilization` - Research slot utilization %
- `is_manufacturing_nearly_full` - Check if >80% utilized
- `is_research_nearly_full` - Check if >80% utilized
- `has_available_manufacturing_slot` - Check for free slot
- `has_available_research_slot` - Check for free slot

**Industry Job Activities Supported:**
- 1: Manufacturing
- 2: Researching Technology (TE)
- 3: Researching Technology (TE - legacy)
- 4: Researching Material Efficiency (ME)
- 5: Copying
- 6: Duplicating (legacy)
- 7: Reverse Engineering
- 8: Invention

**Job Status Values:**
- 1: active
- 2: paused
- 102: cancelled
- 104: delivered
- 105: failed
- 999: unknown

### What's Missing - NO UI EXISTS

1. **No industry jobs view/template** - Cannot list jobs
2. **No industry job detail view** - Cannot see job details
3. **No industry summary/stats view** - Cannot see slot utilization
4. **No industry URL routes** - Cannot access via browser
5. **No dashboard integration** - No industry stats on dashboard
6. **No blueprint management** - Cannot view blueprints separately
7. **No industry calendar** - Cannot see job completion timeline

### Critical Missing Views

| View | Purpose | Priority |
|------|---------|----------|
| Industry Jobs List | Show all jobs with filtering (active, completed, by activity) | HIGH |
| Industry Job Detail | Single job with blueprint/product info, progress bar | HIGH |
| Industry Summary | Slot utilization, active jobs by type, completion queue | HIGH |
| Blueprint Library | List all BPOs/BPCs with locations and ME/TE levels | MEDIUM |
| Industry Calendar | Timeline view of job completions | MEDIUM |

### Suggested URL Routes

```
/industry/                          # Industry summary (slot utilization)
/industry/jobs/                     # List all industry jobs
/industry/jobs/<int:job_id>/        # Job detail
/industry/jobs/?status=active       # Filter by status
/industry/jobs/?activity=manufacturing  # Filter by activity
/industry/blueprints/               # Blueprint library
/industry/calendar/                 # Job completion timeline
```

### Suggested Dashboard Enhancements

Add to dashboard.html:
```html
<div class="card">
    <h3>Industry Slots</h3>
    <ul>
        <li>Manufacturing: {{ character.active_manufacturing_jobs }}/{{ character.manufacturing_slots }}
            ({{ character.manufacturing_utilization|floatformat:0 }}%)</li>
        <li>Research: {{ character.active_research_jobs }}/{{ character.research_slots }}
            ({{ character.research_utilization|floatformat:0 }}%)</li>
    </ul>
    <a href="{% url 'core:industry_jobs' %}">View Industry Jobs</a>
</div>
```

---

## Summary by Feature Area

### Assets
- ✅ Data model complete
- ✅ Basic views exist
- ✅ Location-based organization
- ⚠️ Missing: filtering, blueprints view, export, reprocessing calculator

### Contracts
- ✅ Data model complete
- ✅ Full CRUD (read-only via ESI)
- ✅ Filtering by type, status, availability
- ⚠️ Missing: profitability analysis, export, bulk actions

### Industry
- ✅ Data model complete
- ✅ Character slot calculation utilities
- ❌ NO UI - zero views/templates
- ❌ NO URL routes
- ❌ NO dashboard integration

---

## Recommended Implementation Priority

### Phase 1: Industry Core (CRITICAL)
1. Industry jobs list view with filtering
2. Industry job detail view
3. Industry summary view (slot utilization)
4. Add URL routes for industry
5. Add industry stats to dashboard

### Phase 2: Industry Enhancement
1. Blueprint library view
2. Industry calendar/timeline
3. Job completion notifications

### Phase 3: Assets Enhancement
1. Add filtering/search to assets list
2. Create blueprints view (separate from general assets)
3. Add asset value aggregation by type

### Phase 4: Contracts Enhancement
1. Add profitability analysis for completed contracts
2. Add export functionality
3. Add bulk actions for outstanding contracts

---

## Data Model Assessment

All three feature areas have **complete and well-designed data models**. The gaps are purely in the **presentation layer (views, templates, URLs)**.

**Estimated effort:**
- Industry Phase 1: ~4-6 hours (views + templates + routes)
- Industry Phase 2: ~2-3 hours
- Assets Phase 3: ~2-3 hours
- Contracts Phase 4: ~1-2 hours

**Total:** ~9-14 hours to complete all gaps
