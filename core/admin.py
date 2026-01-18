"""
Django admin configuration for evewire.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Character, AuditLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model."""

    list_display = ['eve_character_name', 'eve_character_id', 'corporation_name', 'is_active', 'last_login']
    list_filter = ['is_active', 'is_staff', 'created_at']
    search_fields = ['eve_character_name', 'eve_character_id']
    ordering = ['eve_character_name']

    fieldsets = (
        (None, {'fields': ('eve_character_id', 'eve_character_name')}),
        ('Corporation/Alliance', {'fields': ('corporation_id', 'corporation_name', 'alliance_id', 'alliance_name')}),
        ('OAuth', {'fields': ('token_expires', 'has_valid_token')}),
        ('Metadata', {'fields': ('created_at', 'updated_at', 'last_login', 'last_sync')}),
        ('Settings', {'fields': ('settings',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )

    readonly_fields = ['eve_character_id', 'eve_character_name', 'created_at', 'updated_at', 'last_login']

    def has_valid_token(self, obj):
        return obj.has_valid_token()
    has_valid_token.boolean = True
    has_valid_token.short_description = 'Has Token'


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    """Admin interface for Character model."""

    list_display = ['name', 'id', 'user', 'last_sync_status', 'last_sync']
    list_filter = ['last_sync_status', 'created_at']
    search_fields = ['name', 'id', 'user__eve_character_name']
    readonly_fields = ['id', 'user', 'created_at', 'updated_at']

    fieldsets = (
        (None, {'fields': ('id', 'user')}),
        ('Data Status', {'fields': ('skills_synced_at', 'skill_queue_synced_at', 'wallet_synced_at', 'assets_synced_at', 'orders_synced_at')}),
        ('Sync Status', {'fields': ('last_sync_status', 'last_sync_error')}),
        ('Metadata', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin interface for AuditLog model."""

    list_display = ['user', 'action', 'ip_address', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['user__eve_character_name', 'action', 'ip_address']
    readonly_fields = ['user', 'action', 'ip_address', 'user_agent', 'metadata', 'created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
