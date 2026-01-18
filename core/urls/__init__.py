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
    path('character/<int:character_id>/skills/', views.character_skills, name='character_skills'),
    path('character/<int:character_id>/sync/', views.sync_character, name='sync_character'),
]
