"""
Live Universe Browser - Views for real-time ESI data.

This module provides views for browsing dynamic EVE universe data
from ESI, supplementing the static SDE browser.

Route prefix: /live/
"""

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta


def live_index(request):
    """Live browser homepage with quick stats."""
    from core.eve.models import CorporationLPStoreInfo, ActiveIncursion, ActiveWar
    from core.eve.models import SovCampaign, FactionWarfareSystem

    # Get quick stats
    lp_store_count = CorporationLPStoreInfo.objects.filter(
        has_loyalty_store=True
    ).count()

    incursion_count = ActiveIncursion.objects.filter(
        last_sync_status='ok'
    ).count()

    war_count = ActiveWar.objects.filter(
        is_active=True
    ).count()

    campaign_count = SovCampaign.objects.filter(
        last_updated__gte=timezone.now() - timedelta(hours=24)
    ).count()

    fw_system_count = FactionWarfareSystem.objects.count()

    return render(request, 'core/live/index.html', {
        'lp_store_count': lp_store_count,
        'incursion_count': incursion_count,
        'war_count': war_count,
        'campaign_count': campaign_count,
        'fw_system_count': fw_system_count,
    })


def live_lp_stores(request):
    """
    Browse loyalty point stores by faction.

    Shows all corporations with LP stores, grouped by their faction.
    """
    from core.eve.models import CorporationLPStoreInfo
    from core.sde.models import CrpNPCCorporations, ChrFactions

    # Get corps with stores
    corps = CorporationLPStoreInfo.objects.filter(
        has_loyalty_store=True
    ).order_by('corporation_id')

    # Enrich with SDE data
    corps_with_factions = []
    for lp_info in corps:
        try:
            corp = CrpNPCCorporations.objects.get(corporation_id=lp_info.corporation_id)
            faction = None
            if corp.faction:
                faction = corp.faction  # FK from CrpNPCCorporations to ChrFactions

            corps_with_factions.append({
                'lp_info': lp_info,
                'corporation': corp,
                'faction': faction,
            })
        except CrpNPCCorporations.DoesNotExist:
            pass

    # Group by faction
    from collections import defaultdict
    factions_dict = defaultdict(list)
    for item in corps_with_factions:
        faction_key = item['faction'] if item['faction'] else None
        factions_dict[faction_key].append(item)

    # Sort factions
    sorted_factions = sorted(
        factions_dict.items(),
        key=lambda x: x[0].faction_name if x[0] else ''
    )

    # Debug: check total_offers values
    non_zero_count = sum(1 for item in corps_with_factions if item['lp_info'].total_offers > 0)
    print(f"DEBUG VIEW: corps_with_factions={len(corps_with_factions)}, non_zero_count={non_zero_count}")

    return render(request, 'core/live/lp_stores.html', {
        'factions': sorted_factions,
        'total_corps': len(corps),
        'total_factions': len(sorted_factions),
    })


def live_lp_store_detail(request, corporation_id):
    """
    Show loyalty store offers for a corporation.

    Args:
        corporation_id: The corporation ID to show offers for
    """
    from core.eve.models import CorporationLPStoreInfo, LoyaltyStoreOffer
    from core.sde.models import CrpNPCCorporations, InvTypes

    lp_info = get_object_or_404(CorporationLPStoreInfo, corporation_id=corporation_id)
    corporation = get_object_or_404(CrpNPCCorporations, corporation_id=corporation_id)

    # Get offers with type names from SDE
    offers = LoyaltyStoreOffer.objects.filter(
        corporation=lp_info
    ).order_by('loyalty_points', 'isk_cost')

    # Enrich with SDE type data
    type_ids = [o.type_id for o in offers]
    types_map = {
        t.type_id: t
        for t in InvTypes.objects.filter(type_id__in=type_ids).select_related('group')
    }

    # Also fetch required item types
    required_type_ids = set()
    for offer in offers:
        for item in offer.required_items or []:
            required_type_ids.add(item['type_id'])

    required_types_map = {
        t.type_id: t
        for t in InvTypes.objects.filter(type_id__in=required_type_ids)
    }

    offers_with_types = []
    for offer in offers:
        offer.item_type = types_map.get(offer.type_id)
        # Enrich required items with type names
        offer.required_items_enriched = []
        for item in offer.required_items or []:
            item_type = required_types_map.get(item['type_id'])
            offer.required_items_enriched.append({
                'type_id': item['type_id'],
                'quantity': item['quantity'],
                'name': item_type.name if item_type else f"Type {item['type_id']}",
            })

        if offer.item_type:
            offers_with_types.append(offer)

    return render(request, 'core/live/lp_store_detail.html', {
        'corporation': corporation,
        'lp_info': lp_info,
        'offers': offers_with_types,
    })


def live_markets(request):
    """
    Browse market activity by region.

    Shows regions with market data and order counts.
    """
    from core.eve.models import RegionMarketSummary
    from core.sde.models import MapRegions

    # Get regions with market data
    summaries = RegionMarketSummary.objects.filter(
        last_sync_status='ok'
    ).order_by('-total_orders')

    regions_with_data = []
    for summary in summaries:
        try:
            region = MapRegions.objects.get(region_id=summary.region_id)
            regions_with_data.append({
                'region': region,
                'summary': summary,
            })
        except MapRegions.DoesNotExist:
            pass

    return render(request, 'core/live/markets.html', {
        'regions': regions_with_data,
    })


def live_incursions(request):
    """
    Show active incursions.

    Displays all active incursions with their state, faction, and location.
    """
    from core.eve.models import ActiveIncursion
    from core.sde.models import MapConstellations, ChrFactions

    incursions = ActiveIncursion.objects.filter(
        last_sync_status='ok'
    ).order_by('-last_updated')

    # Enrich with SDE data
    constellation_ids = [i.constellation_id for i in incursions]
    constellations_map = {
        c.constellation_id: c
        for c in MapConstellations.objects.filter(
            constellation_id__in=constellation_ids
        ).select_related('region')
    }

    faction_ids = [i.faction_id for i in incursions]
    factions_map = {
        f.faction_id: f
        for f in ChrFactions.objects.filter(faction_id__in=faction_ids)
    }

    enriched_incursions = []
    for inc in incursions:
        inc.constellation = constellations_map.get(inc.constellation_id)
        inc.faction = factions_map.get(inc.faction_id)
        if inc.constellation:
            enriched_incursions.append(inc)

    # Group by state
    from collections import defaultdict
    incursions_by_state = defaultdict(list)
    for inc in enriched_incursions:
        incursions_by_state[inc.state].append(inc)

    return render(request, 'core/live/incursions.html', {
        'incursions': enriched_incursions,
        'incursions_by_state': dict(incursions_by_state),
        'total': len(enriched_incursions),
    })


def live_wars(request):
    """
    Show active wars.

    Displays all active wars with aggressor/defender info.
    """
    from core.eve.models import ActiveWar

    wars = ActiveWar.objects.filter(
        is_active=True
    ).order_by('-declared')[:100]  # Limit to 100 most recent

    return render(request, 'core/live/wars.html', {
        'wars': wars,
        'total_wars': wars.count(),
    })


def live_war_detail(request, war_id):
    """
    Show details for a specific war.

    Args:
        war_id: The war ID to show details for
    """
    from core.eve.models import ActiveWar
    from core.eve.models import Corporation, Alliance

    war = get_object_or_404(ActiveWar, war_id=war_id)

    # Enrich with corp/alliance info
    aggressor_corp = None
    aggressor_ally = None
    defender_corp = None
    defender_ally = None

    if war.aggressor_id:
        try:
            aggressor_corp = Corporation.objects.get(id=war.aggressor_id)
        except Corporation.DoesNotExist:
            pass

    if war.ally_id:
        try:
            aggressor_ally = Alliance.objects.get(id=war.ally_id)
        except Alliance.DoesNotExist:
            pass

    if war.defender_id:
        try:
            defender_corp = Corporation.objects.get(id=war.defender_id)
        except Corporation.DoesNotExist:
            pass

    if war.defender_ally_id:
        try:
            defender_ally = Alliance.objects.get(id=war.defender_ally_id)
        except Alliance.DoesNotExist:
            pass

    return render(request, 'core/live/war_detail.html', {
        'war': war,
        'aggressor_corp': aggressor_corp,
        'aggressor_ally': aggressor_ally,
        'defender_corp': defender_corp,
        'defender_ally': defender_ally,
    })


def live_sovereignty(request):
    """
    Show sovereignty map and campaigns.

    Displays nullsec sovereignty by alliance and active campaigns.
    """
    from core.eve.models import SovMapSystem, SovCampaign

    # Get recent campaigns
    campaigns = SovCampaign.objects.filter(
        last_updated__gte=timezone.now() - timedelta(hours=24)
    ).select_related().order_by('-start_time')[:50]

    # Group campaigns by region
    from collections import defaultdict
    campaigns_by_region = defaultdict(list)
    for camp in campaigns:
        campaigns_by_region[camp.region_id].append(camp)

    return render(request, 'core/live/sovereignty.html', {
        'campaigns': campaigns,
        'campaigns_by_region': dict(campaigns_by_region),
        'total_campaigns': len(campaigns),
    })


def live_faction_warfare(request):
    """
    Show faction warfare overview.

    Displays FW stats and system ownership.
    """
    from core.eve.models import FactionWarfareStats, FactionWarfareSystem
    from core.sde.models import ChrFactions

    # Get FW stats
    stats = FactionWarfareStats.objects.all().order_by('-victory_points_last_week')

    # Enrich with faction names
    faction_ids = [s.faction_id for s in stats]
    factions_map = {
        f.faction_id: f
        for f in ChrFactions.objects.filter(faction_id__in=faction_ids)
    }

    stats_with_factions = []
    for stat in stats:
        stat.faction = factions_map.get(stat.faction_id)
        if stat.faction:
            stats_with_factions.append(stat)

    # Get total FW systems count
    fw_system_count = FactionWarfareSystem.objects.count()

    return render(request, 'core/live/faction_warfare.html', {
        'stats': stats_with_factions,
        'fw_system_count': fw_system_count,
    })
