"""
URL configuration for core app.
"""

from django.urls import path
from core import views

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('oauth/callback/', views.oauth_callback, name='oauth_callback'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('theme/toggle/', views.toggle_theme, name='toggle_theme'),

    # Character Management
    path('characters/', views.characters_list, name='characters'),
    path('characters/add/', views.add_character, name='add_character'),
    path('characters/<int:character_id>/remove/', views.remove_character, name='remove_character'),
    path('characters/<int:character_id>/set-main/', views.set_main_character, name='set_main_character'),

    # Character Detail (legacy URL, kept for compatibility)
    path('character/<int:character_id>/', views.character_detail, name='character_detail'),
    path('character/<int:character_id>/sync/', views.sync_character, name='sync_character'),

    # Skill plans
    path('plans/', views.skill_plan_list, name='skill_plan_list'),
    path('plans/create/', views.skill_plan_create, name='skill_plan_create'),
    path('plans/import/', views.skill_plan_import, name='skill_plan_import'),
    path('plans/<int:plan_id>/', views.skill_plan_detail, name='skill_plan_detail'),
    path('plans/<int:plan_id>/edit/', views.skill_plan_edit, name='skill_plan_edit'),
    path('plans/<int:plan_id>/delete/', views.skill_plan_delete, name='skill_plan_delete'),
    path('plans/<int:plan_id>/add-skill/', views.skill_plan_add_skill, name='skill_plan_add_skill'),
    path('plans/<int:plan_id>/remove-skill/<int:entry_id>/', views.skill_plan_remove_skill, name='skill_plan_remove_skill'),
    path('plans/<int:plan_id>/export/', views.skill_plan_export, name='skill_plan_export'),

    # Skills
    path('skills/', views.skills_list, name='skills_list'),
    path('skills/implants/', views.implants_view, name='implants_view'),
    path('skills/attributes/', views.attributes_view, name='attributes_view'),

    # Wallet
    path('wallet/journal/', views.wallet_journal, name='wallet_journal'),
    path('wallet/transactions/', views.wallet_transactions, name='wallet_transactions'),
    path('wallet/balance/', views.wallet_balance, name='wallet_balance'),
    path('wallet/summary/', views.wallet_summary, name='wallet_summary'),
    path('character/<int:character_id>/wallet/journal/', views.wallet_journal, name='character_wallet_journal'),
    path('character/<int:character_id>/wallet/transactions/', views.wallet_transactions, name='character_wallet_transactions'),
    path('character/<int:character_id>/wallet/balance/', views.wallet_balance, name='character_wallet_balance'),
    path('character/<int:character_id>/wallet/summary/', views.wallet_summary, name='character_wallet_summary'),

    # Market Orders
    path('market/orders/', views.market_orders, name='market_orders'),
    path('character/<int:character_id>/market/orders/', views.market_orders, name='character_market_orders'),
    path('market/orders/history/', views.market_orders_history, name='market_orders_history'),
    path('character/<int:character_id>/market/orders/history/', views.market_orders_history, name='character_market_orders_history'),

    # Trade Analysis
    path('trade/', views.trade_overview, name='trade_overview'),
    path('character/<int:character_id>/trade/', views.trade_overview, name='character_trade_overview'),
    path('trade/item/<int:type_id>/', views.trade_item_detail, name='trade_item_detail'),
    path('character/<int:character_id>/trade/item/<int:type_id>/', views.trade_item_detail, name='character_trade_item_detail'),

    # Trade Campaigns
    path('trade/campaigns/', views.campaign_list, name='campaign_list'),
    path('trade/campaigns/create/', views.campaign_create, name='campaign_create'),
    path('trade/campaigns/<int:campaign_id>/', views.campaign_detail, name='campaign_detail'),
    path('trade/campaigns/<int:campaign_id>/edit/', views.campaign_edit, name='campaign_edit'),
    path('trade/campaigns/<int:campaign_id>/delete/', views.campaign_delete, name='campaign_delete'),

    # Contracts
    path('contracts/', views.contracts_list, name='contracts'),
    path('character/<int:character_id>/contracts/', views.contracts_list, name='character_contracts'),
    path('contracts/<int:contract_id>/', views.contract_detail, name='contract_detail'),

    # Assets
    path('assets/', views.assets_list, name='assets_list'),
    path('character/<int:character_id>/assets/', views.assets_list, name='character_assets_list'),
    path('assets/summary/', views.assets_summary, name='assets_summary'),
    path('character/<int:character_id>/assets/summary/', views.assets_summary, name='character_assets_summary'),
    path('assets/ships/', views.fitted_ships, name='fitted_ships'),
    path('character/<int:character_id>/assets/ships/', views.fitted_ships, name='character_fitted_ships'),

    # Industry
    path('industry/', views.industry_summary, name='industry_summary'),
    path('industry/jobs/', views.industry_jobs_list, name='industry_jobs_list'),
    path('industry/jobs/<int:job_id>/', views.industry_job_detail, name='industry_job_detail'),
    path('character/<int:character_id>/industry/', views.industry_summary, name='character_industry_summary'),
    path('character/<int:character_id>/industry/jobs/', views.industry_jobs, name='character_industry_jobs'),
]
