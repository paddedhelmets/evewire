# Evewire Deployment Guide for Mayor

## Overview

Evewire runs as two systemd services on the LAMP server:

- **evewire.service** - Django/gunicorn web app (port 8000)
- **evewire-qcluster.service** - django-q2 background task worker

## Architecture

```
origin/main (GitHub)
    ↓ pull
mayor/rig (worktree at /home/genie/gt/evewire/mayor/rig/)
    ↓ (runs services from here)
evewire.service → gunicorn → Django app
evewire-qcluster.service → django-q2 → background tasks
```

## Service Locations

**Services:** systemd (systemctl)
- **Config:** `/etc/systemd/system/evewire.service`
- **Config:** `/etc/systemd/system/evewire-qcluster.service`
- **Logs:** `journalctl -u evewire -f` and `journalctl -u evewire-qcluster -f`

**Codebase:** `/home/genie/gt/evewire/mayor/rig/`
- **Python venv:** `.venv/`
- **Database:** `db.sqlite3`
- **Logs dir:** `logs/`
- **Static files:** `staticfiles/`

**Development workspace:** `/home/genie/gt/evewire/crew/aura`
- Where polecats work on features
- Commits go to origin/main
- Mayor pulls from origin/main

## Deployment Process

When crew/aura pushes to `origin/main`, the mayor needs to:

```bash
cd /home/genie/gt/evewire/mayor/rig
git pull origin main
sudo systemctl restart evewire.service evewire-qcluster.service
```

## Environment Variables

The `.env` file in mayor/rig contains:
```
EVE_CLIENT_ID=56ab4dbedd3a48b0bed67876058f3f93
EVE_CLIENT_SECRET=*** (keep secret)
EVE_CALLBACK_URL=http://192.168.0.90:8000/oauth/callback/
```

## Service Management

**Check status:**
```bash
sudo systemctl status evewire.service
sudo systemctl status evewire-qcluster.service
```

**View logs:**
```bash
# Real-time
journalctl -u evewire -f
journalctl -u evewire-qcluster -f

# Recent 50 lines
journalctl -u evewire -n 50
```

**Restart services:**
```bash
sudo systemctl restart evewire.service
sudo systemctl restart evewire-qcluster.service
```

**Start/Stop:**
```bash
sudo systemctl start evewire.service
sudo systemctl stop evewire.service
```

## Database Location

The SQLite database is at: `/home/genie/gt/evewire/mayor/rig/db.sqlite3`

To run migrations:
```bash
.venv/bin/python manage.py migrate
```

## Static Files

After deployment, collect static files:
```bash
.venv/bin/python manage.py collectstatic --noinput
```

## Common Issues

**Service fails to start:**
- Check logs: `journalctl -u evewire -n 50`
- Common issue: code has syntax error or import issue

**White page / 500 error:**
- Check logs for exception traceback
- May need to restart services

**Outdated data:**
- Services cache some code, restart after pull
- Background tasks may need to finish

## Current State

- Branch: `main`
- Port: `8000`
- Access: `http://192.168.0.90:8000/`
- Database: SQLite (may need migration for schema changes)
- Virtual environment: `.venv/` (with uv-managed packages)
