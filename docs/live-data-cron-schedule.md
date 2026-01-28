# Live Universe Browser - Cron Schedule

## Overview

The Live Universe Browser fetches dynamic data from ESI and caches it locally. Different data types have different refresh requirements based on how fast they change.

## Command Reference

```bash
cd /home/genie/gt/evewire/mayor/rig
.venv/bin/python manage.py fetch_live_data [options]
```

**Options:**
- `--all` - Fetch all data types
- `--lp-stores` - Fetch loyalty point stores
- `--incursions` - Fetch active incursions
- `--wars` - Fetch active wars
- `--sovereignty` - Fetch sov map + campaigns
- `--fw` / `--faction-warfare` - Fetch faction warfare data
- `--markets` - Fetch market summaries
- `--region <id>` - Specify region for markets (can repeat)
- `--quiet` - Suppress informational output

## Recommended Cron Schedule

### /etc/crontab or /etc/cron.d/evewire-live

```cron
# EVE Online Live Data Refresh
# Run as the evewire user (or whatever user runs the app)

# Incursions - Fastest changing (spawns/despawns)
*/10 * * * * cd /home/genie/gt/evewire/mayor/rig && .venv/bin/python manage.py fetch_live_data --incursions --quiet

# Sov Campaigns - Time-sensitive structure fights
*/15 * * * * cd /home/genie/gt/evewire/mayor/rig && .venv/bin/python manage.py fetch_live_data --sovereignty --quiet

# Wars - Active war status
*/20 * * * * cd /home/genie/gt/evewire/mayor/rig && .venv/bin/python manage.py fetch_live_data --wars --quiet

# Faction Warfare Systems - Ownership changes
*/30 * * * * cd /home/genie/gt/evewire/mayor/rig && .venv/bin/python manage.py fetch_live_data --fw --quiet

# Markets - Trade hub activity (Jita, Amarr, Dodixie, Rens)
0 * * * * cd /home/genie/gt/evewire/mayor/rig && .venv/bin/python manage.py fetch_live_data --markets --region 10000002 --region 10000043 --region 10000032 --region 10000030 --quiet

# Sov Map - System ownership (included with sov, but can run less frequently)
30 */2 * * * cd /home/genie/gt/evewire/mayor/rig && .venv/bin/python manage.py fetch_live_data --sovereignty --quiet

# LP Stores - Rarely changes (daily)
0 3 * * * cd /home/genie/gt/evewire/mayor/rig && .venv/bin/python manage.py fetch_live_data --lp-stores --quiet
```

## Data Type Details

| Data Type | ESI Endpoint | Refresh Interval | Reason |
|-----------|--------------|------------------|--------|
| **Incursions** | `GET /incursions/` | 10 minutes | Spawn/despawn regularly |
| **Sov Campaigns** | `GET /sovereignty/campaigns/` | 15 minutes | Time-sensitive fights |
| **Wars** | `GET /wars/` + details | 20 minutes | War status changes |
| **FW Systems** | `GET /fw/systems/` | 30 minutes | System plexing |
| **Markets** | `GET /markets/{region_id}/orders/` | Hourly | Trade activity |
| **Sov Map** | `GET /sovereignty/map/` | Every 2 hours | Slow ownership changes |
| **FW Stats** | `GET /fw/stats/` | Hourly | With sov command |
| **LP Stores** | `GET /loyalty/stores/` + offers | Daily | Rarely changes |

## Task Queue Behavior

The management command queues background tasks via django-q2. Tasks are executed with random jitter (0-60 seconds) to prevent thundering herd on ESI:

- **LP Stores**: ~4,464 individual corporation refreshes
- **Wars**: ~2,000 war detail fetches
- **Incursions**: Single task (clears and recreates)
- **Sov**: Single task for map, single for campaigns
- **FW**: Single task each for stats and systems
- **Markets**: One task per region

## Systemd Timer Alternative

If using systemd timers instead of cron:

### /etc/systemd/system/evewire-live-incursions.service
```ini
[Unit]
Description=EVE Online - Refresh Incursions
After=network.target

[Service]
Type=oneshot
User=evewire
WorkingDirectory=/home/genie/gt/evewire/mayor/rig
ExecStart=/home/genie/gt/evewire/mayor/rig/.venv/bin/python manage.py fetch_live_data --incursions --quiet
```

### /etc/systemd/system/evewire-live-incursions.timer
```ini
[Unit]
Description=Refresh EVE incursions every 10 minutes

[Timer]
OnCalendar=*:0/10
AccuracySec=30s

[Install]
WantedBy=timers.target
```

Create similar services/timers for other data types.

## Monitoring

Check task queue status:
```bash
# Check pending tasks
/home/genie/gt/evewire/mayor/rig/.venv/bin/python manage.py shell -c "
from django_q.models import Task
print('Pending tasks:', Task.objects.count())
"

# Check completed tasks
/home/genie/gt/evewire/mayor/rig/.venv/bin/python manage.py shell -c "
from django_q.models import Success
from datetime import timedelta
from django.utils import timezone
print('Success (last hour):', Success.objects.filter(stopped__gte=timezone.now()-timedelta(hours=1)).count())
"
```

## Initial Data Population

To populate all data for the first time:
```bash
cd /home/genie/gt/evewire/mayor/rig
.venv/bin/python manage.py fetch_live_data --all
```

This will queue ~6,500 tasks that execute over 1-2 hours due to jitter and ESI rate limiting.

## Notes

- All commands use `--quiet` to suppress output when run via cron
- Tasks are queued with random delays to prevent ESI rate limit issues
- The qcluster workers must be running for tasks to execute
- Check logs at `/home/genie/gt/evewire/mayor/rig/logs/evewire.log` for issues
