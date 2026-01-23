"""
Core views for evewire.

Split into logical modules for better organization.
"""

import logging
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import reverse
from django.db import models

logger = logging.getLogger('evewire')


def get_users_character(user):
    """Get user's character (first character if multiple).
    Returns None if user has no characters.
    """
    from core.models import Character
    return Character.objects.filter(user=user).first()


def index(request: HttpRequest) -> HttpResponse:
    """Landing page - show login button or redirect to dashboard."""
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    return render(request, 'core/index.html')


@require_http_methods(['GET', 'POST'])
def login_view(request: HttpRequest) -> HttpResponse:
    """Initiate EVE SSO login flow."""
    from core.services import TokenManager

    if request.user.is_authenticated:
        return redirect('core:dashboard')

    sso_url = TokenManager.get_sso_login_url()
    return redirect(sso_url)


def oauth_callback(request: HttpRequest) -> HttpResponse:
    """Handle EVE SSO OAuth callback."""
    from core.services import AuthService

    code = request.GET.get('code')
    error = request.GET.get('error')
    error_description = request.GET.get('error_description')

    if error:
        logger.error(f'OAuth error: {error} - {error_description}')
        return render(request, 'core/auth_error.html', {
            'error': error,
            'error_description': error_description,
        })

    if not code:
        logger.error('OAuth callback missing code parameter')
        return render(request, 'core/auth_error.html', {
            'error': 'Missing authorization code',
        })

    try:
        # Check if this is a re-authentication flow
        reauth_char_id = request.session.pop('reauth_character_id', None)

        # Pass request.user if logged in (for adding character to existing account)
        request_user = request.user if request.user.is_authenticated else None
        user = AuthService.handle_callback(code, request_user=request_user, reauth_char_id=reauth_char_id)

        # If not already logged in, login the user
        if not request_user:
            login(request, user)

        logger.info(f'User {user.display_name} logged in via SSO')
        return redirect('core:characters')

    except Exception as e:
        logger.error(f'Failed to handle OAuth callback: {e}')
        return render(request, 'core/auth_error.html', {
            'error': 'Authentication failed',
            'error_description': str(e),
        })


@login_required
def logout_view(request: HttpRequest) -> HttpResponse:
    """Log out the current user."""
    logger.info(f'User {request.user.display_name} logged out')
    logout(request)
    return redirect('core:index')


@login_required
def toggle_theme(request: HttpRequest) -> HttpResponse:
    """Toggle between light and dark theme."""
    from django.http import HttpResponse

    if request.method == 'POST':
        new_theme = 'dark' if request.session.get('theme') == 'light' else 'light'
        request.session['theme'] = new_theme
        return HttpResponse(status=200)

    # Get current theme
    theme = request.session.get('theme', 'light')
    return HttpResponse(theme)


# Import views from submodules to expose them at package level
from .dashboard import dashboard, character_detail, sync_character, reauthenticate_character
from .character import characters_list, add_character, remove_character, set_main_character
from .plans import (
    skill_plan_list, skill_plan_detail, skill_plan_create, skill_plan_edit,
    skill_plan_delete, skill_plan_add_skill, skill_plan_remove_skill,
    skill_search, skill_plan_export, skill_plan_import
)
from .skills import skills_list, implants_view, attributes_view
from .wallet import wallet_journal, wallet_transactions, wallet_balance, wallet_summary
from .market import (
    market_orders, market_orders_history, trade_overview, trade_item_detail,
    campaign_list, campaign_create, campaign_detail, campaign_edit, campaign_delete
)
from .contract import contracts_list, contract_detail, contracts_export
from .asset import assets_list, assets_summary, fitted_ships, assets_export
from .industry import (
    industry_summary, industry_jobs_list, industry_job_detail, industry_jobs,
    blueprints_list, industry_jobs_export
)
from .fitting import (
    fittings_list, fitting_detail, fitting_matches, fitting_import,
    fitting_export, fitting_bulk_import, shopping_lists_list, shopping_list_detail
)

__all__ = [
    # Base
    'get_users_character', 'index', 'login_view', 'oauth_callback', 'logout_view', 'toggle_theme',
    # Dashboard
    'dashboard', 'character_detail', 'sync_character', 'reauthenticate_character',
    # Character management
    'characters_list', 'add_character', 'remove_character', 'set_main_character',
    # Skill plans
    'skill_plan_list', 'skill_plan_detail', 'skill_plan_create', 'skill_plan_edit',
    'skill_plan_delete', 'skill_plan_add_skill', 'skill_plan_remove_skill',
    'skill_search', 'skill_plan_export', 'skill_plan_import',
    # Skills
    'skills_list', 'implants_view', 'attributes_view',
    # Wallet
    'wallet_journal', 'wallet_transactions', 'wallet_balance', 'wallet_summary',
    # Market
    'market_orders', 'market_orders_history', 'trade_overview', 'trade_item_detail',
    # Campaigns
    'campaign_list', 'campaign_create', 'campaign_detail', 'campaign_edit', 'campaign_delete',
    # Contracts
    'contracts_list', 'contract_detail', 'contracts_export',
    # Assets
    'assets_list', 'assets_summary', 'fitted_ships', 'assets_export',
    # Industry
    'industry_summary', 'industry_jobs_list', 'industry_job_detail', 'industry_jobs',
    'blueprints_list', 'industry_jobs_export',
    # Fittings
    'fittings_list', 'fitting_detail', 'fitting_matches', 'fitting_import',
    'fitting_export', 'fitting_bulk_import', 'shopping_lists_list', 'shopping_list_detail',
]
