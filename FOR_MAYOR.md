# Message for Mayor

## Deployment Instructions

I've prepared `DEPLOYMENT.md` with full deployment instructions for the evewire services.

**Quick workflow when we push commits:**
```bash
cd /home/genie/gt/evewire/mayor/rig
git pull origin main
sudo systemctl restart evewire.service evewire-qcluster.service
```

## Recent Changes Deployed

1. **Skills page redesign** - Per-character skills with group headers
2. **Industry slot calculation** - Character model now has manufacturing/science/reaction slots
3. **ItemGroup population** - Added `populate_groups` command (run if needed)
4. **Multi-character fixes** - Fixed skills/implants/attributes views

**Current commit:** `2692751` and newer on main

## Service Status

Both services should be running:
- `evewire.service` - Django/gunicorn on port 8000
- `evewire-qcluster.service` - django-q2 background worker

Check with: `sudo systemctl status evewire evewire-qcluster`

## Architecture

- **crew/aura** - Development workspace (we commit here)
- **mayor/rig** - Production worktree (you pull and run services here)
- **origin/main** - GitHub repo (we push, you pull)

We're switching to PR workflow for feature development now.

Let me know if anything breaks!

-- Claude (crew/aura polecat)
