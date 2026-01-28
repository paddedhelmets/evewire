# Evewire

EVE Online Pilot Management Tool - A Django application for character tracking, skill planning, asset management, fittings, and more.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Database Setup](#database-setup)
- [SDE Import](#sde-import)
- [Running the Application](#running-the-application)
- [Background Workers](#background-workers)
- [Scheduled Tasks](#scheduled-tasks)
- [Production Deployment](#production-deployment)
- [Management Commands](#management-commands)
- [Troubleshooting](#troubleshooting)

## Features

- **Character Management**: Add multiple characters, track skills, assets, wallet, orders
- **Skill Plans**: Create and track training plans with prerequisite detection
- **Fittings**: Import EFT/DNA fittings, check fleet readiness across your assets
- **Asset Browser**: Navigate fitted ships, locate items across stations
- **Live Universe Data**: Incursions, faction warfare, sovereignty, wars, markets
- **SDE Browser**: Complete EVE Static Data Export reference
- **Theme System**: Light, Dark, Solarized Light/Dark themes

## Requirements

- Python 3.12+
- SQLite (default) or PostgreSQL 14+
- EVE SSO Client ID and Secret (from [developers.eveonline.com](https://developers.eveonline.com/))

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/paddedhelmets/evewire.git
cd evewire/mayor/rig
```

### 2. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required variables:

```bash
# Django Settings
SECRET_KEY=generate-a-secure-random-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.com

# Database (SQLite default)
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=~/data/evewire/evewire_app.sqlite3

# OR PostgreSQL (recommended for production)
# DB_ENGINE=django.db.backends.postgresql
# DB_NAME=evewire
# DB_USER=evewire
# DB_PASSWORD=your-password
# DB_HOST=localhost
# DB_PORT=5432

# EVE SSO (Required)
EVE_CLIENT_ID=your-client-id
EVE_CLIENT_SECRET=your-client-secret
EVE_CALLBACK_URL=https://your-domain.com/oauth/callback/

# ESI Settings
ESI_COMPATIBILITY_DATE=2024-01-01

# Django Q2 (Background Workers)
Q_WORKERS=4
Q_TIMEOUT=300
```

### Generate a Secret Key

```bash
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### EVE SSO Setup

1. Visit [developers.eveonline.com](https://developers.eveonline.com/)
2. Create a new application
3. Set **Callback URL**: `https://your-domain.com/oauth/callback/`
4. Required scopes (minimum):
   - `esi-universe.read_structures.v1`
   - `esi-assets.read_assets.v1`
   - `esi-skills.read_skills.v1`
   - `esi-clones.read_clones.v1`
   - `esi-location.read_location.v1`
   - `esi-wallet.read_wallet.v1`
   - `esi-markets.read_character_orders.v1`
   - `esi-contracts.read_character_contracts.v1`
   - `esi-industry.read_character_jobs.v1`

## Database Setup

### SQLite (Default)

```bash
mkdir -p ~/data/evewire
python manage.py migrate
```

### PostgreSQL

```bash
createdb evewire
python manage.py migrate
```

### Create Superuser

```bash
python manage.py createsuperuser
```

## SDE Import

Evewire uses EVE Static Data Export (SDE) from [garveen/eve-sde-converter](https://github.com/garveen/eve-sde-converter).

### Import Core SDE Tables

Required for app functionality (skill plans, fittings, etc.):

```bash
python manage.py import_sde
```

This imports ~9 core tables:
- `invTypes`, `invGroups`, `invCategories` (item catalog)
- `dgmAttributeTypes`, `dgmTypeAttributes` (item attributes)
- `chrFactions` (faction info)
- `mapSolarSystems`, `mapRegions` (universe map)
- `staStations` (stations)

### Import SDE Browser Tables

Optional, for full SDE reference:

```bash
python manage.py import_sde_browser
```

This imports 100+ tables for complete SDE browsing.

### SDE Import Options

```bash
# Import specific tables
python manage.py import_sde_browser --tables=invTypes,invGroups

# Import all available tables
python manage.py import_sde_browser --all

# List available tables
python manage.py import_sde_browser --list

# Force re-import
python manage.py import_sde --force

# Use specific SDE version
python manage.py import_sde --sde-version=3171578-01ec212
```

### SDE Custom Data Fixes

Two custom data fixes are applied automatically:

1. **FactionID Sideload**: The garveen SDE converter includes `factionID` column in `crpNPCCorporations` but leaves it empty. We sideload 273 corporation-faction mappings from `core/data/corp_faction_ids.sql`. Applied automatically by `import_sde_browser`.

2. **LP Store Whitelist**: Only 213 NPC corporations have loyalty stores. See `core/eve/lp_store_whitelist.txt` for the list. Used by `refresh_all_lp_stores()`.

## Running the Application

### Development Server

```bash
python manage.py runserver
```

### Production (gunicorn)

```bash
gunicorn evewire.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

### With nginx (Recommended)

Example nginx config:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /path/to/evewire/static/;
    }
}
```

## Background Workers

Evewire uses **django-q2** for asynchronous tasks (structure lookups, LP store fetches, etc.).

### Start QCluster

```bash
python manage.py qcluster
```

### Worker Scaling

- Development: 1-2 workers
- Small deployments (1-10 users): 2-4 workers
- Medium deployments (10-50 users): 4-8 workers
- Large deployments (50+ users): 8+ workers

Configure via `Q_WORKERS` environment variable.

### systemd Service

Create `/etc/systemd/system/evewire-qcluster.service`:

```ini
[Unit]
Description=Evewire QCluster
After=network.target

[Service]
Type=simple
User=evewire
WorkingDirectory=/path/to/evewire/mayor/rig
Environment="PATH=/path/to/evewire/mayor/rig/.venv/bin"
ExecStart=/path/to/evewire/mayor/rig/.venv/bin/python manage.py qcluster
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable evewire-qcluster
sudo systemctl start evewire-qcluster
```

### Redis (Optional Multi-Worker)

For multi-worker deployments, add Redis for task brokering:

```bash
# .env
REDIS_URL=redis://localhost:6379/0
```

## Scheduled Tasks

Evewire uses **cron** (or systemd timers) for scheduled ESI sync jobs. The django-q2 scheduler is disabled.

### Character Sync Jobs

| Task | Command | Interval | What It Syncs |
|------|---------|----------|---------------|
| Metadata | `python manage.py refresh_characters --metadata` | 10 minutes | Location, wallet, orders, contracts, jobs |
| Assets | `python manage.py refresh_characters --assets` | 1 hour | Asset tree (ships, modules, items) |
| Skills | `python manage.py refresh_characters --skills` | 30 minutes | Skills, queue, attributes, implants |

### Structure Sync

```bash
python manage.py refresh_structures
```

Interval: 7 days for OK, 1 hour for errors.

### Live Universe Data

```bash
python manage.py fetch_live_data --all
```

| Data Type | Flag | Interval |
|-----------|------|----------|
| Incursions | `--incursions` | 10 minutes |
| Sov Campaigns | `--sovereignty` | 15 minutes |
| Wars | `--wars` | 20 minutes |
| FW Systems | `--fw-systems` | 30 minutes |
| Markets | `--markets --region 10000002` | Hourly |
| Sov Map | `--sov-map` | 2 hours |
| FW Stats | `--fw-stats` | Hourly |
| LP Stores | `--lp-stores` | Daily |

### Example Crontab

```cron
# Character metadata (every 10 min)
*/10 * * * * cd /path/to/evewire/mayor/rig && .venv/bin/python manage.py refresh_characters --metadata

# Character assets (hourly)
0 * * * * cd /path/to/evewire/mayor/rig && .venv/bin/python manage.py refresh_characters --assets

# Character skills (every 30 min)
*/30 * * * * cd /path/to/evewire/mayor/rig && .venv/bin/python manage.py refresh_characters --skills

# Structures (daily)
0 3 * * * cd /path/to/evewire/mayor/rig && .venv/bin/python manage.py refresh_structures

# Incursions (every 10 min)
*/10 * * * * cd /path/to/evewire/mayor/rig && .venv/bin/python manage.py fetch_live_data --incursions

# LP stores (daily)
0 4 * * * cd /path/to/evewire/mayor/rig && .venv/bin/python manage.py fetch_live_data --lp-stores
```

### systemd Timers (Alternative to Cron)

Create `/etc/systemd/system/evewire-refresh-characters.service`:

```ini
[Unit]
Description=Evewire Character Refresh
After=network.target

[Service]
Type=oneshot
User=evewire
WorkingDirectory=/path/to/evewire/mayor/rig
ExecStart=/path/to/evewire/mayor/rig/.venv/bin/python manage.py refresh_characters
```

Create `/etc/systemd/system/evewire-refresh-characters.timer`:

```ini
[Unit]
Description=Evewire Character Refresh Timer

[Timer]
OnBootSec=10min
OnUnitActiveSec=10min

[Install]
WantedBy=timers.target
```

Enable:

```bash
sudo systemctl enable evewire-refresh-characters.timer
sudo systemctl start evewire-refresh-characters.timer
```

## Production Deployment

### Checklist

- [ ] Set `DEBUG=False`
- [ ] Set `SECRET_KEY` to a secure random value
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set `HTTPS_ONLY=True` behind SSL terminator
- [ ] Use PostgreSQL for database
- [ ] Run `python manage.py collectstatic`
- [ ] Configure gunicorn workers (CPU count * 2 + 1)
- [ ] Configure nginx reverse proxy
- [ ] Enable qcluster systemd service
- [ ] Configure cron/systemd timers for ESI sync
- [ ] Set log level to `INFO` or `WARNING`

### Static Files

```bash
python manage.py collectstatic --noinput
```

Serve via nginx or Whitenoise.

### Logging

Logs written to `logs/evewire.log` with rotation (10MB per file, 5 backups).

Configure via `DJANGO_LOG_LEVEL` environment variable.

## Management Commands

### SDE Import

```bash
python manage.py import_sde                 # Import core SDE tables
python manage.py import_sde_browser         # Import SDE browser tables
```

### Live Data

```bash
python manage.py fetch_live_data --all                      # All live data
python manage.py fetch_live_data --incursions               # Incursions only
python manage.py fetch_live_data --markets --region 10000002 # Specific region
```

### Character/Structure Sync

```bash
python manage.py refresh_characters                          # All data
python manage.py refresh_characters --metadata              # Metadata only
python manage.py refresh_characters --assets                # Assets only
python manage.py refresh_characters --skills                # Skills only
python manage.py refresh_structures                         # All structures
python manage.py refresh_structures --id 12345              # Specific structure
```

### Fitting Import

```bash
python manage.py import_fittings <eft_file.txt>             # Import EFT format
python manage.py import_canonical_fittings                  # From zkill clustering
python manage.py import_markdown_fittings                   # From markdown
python manage.py import_meta_fits                           # Import meta fits
```

### Skill Plans

```bash
python manage.py seed_skillplans                            # Create sample plans
python manage.py import_reference_plans                     # Import reference plans
python manage.py reorder_skill_plans                        # Reorder display
```

### Utilities

```bash
python manage.py createsuperuser                            # Create admin user
python manage.py changepassword <username>                  # Change password
python manage.py shell                                      # Django shell
python manage.py dbshell                                    # Database shell
python manage.py showmigrations                             # Show migrations
python manage.py sqlmigrate core 0001                       # Show SQL for migration
```

## Troubleshooting

### QCluster Not Processing Tasks

```bash
# Check if qcluster is running
ps aux | grep qcluster

# Check for errors in logs
tail -f logs/evewire.log

# Check task queue
python manage.py shell
>>> from django_q.models import Task
>>> Task.objects.count()
```

### SDE Import Fails

```bash
# Test SDE database connectivity
python manage.py import_sde --dry-run

# Use specific SDE version
python manage.py import_sde --sde-version=3171578-01ec212
```

### ESI Rate Limiting

Evewire's ESI client automatically backs off at 20 remaining requests. Adjust jitter ranges in `core/eve/tasks.py` if needed.

### Database Locked (SQLite)

```bash
# Check for long-running transactions
python manage.py dbshell
> PRAGMA busy_timeout;
> .timeout 30000

# Or switch to PostgreSQL for production
```

### Token Refresh Fails

Characters with invalid tokens will show errors in logs. Re-authenticate via:
1. Log in as the user
2. Visit `/characters/`
3. Click "Reauthenticate" next to the character

## License

[Your License Here]

## Support

For issues, questions, or contributions, please visit [GitHub Issues](https://github.com/paddedhelmets/evewire/issues).
