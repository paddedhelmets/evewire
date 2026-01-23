"""Contract views."""

import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpRequest, HttpResponse, JsonResponse

logger = logging.getLogger(__name__)


def get_users_character(user):
    """Get user's character (first character if multiple).
    Returns None if user has no characters.
    """
    from core.models import Character
    return Character.objects.filter(user=user).first()


# Contracts Views

@login_required
def contracts_list(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """View contracts with filtering and pagination."""
    from core.models import Character
    from core.character.models import Contract
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

    # Get all user's characters for pilot filter
    all_characters = list(Character.objects.filter(user=request.user).order_by('character_name'))

    if not all_characters:
        return render(request, 'core/error.html', {
            'message': 'No characters found',
        }, status=404)

    # Get character - either specified or user's first character
    if character_id:
        try:
            character = Character.objects.get(id=character_id, user=request.user)
        except Character.DoesNotExist:
            return render(request, 'core/error.html', {
                'message': 'Character not found',
            }, status=404)
        is_account_wide = False
    else:
        # Account-wide view - show all characters
        character = None
        is_account_wide = True

    # Get filter parameters
    pilot_filter = request.GET.getlist('pilots', [])  # Multi-select for account-wide
    contract_type = request.GET.get('type', '')  # 'item_exchange', 'auction', 'courier', 'loan', or ''
    status_filter = request.GET.get('status', '')  # 'outstanding', 'in_progress', etc.
    availability_filter = request.GET.get('availability', '')  # 'public', 'personal', 'corporation', 'alliance'

    # Build queryset
    if is_account_wide:
        # Filter by selected pilots, or show all if none selected
        if pilot_filter:
            pilot_ids = [int(pid) for pid in pilot_filter if pid.isdigit()]
            contracts_qs = Contract.objects.filter(character_id__in=pilot_ids)
        else:
            contracts_qs = Contract.objects.filter(character__user=request.user)
    else:
        contracts_qs = Contract.objects.filter(character=character)

    # Apply type filter
    if contract_type:
        contracts_qs = contracts_qs.filter(type=contract_type)

    # Apply status filter
    if status_filter:
        contracts_qs = contracts_qs.filter(status=status_filter)

    # Apply availability filter
    if availability_filter:
        contracts_qs = contracts_qs.filter(availability=availability_filter)

    # Order by issued date (newest first)
    contracts_qs = contracts_qs.order_by('-date_issued')

    # Pagination
    page = request.GET.get('page', 1)
    per_page = 50
    paginator = Paginator(contracts_qs, per_page)

    try:
        contracts = paginator.page(page)
    except PageNotAnInteger:
        contracts = paginator.page(1)
    except EmptyPage:
        contracts = paginator.page(paginator.num_pages)

    # Calculate summary stats for account-wide view
    summary = None
    if is_account_wide:
        outstanding_count = contracts_qs.filter(status='outstanding').count()
        in_progress_count = contracts_qs.filter(status='in_progress').count()
        completed_count = contracts_qs.filter(
            status__in=('finished_issuer', 'finished_contractor', 'finished')
        ).count()
        summary = {
            'outstanding_count': outstanding_count,
            'in_progress_count': in_progress_count,
            'completed_count': completed_count,
        }
    else:
        # Calculate contract counts by status for single character
        outstanding_count = Contract.objects.filter(
            character=character, status='outstanding'
        ).count()
        in_progress_count = Contract.objects.filter(
            character=character, status='in_progress'
        ).count()
        completed_count = Contract.objects.filter(
            character=character, status__in=('finished_issuer', 'finished_contractor', 'finished')
        ).count()

    return render(request, 'core/contracts.html', {
        'character': character,
        'all_characters': all_characters,
        'is_account_wide': is_account_wide,
        'contracts': contracts,
        'contract_type': contract_type,
        'status_filter': status_filter,
        'availability_filter': availability_filter,
        'pilot_filter': pilot_filter,
        'summary': summary,
        'outstanding_count': outstanding_count if not is_account_wide else None,
        'in_progress_count': in_progress_count if not is_account_wide else None,
        'completed_count': completed_count if not is_account_wide else None,
    })


@login_required
def contract_detail(request: HttpRequest, contract_id: int) -> HttpResponse:
    """View a single contract with its items."""
    from core.models import Character
    from core.character.models import Contract, ContractItem

    try:
        contract = Contract.objects.get(contract_id=contract_id)
    except Contract.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Contract not found',
        }, status=404)

    # Verify ownership
    if contract.character.user != request.user:
        return render(request, 'core/error.html', {
            'message': 'Access denied',
        }, status=403)

    # Get contract items
    items = contract.items.all()

    # Calculate item statistics
    included_items = [item for item in items if item.is_included]
    requested_items = [item for item in items if not item.is_included]

    return render(request, 'core/contract_detail.html', {
        'contract': contract,
        'items': items,
        'included_items': included_items,
        'requested_items': requested_items,
    })


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


