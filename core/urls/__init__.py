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
    path('character/<int:character_id>/', views.character_detail, name='character_detail'),
    path('character/<int:character_id>/sync/', views.sync_character, name='sync_character'),
    path('theme/toggle/', views.toggle_theme, name='toggle_theme'),

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

    # Wallet
    path('wallet/journal/', views.wallet_journal, name='wallet_journal'),
    path('wallet/transactions/', views.wallet_transactions, name='wallet_transactions'),
    path('wallet/balance/', views.wallet_balance, name='wallet_balance'),
    path('wallet/summary/', views.wallet_summary, name='wallet_summary'),
    path('character/<int:character_id>/wallet/journal/', views.wallet_journal, name='character_wallet_journal'),
    path('character/<int:character_id>/wallet/transactions/', views.wallet_transactions, name='character_wallet_transactions'),
    path('character/<int:character_id>/wallet/balance/', views.wallet_balance, name='character_wallet_balance'),
    path('character/<int:character_id>/wallet/summary/', views.wallet_summary, name='character_wallet_summary'),
]
