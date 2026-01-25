"""
Core views for evewire.
"""

import logging
from datetime import timedelta
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import reverse
from django.db import models
from django.utils import timezone

logger = logging.getLogger('evewire')
# CSV Export Views

@login_required
def assets_export(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """Export character assets to CSV."""
    from core.models import Character
    from core.character.models import CharacterAsset
    from core.eve.models import ItemType
    import csv

    # Get character
    if character_id:
        try:
            character = Character.objects.get(id=character_id, user=request.user)
        except Character.DoesNotExist:
            return render(request, 'core/error.html', {
                'message': 'Character not found',
            }, status=404)
    else:
        character = get_users_character(request.user)
        if not character:
            return render(request, 'core/error.html', {
                'message': 'Character not found',
            }, status=404)

    # Get all assets for this character
    assets_qs = CharacterAsset.objects.filter(character=character).select_related('type')

    # Apply filters from query string
    location_type = request.GET.get('location_type', '')
    if location_type:
        assets_qs = assets_qs.filter(location_type=location_type)

    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    filename = f"{character.character_name}_assets.csv"
    filename = filename.replace(' ', '_').replace('/', '_')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    # Write header
    writer.writerow([
        'Item ID',
        'Item Name',
        'Type ID',
        'Quantity',
        'Location ID',
        'Location Type',
        'Location Flag',
        'Is Singleton',
        'Is Blueprint Copy',
        'Estimated Value (ISK)',
    ])

    # Write data rows
    for asset in assets_qs:
        item_type = asset.type
        item_name = item_type.name if item_type else f"Type {asset.type_id}"

        # Calculate estimated value
        if item_type and item_type.sell_price:
            value = float(item_type.sell_price) * asset.quantity
        elif item_type and item_type.base_price:
            value = float(item_type.base_price) * asset.quantity
        else:
            value = 0.0

        writer.writerow([
            asset.item_id,
            item_name,
            asset.type_id,
            asset.quantity,
            asset.location_id or '',
            asset.location_type,
            asset.location_flag,
            'Yes' if asset.is_singleton else 'No',
            'Yes' if asset.is_blueprint_copy else 'No',
            f'{value:.2f}',
        ])

    return response


@login_required
def contracts_export(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """Export character contracts to CSV."""
    from core.models import Character
    from core.character.models import Contract
    import csv

    # Get character
    if character_id:
        try:
            character = Character.objects.get(id=character_id, user=request.user)
        except Character.DoesNotExist:
            return render(request, 'core/error.html', {
                'message': 'Character not found',
            }, status=404)
    else:
        character = get_users_character(request.user)
        if not character:
            return render(request, 'core/error.html', {
                'message': 'Character not found',
            }, status=404)

    # Get all contracts for this character
    contracts_qs = Contract.objects.filter(character=character)

    # Apply filters from query string
    contract_type = request.GET.get('type', '')
    status_filter = request.GET.get('status', '')
    availability_filter = request.GET.get('availability', '')

    if contract_type:
        contracts_qs = contracts_qs.filter(type=contract_type)
    if status_filter:
        contracts_qs = contracts_qs.filter(status=status_filter)
    if availability_filter:
        contracts_qs = contracts_qs.filter(availability=availability_filter)

    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    filename = f"{character.character_name}_contracts.csv"
    filename = filename.replace(' ', '_').replace('/', '_')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    # Write header
    writer.writerow([
        'Contract ID',
        'Type',
        'Status',
        'Title',
        'Availability',
        'Date Issued',
        'Date Expires',
        'Date Completed',
        'Issuer ID',
        'Assignee ID',
        'Acceptor ID',
        'Price (ISK)',
        'Reward (ISK)',
        'Collateral (ISK)',
        'Buyout (ISK)',
        'Volume (m3)',
        'Items Count',
        'Total Value (ISK)',
    ])

    # Write data rows
    for contract in contracts_qs:
        writer.writerow([
            contract.contract_id,
            contract.type_name,
            contract.status_name,
            contract.title,
            contract.availability_name,
            contract.date_issued.strftime('%Y-%m-%d %H:%M:%S') if contract.date_issued else '',
            contract.date_expired.strftime('%Y-%m-%d %H:%M:%S') if contract.date_expired else '',
            contract.date_completed.strftime('%Y-%m-%d %H:%M:%S') if contract.date_completed else '',
            contract.issuer_id,
            contract.assignee_id or '',
            contract.acceptor_id or '',
            f'{float(contract.price):.2f}' if contract.price else '0.00',
            f'{float(contract.reward):.2f}' if contract.reward else '0.00',
            f'{float(contract.collateral):.2f}' if contract.collateral else '0.00',
            f'{float(contract.buyout):.2f}' if contract.buyout else '0.00',
            f'{contract.volume:.2f}' if contract.volume else '0.00',
            contract.items_count,
            f'{contract.total_value:.2f}',
        ])

    return response


@login_required
def industry_jobs_export(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """Export character industry jobs to CSV."""
    from core.models import Character
    from core.character.models import IndustryJob
    import csv

    # Get character
    if character_id:
        try:
            character = Character.objects.get(id=character_id, user=request.user)
        except Character.DoesNotExist:
            return render(request, 'core/error.html', {
                'message': 'Character not found',
            }, status=404)
    else:
        character = get_users_character(request.user)
        if not character:
            return render(request, 'core/error.html', {
                'message': 'Character not found',
            }, status=404)

    # Get all industry jobs for this character
    jobs_qs = IndustryJob.objects.filter(character=character)

    # Apply filters from query string
    activity_id = request.GET.get('activity', '')
    status_filter = request.GET.get('status', '')

    if activity_id:
        jobs_qs = jobs_qs.filter(activity_id=activity_id)
    if status_filter:
        jobs_qs = jobs_qs.filter(status=status_filter)

    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    filename = f"{character.character_name}_industry_jobs.csv"
    filename = filename.replace(' ', '_').replace('/', '_')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    # Write header
    writer.writerow([
        'Job ID',
        'Activity',
        'Status',
        'Blueprint Type ID',
        'Blueprint Name',
        'Product Type ID',
        'Product Name',
        'Station ID',
        'Solar System ID',
        'Start Date',
        'End Date',
        'Completed Date',
        'Runs',
        'Cost (ISK)',
        'Probability (%)',
        'Attempts',
        'Success',
        'Progress (%)',
    ])

    # Write data rows
    for job in jobs_qs:
        writer.writerow([
            job.job_id,
            job.activity_name,
            job.status_name,
            job.blueprint_type_id,
            job.blueprint_type_name,
            job.product_type_id or '',
            job.product_name,
            job.station_id,
            job.solar_system_id,
            job.start_date.strftime('%Y-%m-%d %H:%M:%S') if job.start_date else '',
            job.end_date.strftime('%Y-%m-%d %H:%M:%S') if job.end_date else '',
            job.completed_date.strftime('%Y-%m-%d %H:%M:%S') if job.completed_date else '',
            job.runs,
            f'{float(job.cost):.2f}' if job.cost else '0.00',
            f'{job.probability:.1f}' if job.probability is not None else '',
            job.attempts or '',
            'Yes' if job.success else ('No' if job.success is not None else ''),
            f'{job.progress_percent:.1f}' if job.progress_percent else '0.0',
        ])

    return response


@login_required
def blueprints_list(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """View blueprint library with BPO/BPC distinction and filtering."""
    from core.models import Character
    from core.character.models import CharacterAsset
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from collections import defaultdict

    # Get character
    if character_id:
        try:
            character = Character.objects.get(id=character_id, user=request.user)
        except Character.DoesNotExist:
            return render(request, 'core/error.html', {
                'message': 'Character not found',
            }, status=404)
    else:
        character = get_users_character(request.user)
        if not character:
            return render(request, 'core/error.html', {
                'message': 'Character not found',
            }, status=404)

    # Get filter parameters
    bp_type_filter = request.GET.get('type', '')  # 'BPO', 'BPC', or ''
    search_query = request.GET.get('search', '')
    location_filter = request.GET.get('location', '')

    # Get all blueprint assets for this character
    # Note: filter by checking type_id against blueprints in the SDE
    from core.eve.models import ItemType
    blueprint_type_ids = ItemType.objects.filter(category_id=9).values_list('id', flat=True)

    # Build base queryset
    blueprints_qs = CharacterAsset.objects.filter(
        character=character,
        type_id__in=blueprint_type_ids
    )

    # Apply type filter
    if bp_type_filter == 'BPO':
        # BPO: is_blueprint_copy = False
        blueprints_qs = blueprints_qs.filter(is_blueprint_copy=False)
    elif bp_type_filter == 'BPC':
        # BPC: is_blueprint_copy = True
        blueprints_qs = blueprints_qs.filter(is_blueprint_copy=True)

    # Apply location filter
    if location_filter:
        if location_filter == 'station':
            blueprints_qs = blueprints_qs.filter(location_type='station')
        elif location_filter == 'structure':
            blueprints_qs = blueprints_qs.filter(location_type='structure')
        elif location_filter == 'solar_system':
            blueprints_qs = blueprints_qs.filter(location_type='solar_system')

    # Apply search filter (need to filter by type_id from matching ItemType names)
    if search_query:
        matching_type_ids = ItemType.objects.filter(
            id__in=blueprint_type_ids,
            name__icontains=search_query
        ).values_list('id', flat=True)
        blueprints_qs = blueprints_qs.filter(type_id__in=matching_type_ids)

    # Get all matching blueprints and sort in Python (since we can't order by type__name without FK)
    all_blueprints = list(blueprints_qs)

    # Sort by type name (fetch names for sorting)
    if all_blueprints:
        type_ids = [bp.type_id for bp in all_blueprints]
        type_names = dict(ItemType.objects.filter(
            id__in=type_ids
        ).values_list('id', 'name'))
        for bp in all_blueprints:
            bp._cached_type_name = type_names.get(bp.type_id, f"Type {bp.type_id}")
        all_blueprints.sort(key=lambda x: x._cached_type_name)

    # Pagination
    page = request.GET.get('page', 1)
    per_page = 50
    paginator = Paginator(all_blueprints, per_page)

    try:
        blueprints = paginator.page(page)
    except PageNotAnInteger:
        blueprints = paginator.page(1)
    except EmptyPage:
        blueprints = paginator.page(paginator.num_pages)

    # Calculate blueprint counts
    base_qs = CharacterAsset.objects.filter(
        character=character,
        type_id__in=blueprint_type_ids
    )
    bpo_count = base_qs.filter(is_blueprint_copy=False).count()
    bpc_count = base_qs.filter(is_blueprint_copy=True).count()

    return render(request, 'core/blueprints_list.html', {
        'character': character,
        'blueprints': blueprints,
        'bp_type_filter': bp_type_filter,
        'search_query': search_query,
        'location_filter': location_filter,
        'bpo_count': bpo_count,
        'bpc_count': bpc_count,
        'total_blueprints': bpo_count + bpc_count,
    })

