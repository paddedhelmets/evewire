"""
URL configuration for core app.
"""

from django.urls import path
from core import views
from core.views import api
from core.sde import views as sde_views

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('oauth/callback/', views.oauth_callback, name='oauth_callback'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('theme/toggle/', views.toggle_theme, name='toggle_theme'),

    # Email verification
    path('verify-email/<str:token>/', views.verify_email_login, name='verify_email_login'),
    path('email-prompt/', views.email_prompt_page, name='email_prompt'),
    path('account-claim/', views.account_claim_page, name='account_claim'),
    path('profile/', views.user_profile, name='user_profile'),

    # Character Management
    path('characters/', views.characters_list, name='characters'),
    path('characters/add/', views.add_character, name='add_character'),
    path('characters/<int:character_id>/remove/', views.remove_character, name='remove_character'),
    path('characters/<int:character_id>/set-main/', views.set_main_character, name='set_main_character'),

    # Character pages (new plural URLs)
    path('characters/<int:character_id>/', views.character_overview, name='character_overview'),
    path('characters/<int:character_id>/skills', views.character_skills_page, name='character_skills_page'),
    path('characters/<int:character_id>/queue', views.character_queue_page, name='character_queue_page'),
    path('characters/<int:character_id>/plans', views.character_plans_page, name='character_plans_page'),

    # Character Detail (legacy URL, kept for compatibility)
    path('character/<int:character_id>/', views.character_detail, name='character_detail'),
    path('character/<int:character_id>/sync/', views.sync_character, name='sync_character'),
    path('character/<int:character_id>/reauthenticate/', views.reauthenticate_character, name='reauthenticate_character'),

    # Skill plans
    path('plans/', views.skill_plan_list, name='skill_plan_list'),
    path('plans/create/', views.skill_plan_create, name='skill_plan_create'),
    path('plans/import/', views.skill_plan_import, name='skill_plan_import'),
    path('plans/<int:plan_id>/', views.skill_plan_detail, name='skill_plan_detail'),
    path('plans/<int:plan_id>/edit/', views.skill_plan_edit, name='skill_plan_edit'),
    path('plans/<int:plan_id>/delete/', views.skill_plan_delete, name='skill_plan_delete'),
    path('plans/<int:plan_id>/add-skill/', views.skill_plan_add_skill, name='skill_plan_add_skill'),
    path('plans/<int:plan_id>/remove-skill/<int:entry_id>/', views.skill_plan_remove_skill, name='skill_plan_remove_skill'),
    path('plans/<int:plan_id>/import-skills/', views.skill_plan_import_skills, name='skill_plan_import_skills'),
    path('plans/<int:plan_id>/export/', views.skill_plan_export, name='skill_plan_export'),
    path('skills/search/', views.skill_search, name='skill_search'),

    # Skills
    path('skills/', views.skills_list, name='skills_list'),
    path('character/<int:character_id>/skills/', views.skills_list, name='character_skills'),
    path('skills/implants/', views.implants_view, name='implants_view'),
    path('skills/attributes/', views.attributes_view, name='attributes_view'),

    # Wallet
    path('wallet/journal/', views.wallet_journal, name='wallet_journal'),
    path('wallet/balance/', views.wallet_balance, name='wallet_balance'),
    path('wallet/summary/', views.wallet_summary, name='wallet_summary'),
    path('character/<int:character_id>/wallet/journal/', views.wallet_journal, name='character_wallet_journal'),
    path('character/<int:character_id>/wallet/balance/', views.wallet_balance, name='character_wallet_balance'),
    path('character/<int:character_id>/wallet/summary/', views.wallet_summary, name='character_wallet_summary'),

    # Market Orders
    path('market/orders/', views.market_orders, name='market_orders'),
    path('character/<int:character_id>/market/orders/', views.market_orders, name='character_market_orders'),
    path('market/orders/history/', views.market_orders_history, name='market_orders_history'),
    path('character/<int:character_id>/market/orders/history/', views.market_orders_history, name='character_market_orders_history'),
    path('market/transactions/', views.wallet_transactions, name='market_transactions'),
    path('character/<int:character_id>/market/transactions/', views.wallet_transactions, name='character_market_transactions'),

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
    path('assets/export/', views.assets_export, name='assets_export'),
    path('character/<int:character_id>/assets/export/', views.assets_export, name='character_assets_export'),

    # Contracts
    path('contracts/', views.contracts_list, name='contracts'),
    path('character/<int:character_id>/contracts/', views.contracts_list, name='character_contracts'),
    path('contracts/<int:contract_id>/', views.contract_detail, name='contract_detail'),
    path('contracts/export/', views.contracts_export, name='contracts_export'),
    path('character/<int:character_id>/contracts/export/', views.contracts_export, name='character_contracts_export'),

    # Industry
    path('industry/', views.industry_summary, name='industry_summary'),
    path('industry/blueprints/', views.blueprints_list, name='blueprints_list'),
    path('character/<int:character_id>/industry/blueprints/', views.blueprints_list, name='character_blueprints_list'),
    path('industry/jobs/', views.industry_jobs_list, name='industry_jobs_list'),
    path('industry/jobs/<int:job_id>/', views.industry_job_detail, name='industry_job_detail'),
    path('character/<int:character_id>/industry/', views.industry_summary, name='character_industry_summary'),
    path('character/<int:character_id>/industry/jobs/', views.industry_jobs, name='character_industry_jobs'),
    path('industry/jobs/export/', views.industry_jobs_export, name='industry_jobs_export'),
    path('character/<int:character_id>/industry/jobs/export/', views.industry_jobs_export, name='character_industry_jobs_export'),

    # Fittings
    path('fittings/', views.fittings_list, name='fittings_list'),
    path('fittings/<int:fitting_id>/', views.fitting_detail, name='fitting_detail'),
    path('fittings/<int:fitting_id>/ignore-toggle/', views.fitting_ignore_toggle, name='fitting_ignore_toggle'),
    path('fittings/matches/', views.fitting_matches, name='fitting_matches'),
    path('character/<int:character_id>/fittings/matches/', views.fitting_matches, name='character_fitting_matches'),
    path('fittings/import/', views.fitting_import, name='fitting_import'),
    path('fittings/<int:fitting_id>/export/<str:format>/', views.fitting_export, name='fitting_export'),
    path('fittings/bulk-import/', views.fitting_bulk_import, name='fitting_bulk_import'),
    path('shopping-lists/', views.shopping_lists_list, name='shopping_lists_list'),
    path('character/<int:character_id>/shopping-lists/', views.shopping_lists_list, name='character_shopping_lists_list'),
    path('shopping-lists/<int:list_id>/', views.shopping_list_detail, name='shopping_list_detail'),

    # SDE Browser (read-only SDE exploration)
    path('sde/', sde_views.sde_index, name='sde_index'),
    path('sde/search', sde_views.sde_search, name='sde_search'),
    path('sde/route/', sde_views.sde_route_planner, name='sde_route_planner'),
    path('sde/item/<int:type_id>/', sde_views.sde_item_detail, name='sde_item_detail'),
    path('sde/ship/<int:ship_id>/', sde_views.sde_ship_detail, name='sde_ship_detail'),
    path('sde/category/<int:category_id>/', sde_views.sde_category_detail, name='sde_category_detail'),
    path('sde/group/<int:group_id>/', sde_views.sde_group_detail, name='sde_group_detail'),
    path('sde/market/<int:group_id>/', sde_views.sde_market_group_detail, name='sde_market_group_detail'),
    path('sde/system/<int:system_id>/', sde_views.sde_system_detail, name='sde_system_detail'),
    path('sde/region/<int:region_id>/', sde_views.sde_region_detail, name='sde_region_detail'),
    path('sde/skill/<int:skill_id>/', sde_views.sde_skill_detail, name='sde_skill_detail'),
    path('sde/blueprint/<int:blueprint_id>/', sde_views.sde_blueprint_detail, name='sde_blueprint_detail'),
    path('sde/variants/<int:type_id>/', sde_views.sde_variant_comparison, name='sde_variant_comparison'),
    path('sde/certificate/<int:cert_id>/', sde_views.sde_certificate_detail, name='sde_certificate_detail'),
    path('sde/industry/', sde_views.sde_industry_activities, name='sde_industry_activities'),
    path('sde/skills/', sde_views.sde_skills_directory, name='sde_skills_directory'),
    path('sde/factions/', sde_views.sde_faction_list, name='sde_faction_list'),
    path('sde/faction/<int:faction_id>/', sde_views.sde_faction_detail, name='sde_faction_detail'),
    path('sde/corporation/<int:corporation_id>/', sde_views.sde_corporation_detail, name='sde_corporation_detail'),
    path('sde/agent/<int:agent_id>/', sde_views.sde_agent_detail, name='sde_agent_detail'),

    # API endpoints
    path('api/assets/locations/', api.api_asset_locations, name='api_asset_locations'),
    path('api/assets/location/<int:location_id>/<str:location_type>/', api.api_location_assets, name='api_location_assets'),
    path('api/assets/<int:asset_id>/children/', api.api_asset_children, name='api_asset_children'),
    path('api/assets/tree/<int:character_id>/', api.api_asset_tree, name='api_asset_tree'),
    path('api/assets/tree/', api.api_asset_tree, name='api_asset_tree_account'),
    path('api/assets/cache/invalidate/', api.api_assets_invalidate_cache, name='api_assets_invalidate_cache'),
]
