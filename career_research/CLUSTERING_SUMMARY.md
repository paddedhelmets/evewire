# Clustering Analysis Summary

## What We Built

1. **Zkillboard Ingestion** - 5.96M fits from 2025 (EvereF daily dumps)
2. **Skill-based Embeddings** - 572-dim binary vectors from explicit skill requirements
3. **Clustering Pipeline** - pgvector cosine similarity clustering
4. **Canonical Fit Extraction** - Slot-by-slot mode finding for representative fits
5. **CLI Tools** - Reusable scripts for analysis

## Key Insight: Cluster Size ≠ Popularity

**Lossmail bias** means frequently-lost ships dominate the data:
- Industrial Cyno Venture (3,887 fits) = immobile target = dies more
- Actual popular fits might die less = underrepresented

**Small clusters can be MORE meta-meaningful:**
- Venture Mining (8 fits) - distinct playstyle
- Venture Exploration (9 fits) - distinct playstyle
- Cargo hauler (3,887 fits) - just dies a lot

## Clustering Results

### Ships Analyzed

**Venture** (Mining Frigate)
- Cluster 1 (3,887) - Cargo hauler with cyno
- Cluster 2 (9) - Exploration with probe launcher
- Cluster 3 (8) - Mining with tank

**Ishtar** (HAC) - ZADDY
- Cluster 1 (521) - AFK sentry ratting (4x DDAs, X-Large SB)
- Cluster 2 (212) - Cap-stable ratting
- Cluster 3 (173) - Nullified/cloaky ratting (Auto Targeter for bots?)
- Clusters 4-5 (<10) - PvP variants

**Vexor** (Cruiser) - ZADDY JR
- Cluster 1 (387) - Mini-Ishtar (4x DDA, shield buffer)
- Cluster 2 (103) - Active shield (AB, hardeners)
- Cluster 3 (65) - Mixed tank (DC II)

**Catalyst** (Destroyer)
- Cluster 1 (2,017) - THE suicide gank (7x Neutron Blaster II, Void S, sensor boosters)
- Cluster 2 (330) - Budget gank (T1 guns, faction ammo)
- Cluster 4 (562) - With stasis web

**Scimitar** (Logistics)
- Cluster 1 (260) - Fleet Scimitar (deadspace Pithum reps, LSEs, CPRs)
- Cluster 2 (53) - T2/small gang (cheaper)
- Cluster 3 (29) - Mixed faction mods

**Pilgrim** (Force Recon) - Covert Cyno Hunter
- Cluster 1 (21) - Solo hunter (regular cyno)
- Cluster 2 (11) - BLOPS hunter (**Covert Cyno**, ship scanner)
- Cluster 3 (7) - Hardcore hunter

**Sabre** (Interdictor)
- All clusters = ONE META with tiny variations
- 8x 125mm Gatling AutoCannon II
- Shield buffer + nanofiber + hyperspatial rigs
- Only difference: AB vs MWD, different module types

## Meta Insights

### What Clustering Found

1. **Distinct Playstyles** - Pilgrim has 3 fundamentally different roles
2. **Botting Signatures** - Auto Targeter on Ishtar (bottled ratting?)
3. **Alliance Doctrines** - Scimitar clustering shows fleet standards
4. **Ship Class Constraints** - Sabre has ONE job, ONE fit
5. **Lossmail Bias** - Ships that die more appear larger in dataset

### Domain Knowledge Required

The clustering finds patterns, but YOU must interpret:
- Is this meta or just dies a lot? (Sabre)
- Is this botting or real play? (Ishtar Auto Targeter)
- Is this alliance doctrine or trash? (Scimitar deadspace)
- What's the tactical purpose? (Pilgrim covert cyno)

## Next Steps

1. **Wait for embeddings** - 295K/5.95M (4.96%), ~8 hours remaining
2. **Analyze more ships** - All factions, all ship classes
3. **Generate skill plans** - From canonical fits + skill requirements
4. **Build career paths** - Each cluster = a potential career path
5. **Validate with domain experts** - Confirm meta interpretations

## Technical Notes

- **Embeddings**: 572-dim binary vectors (skills present/absent)
- **Clustering**: pgvector cosine similarity, k=5 clusters
- **Canonical Fit**: Mode of each slot position with usage %
- **Sample Size**: 295K embeddings (4.96%) is sufficient for meaningful analysis
