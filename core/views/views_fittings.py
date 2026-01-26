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
# ============================================================================
# FITTINGS VIEWS
# ============================================================================

@login_required
def fittings_list(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """View all fittings with filtering."""
    from core.models import Character
    from core.doctrines.models import Fitting
    from core.eve.models import ItemType

    # Get character
    if character_id:
        try:
            character = Character.objects.get(id=character_id, user=request.user)
        except Character.DoesNotExist:
            return render(request, 'core/error.html', {
                'message': 'Character not found',
            }, status=404)
    else:
        character = None

    # Get filter parameters
    ship_type_filter = request.GET.get('ship_type', '')
    search_query = request.GET.get('search', '')
    tag_filter = request.GET.get('tag', '')

    # Build base queryset
    fittings_qs = Fitting.objects.active()

    # Apply ship type filter
    if ship_type_filter:
        fittings_qs = fittings_qs.filter(ship_type_id=ship_type_filter)

    # Apply tag filter (JSON field query)
    if tag_filter:
        # Filter by JSON tags field - check if tag exists in the tags dict
        fittings_qs = [f for f in fittings_qs if tag_filter in f.tags]

    # Apply search filter
    if search_query:
        fittings_qs = fittings_qs.filter(name__icontains=search_query)

    # Prefetch related data
    fittings_qs = fittings_qs.select_related()

    # Get all ship types for filter dropdown (category 6 = Ships in EVE SDE)
    from core.eve.models import ItemGroup
    ship_group_ids = ItemGroup.objects.filter(category_id=6, published=True).values_list('id', flat=True)
    ship_types = ItemType.objects.filter(group_id__in=ship_group_ids, published=True).order_by('name')

    # Get all unique tags from active fittings
    all_tags = set()
    for fitting in Fitting.objects.active():
        all_tags.update(fitting.tags.keys())

    return render(request, 'core/fittings_list.html', {
        'character': character,
        'fittings': fittings_qs,
        'ship_types': ship_types,
        'ship_type_filter': ship_type_filter,
        'search_query': search_query,
        'tag_filter': tag_filter,
        'all_tags': sorted(all_tags),
    })


@login_required
def fitting_detail(request: HttpRequest, fitting_id: int) -> HttpResponse:
    """View fitting details with module layout."""
    from core.doctrines.models import Fitting, FittingMatch
    from core.models import Character

    try:
        fitting = Fitting.objects.get(id=fitting_id)
    except Fitting.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Fitting not found',
        }, status=404)

    # Get slots
    slots = fitting.get_slots()

    # Get matching assets for current user's characters
    matching_assets = []
    if request.user.is_authenticated:
        for character in request.user.characters.all():
            matches = FittingMatch.objects.filter(
                character=character,
                fitting=fitting,
                is_match=True
            ).select_related('character')
            matching_assets.extend(matches)

    return render(request, 'core/fitting_detail.html', {
        'fitting': fitting,
        'slots': slots,
        'matching_assets': matching_assets,
    })


@login_required
def fitting_matches(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """View asset matching results - show which ships match which fittings."""
    from core.models import Character
    from core.doctrines.services import AssetFitExtractor, FittingMatcher
    from core.doctrines.models import Fitting

    # Get character
    if character_id:
        try:
            character = Character.objects.get(id=character_id, user=request.user)
        except Character.DoesNotExist:
            return render(request, 'core/error.html', {
                'message': 'Character not found',
            }, status=404)
    else:
        # Use first character if none specified
        try:
            character = request.user.characters.first()
            if not character:
                return render(request, 'core/error.html', {
                    'message': 'No characters found. Please add a character first.',
                }, status=404)
        except Character.DoesNotExist:
            return render(request, 'core/error.html', {
                'message': 'No characters found. Please add a character first.',
            }, status=404)

    # Extract fitted ships and match against fittings
    extractor = AssetFitExtractor()
    matcher = FittingMatcher(extractor)
    
    fitted_ships = extractor.extract_ships(character)
    matches = []
    
    for ship in fitted_ships:
        # Find matching fittings for this ship type
        ship_fittings = Fitting.objects.active().filter(ship_type_id=ship.ship_type_id)
        
        for fitting in ship_fittings:
            match_result = matcher._match_ship_to_fitting(ship, fitting)
            if match_result:
                matches.append(match_result)
    
    # Sort by match score descending
    matches.sort(key=lambda m: m['score'], reverse=True)

    # Get all characters for filter dropdown
    characters = request.user.characters.all() if request.user.is_authenticated else []

    return render(request, 'core/fitting_matches.html', {
        'character': character,
        'characters': characters,
        'matches': matches,
        'fitted_ships_count': len(fitted_ships),
    })


@login_required
def shopping_lists_list(request: HttpRequest, character_id: int = None) -> HttpResponse:
    """View shopping lists for fitting fulfillment."""
    from core.models import Character
    from core.doctrines.models import ShoppingList

    # Get character
    if character_id:
        try:
            character = Character.objects.get(id=character_id, user=request.user)
        except Character.DoesNotExist:
            return render(request, 'core/error.html', {
                'message': 'Character not found',
            }, status=404)
    else:
        # Use first character if none specified
        try:
            character = request.user.characters.first()
            if not character:
                return render(request, 'core/error.html', {
                    'message': 'No characters found. Please add a character first.',
                }, status=404)
        except Character.DoesNotExist:
            return render(request, 'core/error.html', {
                'message': 'No characters found. Please add a character first.',
            }, status=404)

    # Get filter parameters
    status_filter = request.GET.get('status', '')

    # Build base queryset
    lists_qs = ShoppingList.objects.filter(character=character)

    # Apply status filter
    if status_filter:
        lists_qs = lists_qs.filter(status=status_filter)

    # Order by created date (newest first)
    lists_qs = lists_qs.order_by('-created_at')

    # Get all characters for filter dropdown
    characters = request.user.characters.all() if request.user.is_authenticated else []

    # Calculate counts by status
    all_lists = ShoppingList.objects.filter(character=character)
    pending_count = all_lists.filter(status='pending').count()
    partial_count = all_lists.filter(status='partial').count()
    complete_count = all_lists.filter(status='complete').count()

    return render(request, 'core/shopping_lists_list.html', {
        'character': character,
        'characters': characters,
        'shopping_lists': lists_qs,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'partial_count': partial_count,
        'complete_count': complete_count,
    })


@login_required
def shopping_list_detail(request: HttpRequest, list_id: int) -> HttpResponse:
    """View shopping list details."""
    from core.models import Character
    from core.doctrines.models import ShoppingList
    from core.eve.models import ItemType

    try:
        shopping_list = ShoppingList.objects.get(id=list_id)
    except ShoppingList.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Shopping list not found',
        }, status=404)

    # Check ownership
    if shopping_list.character.user != request.user:
        return render(request, 'core/error.html', {
            'message': 'Access denied',
        }, status=403)

    # Get item details for items_to_buy
    items_to_buy = []
    if shopping_list.items_to_buy:
        for type_id, quantity in shopping_list.items_to_buy.items():
            try:
                item_type = ItemType.objects.get(id=type_id)
                items_to_buy.append({
                    'type_id': type_id,
                    'name': item_type.name,
                    'quantity': quantity,
                    'base_price': float(item_type.base_price or 0),
                    'total_value': float(item_type.base_price or 0) * quantity,
                })
            except ItemType.DoesNotExist:
                items_to_buy.append({
                    'type_id': type_id,
                    'name': f'Unknown Type {type_id}',
                    'quantity': quantity,
                    'base_price': 0,
                    'total_value': 0,
                })

    # Sort by total value descending
    items_to_buy.sort(key=lambda x: x['total_value'], reverse=True)

    return render(request, 'core/shopping_list_detail.html', {
        'shopping_list': shopping_list,
        'items_to_buy': items_to_buy,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def fitting_import(request: HttpRequest) -> HttpResponse:
    """Import a fitting from EFT/DNA/XML/Markdown format."""
    from core.fitting_formats import FittingImporter, detect_format, FormatDetectionError
    from core.fitting_formats.exceptions import FittingFormatError

    if request.method == 'GET':
        return render(request, 'core/fitting_import.html', {
            'formats': [
                {'name': 'EFT', 'description': 'EVE Fitting Tool - Human-readable text format'},
                {'name': 'DNA', 'description': 'Compact type_id format for chat links'},
                {'name': 'XML', 'description': 'CCP official XML format'},
                {'name': 'MD', 'description': 'Markdown format with embedded EFT fit and metadata'},
            ],
        })

    # Handle POST import
    content = request.POST.get('content', '')
    format_name = request.POST.get('format', '')
    auto_detect = request.POST.get('auto_detect') == 'on'

    if not content:
        return render(request, 'core/fitting_import.html', {
            'error': 'Please paste fitting content',
            'formats': [
                {'name': 'EFT', 'description': 'EVE Fitting Tool - Human-readable text format'},
                {'name': 'DNA', 'description': 'Compact type_id format for chat links'},
                {'name': 'XML', 'description': 'CCP official XML format'},
                {'name': 'MD', 'description': 'Markdown format with embedded EFT fit and metadata'},
            ],
        })

    try:
        # Import fitting
        fitting = FittingImporter.import_from_string(
            content,
            format_name=format_name if not auto_detect else None,
            auto_detect=auto_detect,
        )

        return render(request, 'core/fitting_import.html', {
            'success': True,
            'fitting': fitting,
            'formats': [
                {'name': 'EFT', 'description': 'EVE Fitting Tool - Human-readable text format'},
                {'name': 'DNA', 'description': 'Compact type_id format for chat links'},
                {'name': 'XML', 'description': 'CCP official XML format'},
                {'name': 'MD', 'description': 'Markdown format with embedded EFT fit and metadata'},
            ],
        })

    except FormatDetectionError as e:
        return render(request, 'core/fitting_import.html', {
            'error': f'Could not detect format: {e}',
            'content': content,
            'formats': [
                {'name': 'EFT', 'description': 'EVE Fitting Tool - Human-readable text format'},
                {'name': 'DNA', 'description': 'Compact type_id format for chat links'},
                {'name': 'XML', 'description': 'CCP official XML format'},
                {'name': 'MD', 'description': 'Markdown format with embedded EFT fit and metadata'},
            ],
        })
    except FittingFormatError as e:
        return render(request, 'core/fitting_import.html', {
            'error': f'Import failed: {e}',
            'content': content,
            'formats': [
                {'name': 'EFT', 'description': 'EVE Fitting Tool - Human-readable text format'},
                {'name': 'DNA', 'description': 'Compact type_id format for chat links'},
                {'name': 'XML', 'description': 'CCP official XML format'},
                {'name': 'MD', 'description': 'Markdown format with embedded EFT fit and metadata'},
            ],
        })


@login_required
def fitting_export(request: HttpRequest, fitting_id: int, format: str) -> HttpResponse:
    """Export a fitting to EFT/DNA/XML format."""
    from django.http import FileResponse
    from core.doctrines.models import Fitting
    from core.fitting_formats import FittingExporter, FittingFormatError
    import io

    # Validate format
    if format not in ('eft', 'dna', 'xml'):
        return render(request, 'core/error.html', {
            'message': f'Invalid format: {format}',
        }, status=400)

    try:
        fitting = Fitting.objects.get(id=fitting_id)
    except Fitting.DoesNotExist:
        return render(request, 'core/error.html', {
            'message': 'Fitting not found',
        }, status=404)

    try:
        # Export fitting
        content = FittingExporter.export_to_string(fitting, format)

        # Create response with appropriate content type and filename
        filename = f"{fitting.name.replace('/', '-')}.{format}"
        if format == 'eft':
            content_type = 'text/plain'
        elif format == 'dna':
            content_type = 'text/plain'
        elif format == 'xml':
            content_type = 'application/xml'
        else:
            content_type = 'text/plain'

        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except FittingFormatError as e:
        return render(request, 'core/error.html', {
            'message': f'Export failed: {e}',
        }, status=500)


@login_required
@require_http_methods(['GET', 'POST'])
def fitting_bulk_import(request: HttpRequest) -> HttpResponse:
    """Bulk import fittings from a file."""
    from core.fitting_formats import FittingImporter, detect_format, FormatDetectionError
    from core.fitting_formats.exceptions import FittingFormatError
    import re

    if request.method == 'GET':
        return render(request, 'core/fitting_bulk_import.html', {
            'formats': [
                {'name': 'EFT', 'description': 'EVE Fitting Tool - Human-readable text format'},
                {'name': 'DNA', 'description': 'Compact type_id format for chat links'},
                {'name': 'XML', 'description': 'CCP official XML format'},
                {'name': 'MD', 'description': 'Markdown format with embedded EFT fit and metadata'},
            ],
        })

    # Handle POST import
    uploaded_file = request.FILES.get('file')
    format_name = request.POST.get('format', '')
    auto_detect = request.POST.get('auto_detect') == 'on'

    if not uploaded_file:
        return render(request, 'core/fitting_bulk_import.html', {
            'error': 'Please upload a file',
            'formats': [
                {'name': 'EFT', 'description': 'EVE Fitting Tool - Human-readable text format'},
                {'name': 'DNA', 'description': 'Compact type_id format for chat links'},
                {'name': 'XML', 'description': 'CCP official XML format'},
                {'name': 'MD', 'description': 'Markdown format with embedded EFT fit and metadata'},
            ],
        })

    try:
        content = uploaded_file.read().decode('utf-8')
    except UnicodeDecodeError:
        return render(request, 'core/fitting_bulk_import.html', {
            'error': 'File encoding error. Please upload a UTF-8 text file.',
            'formats': [
                {'name': 'EFT', 'description': 'EVE Fitting Tool - Human-readable text format'},
                {'name': 'DNA', 'description': 'Compact type_id format for chat links'},
                {'name': 'XML', 'description': 'CCP official XML format'},
                {'name': 'MD', 'description': 'Markdown format with embedded EFT fit and metadata'},
            ],
        })

    # Import fittings
    imported = []
    errors = []

    # For EFT format, split by [Ship, Name] headers
    if format_name == 'eft' or (auto_detect and '[' in content and ']' in content and '#' not in content.split('\n')[0]):
        # Split by fitting headers
        pattern = r'\[([^,\]]+),\s*([^\]]+)\]'
        parts = re.split(pattern, content)

        for i in range(1, len(parts), 3):
            if i + 2 >= len(parts):
                break
            ship_name = parts[i].strip()
            fitting_name = parts[i + 1].strip()
            fitting_content = f'[{ship_name}, {fitting_name}]'

            # Add remaining content until next header or end
            j = i + 2
            while j < len(parts) and not parts[j].startswith('['):
                fitting_content += parts[j]
                j += 1

            try:
                fitting = FittingImporter.import_from_string(
                    fitting_content,
                    format_name='eft',
                    auto_detect=False,
                )
                imported.append(fitting)
            except FittingFormatError as e:
                errors.append(f'{fitting_name}: {e}')

    # For XML with multiple fittings
    elif format_name == 'xml' or (auto_detect and content.strip().startswith('<')):
        # XML can contain multiple fittings
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(content)

            fitting_elems = root.findall('.//fitting')
            if not fitting_elems:
                # Try direct parsing of single fitting
                fitting = FittingImporter.import_from_string(
                    content,
                    format_name='xml',
                    auto_detect=False,
                )
                imported.append(fitting)
            else:
                for fitting_elem in fitting_elems:
                    fitting_xml = ET.tostring(fitting_elem, encoding='unicode')
                    try:
                        fitting = FittingImporter.import_from_string(
                            f'<fittings>{fitting_xml}</fittings>',
                            format_name='xml',
                            auto_detect=False,
                        )
                        imported.append(fitting)
                    except FittingFormatError as e:
                        fitting_name = fitting_elem.get('name', 'Unknown')
                        errors.append(f'{fitting_name}: {e}')
        except Exception as e:
            errors.append(f'XML parsing error: {e}')

    else:
        # Single fitting (Markdown, DNA, or single EFT)
        try:
            fitting = FittingImporter.import_from_string(
                content,
                format_name=format_name if not auto_detect else None,
                auto_detect=auto_detect,
            )
            imported.append(fitting)
        except FittingFormatError as e:
            errors.append(str(e))

    return render(request, 'core/fitting_bulk_import.html', {
        'success': True if imported else False,
        'imported': imported,
        'errors': errors,
        'formats': [
            {'name': 'EFT', 'description': 'EVE Fitting Tool - Human-readable text format'},
            {'name': 'DNA', 'description': 'Compact type_id format for chat links'},
            {'name': 'XML', 'description': 'CCP official XML format'},
            {'name': 'MD', 'description': 'Markdown format with embedded EFT fit and metadata'},
        ],
    })
