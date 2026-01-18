# evewire Discovery Phase

**Date**: 2026-01-17
**Author**: evewire/crew/aura
**Reference**: Original evething at `reference/evething/`

---

## Executive Summary

evething was a Django-based EVE Online management tool using the now-deprecated XML API. This document analyzes its features, maps them to modern ESI endpoints, and proposes an architecture for evewire - a from-scratch rebuild.

---

## 1. Feature Inventory

### 1.1 Core Features (evething provided)

| Priority | Feature | Description | User Value |
|----------|---------|-------------|------------|
| **P0** | Multi-Character Dashboard | Overview of all pilots with training status, wallet balances | Essential - primary use case |
| **P0** | Character Sheet | Skills, attributes, implants, clone info | Essential for pilot management |
| **P0** | Wallet Tracking | Balance, journal entries, transactions | Financial management |
| **P0** | Asset Management | Browse assets across all characters/corps | Core inventory tracking |
| **P1** | Market Orders | Active buy/sell orders, slot counts | Active traders need this |
| **P1** | Industry Jobs | Manufacturing, research, invention tracking | Industrialists need this |
| **P1** | Skill Queue | Current training, completion times | Training optimization |
| **P1** | Contracts | Courier, item exchange, auction contracts | Trade logistics |
| **P2** | Trade Analytics | Profit/loss, monthly summaries, campaigns | Advanced trading insights |
| **P2** | Blueprint Management | BPO/BPC tracking, efficiency, calculator | Industrial optimization |
| **P2** | Planetary Interaction | Colony tracking, pin status | PI monitoring |
| **P2** | Mail | In-game mail viewer | Convenience feature |
| **P3** | Skill Plans | Custom skill training plans | Planning tool |
| **P3** | Standings | Faction/corporation standings | Reference info |

### 1.2 evething Architecture Highlights

**Good patterns to preserve:**
- Multi-character aggregation (see all pilots at once)
- API key abstraction (one credential, multiple characters)
- Async background sync via Celery task queue
- Configurable privacy/visibility per character
- Theme support (user customization)

**Pain points to address:**
- Python 2.7 / Django 1.7 (severely outdated)
- Celery complexity for simple background jobs
- XML API parsing overhead (no longer relevant)
- No real-time updates (polling only)
- Heavy database queries for asset summaries

---

## 2. ESI Endpoint Mapping

ESI provides 195 endpoints (76 public, 119 authenticated) as of 2025.

### 2.1 Feature → Endpoint Mapping

| evething Feature | ESI Endpoint | Scope Required | Cache Timer |
|------------------|--------------|----------------|-------------|
| **Character Info** | `GET /characters/{id}/` | Public | 24h |
| **Character Portrait** | `GET /characters/{id}/portrait/` | Public | 24h |
| **Skills** | `GET /characters/{id}/skills/` | `esi-skills.read_skills.v1` | 120s |
| **Skill Queue** | `GET /characters/{id}/skillqueue/` | `esi-skills.read_skillqueue.v1` | 120s |
| **Attributes** | `GET /characters/{id}/attributes/` | `esi-skills.read_skills.v1` | 120s |
| **Implants** | `GET /characters/{id}/implants/` | `esi-clones.read_implants.v1` | 120s |
| **Clones** | `GET /characters/{id}/clones/` | `esi-clones.read_clones.v1` | 120s |
| **Wallet Balance** | `GET /characters/{id}/wallet/` | `esi-wallet.read_character_wallet.v1` | 120s |
| **Wallet Journal** | `GET /characters/{id}/wallet/journal/` | `esi-wallet.read_character_wallet.v1` | 1h |
| **Wallet Transactions** | `GET /characters/{id}/wallet/transactions/` | `esi-wallet.read_character_wallet.v1` | 1h |
| **Character Assets** | `GET /characters/{id}/assets/` | `esi-assets.read_assets.v1` | 1h |
| **Asset Locations** | `POST /characters/{id}/assets/locations/` | `esi-assets.read_assets.v1` | - |
| **Asset Names** | `POST /characters/{id}/assets/names/` | `esi-assets.read_assets.v1` | - |
| **Market Orders** | `GET /characters/{id}/orders/` | `esi-markets.read_character_orders.v1` | 1h |
| **Order History** | `GET /characters/{id}/orders/history/` | `esi-markets.read_character_orders.v1` | 1h |
| **Industry Jobs** | `GET /characters/{id}/industry/jobs/` | `esi-industry.read_character_jobs.v1` | 5m |
| **Contracts** | `GET /characters/{id}/contracts/` | `esi-contracts.read_character_contracts.v1` | 5m |
| **Contract Items** | `GET /characters/{id}/contracts/{id}/items/` | `esi-contracts.read_character_contracts.v1` | - |
| **Blueprints** | `GET /characters/{id}/blueprints/` | `esi-characters.read_blueprints.v1` | 1h |
| **PI Colonies** | `GET /characters/{id}/planets/` | `esi-planets.manage_planets.v1` | 10m |
| **PI Colony Details** | `GET /characters/{id}/planets/{id}/` | `esi-planets.manage_planets.v1` | 10m |
| **Mail Headers** | `GET /characters/{id}/mail/` | `esi-mail.read_mail.v1` | 30s |
| **Mail Body** | `GET /characters/{id}/mail/{id}/` | `esi-mail.read_mail.v1` | - |
| **Mailing Lists** | `GET /characters/{id}/mail/lists/` | `esi-mail.read_mail.v1` | 2m |
| **Standings** | `GET /characters/{id}/standings/` | `esi-characters.read_standings.v1` | 1h |

### 2.2 Corporation Endpoints

| Feature | ESI Endpoint | Scope Required |
|---------|--------------|----------------|
| Corp Info | `GET /corporations/{id}/` | Public |
| Corp Assets | `GET /corporations/{id}/assets/` | `esi-assets.read_corporation_assets.v1` |
| Corp Wallets | `GET /corporations/{id}/wallets/` | `esi-wallet.read_corporation_wallets.v1` |
| Corp Journal | `GET /corporations/{id}/wallets/{div}/journal/` | `esi-wallet.read_corporation_wallets.v1` |
| Corp Orders | `GET /corporations/{id}/orders/` | `esi-markets.read_corporation_orders.v1` |
| Corp Industry | `GET /corporations/{id}/industry/jobs/` | `esi-industry.read_corporation_jobs.v1` |
| Corp Contracts | `GET /corporations/{id}/contracts/` | `esi-contracts.read_corporation_contracts.v1` |
| Corp Blueprints | `GET /corporations/{id}/blueprints/` | `esi-corporations.read_blueprints.v1` |

### 2.3 Universe/Reference Data (Public)

| Data | Endpoint |
|------|----------|
| Item Types | `GET /universe/types/{id}/` |
| Systems | `GET /universe/systems/{id}/` |
| Stations | `GET /universe/stations/{id}/` |
| Regions | `GET /universe/regions/{id}/` |
| Market Prices | `GET /markets/prices/` |
| Market History | `GET /markets/{region}/history/` |

### 2.4 Features That Cannot Be Replicated

| evething Feature | Reason |
|------------------|--------|
| API Key Management | ESI uses OAuth2 per-character, no "API keys" |
| Account-level access | Must authorize each character individually |
| Bookmarks | Endpoint removed March 2025 |
| Opportunities | Endpoint removed March 2025 |

---

## 3. Architecture Recommendation

### 3.1 Constraints

- **No Rust or Go** (owner preference for contributor accessibility)
- **Performance** focused on web response times (ESI latency is external)
- **Modern APIs** (OAuth2/ESI)
- **Open source friendly** - easy for community to contribute and self-host
- **Clean, maintainable** codebase

### 3.2 Options Evaluated

| Stack | Pros | Cons |
|-------|------|------|
| **Python + Django** | Huge community, EVE ecosystem precedent (Alliance Auth), built-in admin, battle-tested | Sync by default (async requires work) |
| **Python + FastAPI** | Async native, great typing, mature ecosystem | Less familiar to EVE self-hosters |
| **TypeScript + Bun** | Very fast, great DX, modern | Newer ecosystem, less familiar |
| **Go/Rust** | Maximum performance | Contributor accessibility concerns |

### 3.3 Decision: Python + Django ✓

**See ADR**: `ev-kll` - ADR-001: Django as web framework

**Why Django:**

1. **Community familiarity**: Django has a massive community. For an open-source project intended for self-hosting, contributor accessibility matters more than raw performance.

2. **EVE ecosystem precedent**: Alliance Auth (the major EVE corp/alliance management tool) uses Django. EVE players who self-host are likely already familiar with Django deployment patterns.

3. **Built-in admin**: Django admin panel is genuinely useful for debugging data issues during development and for power users managing their data.

4. **Adequate performance**: While not the fastest, Django's performance is sufficient. Our bottlenecks will be:
   - ESI API latency (external, can't optimize)
   - Database query design (good schema > fast language)

5. **Mature ecosystem**: django-oauth-toolkit, django-q2, django-mptt, well-documented deployment patterns.

### 3.4 Stack Details

- **Django 5.x** with Python 3.11+
- **PostgreSQL** for production (SQLite acceptable for local dev)
- **Django ORM** with django-mptt or django-tree-queries for asset hierarchy
- **Background tasks**: django-q2 (simpler than Celery) or Celery if needed
- **Frontend**: Server-rendered templates + htmx for interactivity (evaluate SPA later if needed)
- **Authentication**: django-oauth-toolkit for EVE SSO integration

### 3.5 Proposed Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     evewire                             │
├─────────────────────────────────────────────────────────┤
│  Frontend                                               │
│  - Django templates + htmx for interactivity            │
│  - Tailwind CSS or Bootstrap for styling                │
│  - Minimal JavaScript, progressive enhancement          │
├─────────────────────────────────────────────────────────┤
│  Django Application                                     │
│  - Views: Dashboard, Character, Assets, Orders          │
│  - EVE SSO OAuth2 via django-oauth-toolkit              │
│  - Django Admin for power users and debugging           │
├─────────────────────────────────────────────────────────┤
│  Service Layer                                          │
│  - ESI Client (typed wrapper around ESI endpoints)      │
│  - Token Manager (refresh handling, multi-character)    │
│  - Data Aggregator (combine data across characters)     │
├─────────────────────────────────────────────────────────┤
│  Background Sync                                        │
│  - django-q2 or Celery for task queue                   │
│  - Scheduled ESI pulls (respect cache timers)           │
│  - Manual sync triggers (MVP: manual only)              │
├─────────────────────────────────────────────────────────┤
│  Data Layer                                             │
│  - PostgreSQL (production) / SQLite (dev)               │
│  - Django ORM with django-mptt for asset hierarchy      │
│  - ESI response caching (respect Expires headers)       │
└─────────────────────────────────────────────────────────┘
```

### 3.6 Key Design Decisions

1. **Local-first option**: SQLite allows running as a local tool (like original evething intent) without server infrastructure.

2. **Multi-tenant ready**: PostgreSQL path supports shared hosting for multiple users.

3. **Respect ESI cache timers**: Store `expires` header, don't re-fetch before cache expires. This is both polite and efficient.

4. **Character-centric tokens**: Each character needs their own OAuth2 token. Store refresh tokens securely, access tokens in memory.

5. **Incremental sync**: Don't bulk-fetch everything. Sync what's needed, when needed, respecting rate limits.

---

## 4. MVP Proposal

### 4.1 MVP Feature Set (v0.1)

A useful first version needs these core features:

| Feature | Why MVP |
|---------|---------|
| **EVE SSO Login** | Can't do anything without auth |
| **Multi-character support** | Core value prop of evething |
| **Dashboard** | Overview of all characters |
| **Wallet balance** | Quick financial check |
| **Skill queue** | What's training, when done |
| **Assets** | What do I own, where |
| **Market orders** | Active orders status |

### 4.2 MVP Scope (Explicit)

**In scope:**
- Add/remove EVE characters via OAuth2
- Dashboard showing all characters
- Per-character: wallet, skills, skill queue, assets, orders
- Basic filtering (assets by location, orders by type)
- Manual refresh button (respecting cache timers)
- Dark/light theme

**Out of scope for v0.1:**
- Corporation data (add in v0.2)
- Industry jobs
- Contracts
- Planetary interaction
- Mail
- Blueprint calculator
- Trade analytics
- Background auto-sync
- Skill plans

### 4.3 MVP Data Model

```typescript
// Core entities
User {
  id: string
  created_at: timestamp
  settings: json // theme, preferences
}

Character {
  id: number // EVE character ID
  user_id: string
  name: string
  corporation_id: number
  alliance_id?: number
  refresh_token: encrypted_string
  token_expires: timestamp
  last_sync: timestamp
}

// Cached ESI data
CharacterSkills {
  character_id: number
  total_sp: number
  unallocated_sp: number
  skills: json // skill_id -> {level, sp}
  synced_at: timestamp
}

CharacterAssets {
  character_id: number
  assets: json // full asset tree
  synced_at: timestamp
}

// ... similar for wallet, orders, etc.
```

### 4.4 MVP Milestones

1. **M1: Auth & Characters**
   - EVE SSO OAuth2 flow
   - Add/remove characters
   - Token refresh logic

2. **M2: Basic Data Display**
   - Fetch skills, wallet, assets from ESI
   - Store in database
   - Display on dashboard

3. **M3: Orders & Polish**
   - Market orders display
   - Asset/order filtering
   - Theme support
   - Error handling

---

## 5. Open Questions (Updated)

### Resolved ✓

1. **Stack**: Django selected (community accessibility, Alliance Auth precedent)
2. **Frontend**: Server-rendered templates + htmx (start simple, SPA later if needed)
3. **Deployment**: Support both local (SQLite) and server (PostgreSQL)

### Still Open

1. **Multi-user scope**: Personal tool only, or support multiple users on one instance?
   - Affects: user isolation, admin features, registration flow

2. **Corporation support depth**: MVP excludes corp data, but for v0.2:
   - Full corp wallet/assets? Or just "my alt's corp" visibility?
   - Director-level vs member-level access?

3. **Background sync**: MVP is manual-only. For v0.2+:
   - How aggressive should auto-sync be?
   - User-configurable intervals?

4. **Priority features**: Any P2/P3 features that should move up?
   - Industry jobs? (popular with builders)
   - Contracts? (essential for haulers)
   - PI? (passive income tracking)

---

## 6. References

- [EVE SSO Documentation](https://developers.eveonline.com/docs/services/sso/)
- [ESI Documentation](https://docs.esi.evetech.net/)
- [ESI Endpoint Browser](https://esi.evetech.net/ui/)
- [EVE University ESI Guide](https://wiki.eveuniversity.org/EVE_Swagger_Interface)
- [EsiPy (Python ESI Library)](https://kyria.github.io/EsiPy/)
- [Bun Runtime](https://bun.sh/)
- [Hono Framework](https://hono.dev/)
- [Drizzle ORM](https://orm.drizzle.team/)
- Original evething: `reference/evething/` in this repo

---

## 7. Project Tracking

**MVP Epic**: `ev-9xi` - evewire MVP (v0.1)

**Milestones**:
- `ev-5y7` - M1: Project Bootstrap & Auth
- `ev-27z` - M2: Data Models & ESI Client
- `ev-3qt` - M3: Dashboard & Character Views
- `ev-d8e` - M4: Assets & Orders
- `ev-7ib` - M5: Polish & Deploy

**Architecture Decisions**:
- `ev-kll` - ADR-001: Django as web framework

---

*Discovery phase complete. Architecture decided. MVP milestones defined. Ready to begin M1 implementation.*
