# Career Research

Synthesizing new information from EVE Online data to rebuild the certificate system.

> **Note**: Uses underscore (`career_research`) not hyphen (`career-research`) due to Python module naming rules.

## What This Does

1. **Killmail Ingestion** - Pull fits from zkillboard API
2. **Fit → Skills Resolution** - Compute required skills from fits (including fitting skills)
3. **Fit Clustering** - Group similar fits to find the "meta"
4. **Canonical Skill Plans** - Generate empirically-derived career paths

## Architecture

```
career_research/   # Note: underscore, not hyphen (Python naming)
├── eos/           # Fitting engine from pyfa (LGPL)
├── zkillboard/    # Killmail ingestion
├── fit_resolver/  # Fit → skills conversion
├── clustering/    # Fit similarity & grouping
├── skill_plans/   # Plan generation
└── output/        # Canonical plans (JSON, ready for import)
```

## Using eos

The `eos/` directory is the fitting engine from [pyfa](https://github.com/pyfa-org/Pyfa).
It's licensed under LGPL v3.

To set up the eos database:
```bash
cd eos
python db_update.py
```

This creates `eve.db` with pre-computed skill requirements.

## Deployment

This directory is **excluded from production deployment**. It's research tooling, not
part of the web application.
