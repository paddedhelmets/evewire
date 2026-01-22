"""
Django admin configuration for evewire.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from mptt.admin import MPTTModelAdmin
from .models import User, Character, AuditLog
from .eve.models import ItemType, SolarSystem, Station, Region, Faction, Corporation, Alliance
from .character.models import CharacterSkill, SkillQueueItem, CharacterAsset, WalletJournalEntry, WalletTransaction, MarketOrder
from .trade.models import Campaign


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

    list_display = ['name', 'id', 'user', 'total_sp', 'wallet_balance', 'last_sync_status', 'last_sync']
    list_filter = ['last_sync_status', 'created_at']
    search_fields = ['name', 'id', 'user__eve_character_name']
    readonly_fields = ['id', 'user', 'created_at', 'updated_at']

    fieldsets = (
        (None, {'fields': ('id', 'user')}),
        ('Cached Data', {'fields': ('total_sp', 'wallet_balance')}),
        ('Sync Status', {'fields': ('skills_synced_at', 'wallet_synced_at', 'last_sync_status', 'last_sync_error')}),
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


# EVE reference data models

@admin.register(ItemType)
class ItemTypeAdmin(admin.ModelAdmin):
    """Admin interface for ItemType model."""

    list_display = ['id', 'name', 'group_id', 'category_id', 'published']
    list_filter = ['published', 'group_id']
    search_fields = ['name', 'id']
    ordering = ['name']


@admin.register(SolarSystem)
class SolarSystemAdmin(admin.ModelAdmin):
    """Admin interface for SolarSystem model."""

    list_display = ['id', 'name', 'region_id', 'security', 'security_class']
    list_filter = ['region_id', 'security_class']
    search_fields = ['name', 'id']
    ordering = ['name']


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    """Admin interface for Station model."""

    list_display = ['id', 'name', 'solar_system_id', 'region_id', 'corporation_id']
    list_filter = ['region_id', 'corporation_id']
    search_fields = ['name', 'id']
    ordering = ['name']


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    """Admin interface for Region model."""

    list_display = ['id', 'name']
    search_fields = ['name', 'id']
    ordering = ['name']


@admin.register(Faction)
class FactionAdmin(admin.ModelAdmin):
    """Admin interface for Faction model."""

    list_display = ['id', 'name', 'solar_system_id', 'corporation_id']
    search_fields = ['name', 'id']
    ordering = ['name']


@admin.register(Corporation)
class CorporationAdmin(admin.ModelAdmin):
    """Admin interface for Corporation model."""

    list_display = ['id', 'name', 'ticker', 'faction_id', 'is_npc']
    list_filter = ['is_npc', 'faction_id']
    search_fields = ['name', 'ticker', 'id']
    ordering = ['name']


@admin.register(Alliance)
class AllianceAdmin(admin.ModelAdmin):
    """Admin interface for Alliance model."""

    list_display = ['id', 'name', 'ticker', 'creator_corporation_id', 'date_founded']
    search_fields = ['name', 'ticker', 'id']
    ordering = ['name']


# Character data models

@admin.register(CharacterSkill)
class CharacterSkillAdmin(admin.ModelAdmin):
    """Admin interface for CharacterSkill model."""

    list_display = ['character', 'skill_id', 'skill_name', 'skill_level', 'skillpoints_in_skill']
    list_filter = ['skill_level']
    search_fields = ['character__user__eve_character_name', 'skill_id']
    readonly_fields = ['synced_at']

    def skill_name(self, obj):
        return obj.skill_name
    skill_name.short_description = 'Skill'


@admin.register(SkillQueueItem)
class SkillQueueItemAdmin(admin.ModelAdmin):
    """Admin interface for SkillQueueItem model."""

    list_display = ['character', 'queue_position', 'skill_id', 'skill_name', 'finish_level', 'finish_date', 'is_completed']
    list_filter = ['finish_level']
    search_fields = ['character__user__eve_character_name', 'skill_id']
    readonly_fields = ['synced_at']

    def skill_name(self, obj):
        return obj.skill_name
    skill_name.short_description = 'Skill'


@admin.register(CharacterAsset)
class CharacterAssetAdmin(MPTTModelAdmin):
    """Admin interface for CharacterAsset model."""

    list_display = ['character', 'item_id', 'type_name', 'quantity', 'location_flag', 'location_name']
    list_filter = ['location_type', 'location_flag']
    search_fields = ['character__user__eve_character_name', 'type_id', 'item_id']
    readonly_fields = ['synced_at']

    def type_name(self, obj):
        return obj.type_name
    type_name.short_description = 'Type'


@admin.register(WalletJournalEntry)
class WalletJournalEntryAdmin(admin.ModelAdmin):
    """Admin interface for WalletJournalEntry model."""

    list_display = ['character', 'date', 'ref_type', 'amount', 'balance', 'description']
    list_filter = ['ref_type', 'date']
    search_fields = ['character__user__eve_character_name', 'description']
    readonly_fields = ['synced_at']
    ordering = ['-date']


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    """Admin interface for WalletTransaction model."""

    list_display = ['character', 'date', 'is_buy', 'type_id', 'quantity', 'unit_price', 'total_value']
    list_filter = ['is_buy', 'date']
    search_fields = ['character__user__eve_character_name', 'type_id']
    readonly_fields = ['synced_at']
    ordering = ['-date']

    def total_value(self, obj):
        return obj.total_value
    total_value.short_description = 'Total Value'


@admin.register(MarketOrder)
class MarketOrderAdmin(admin.ModelAdmin):
    """Admin interface for MarketOrder model."""

    list_display = ['character', 'order_id', 'is_buy_order', 'type_id', 'price', 'volume_remain', 'state', 'expires_at']
    list_filter = ['is_buy_order', 'state', 'region_id']
    search_fields = ['character__user__eve_character_name', 'type_id', 'order_id']
    readonly_fields = ['synced_at']
    ordering = ['-issued']


# Trade analysis models

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    """Admin interface for Campaign model."""

    list_display = ['title', 'user', 'start_date', 'end_date', 'created_at']
    list_filter = ['created_at', 'start_date']
    search_fields = ['title', 'slug', 'user__eve_character_name']
    readonly_fields = ['created_at']
    filter_horizontal = ['characters']
    prepopulated_fields = {'slug': ('title',)}

    fieldsets = (
        (None, {'fields': ('user', 'title', 'slug', 'description')}),
        ('Date Range', {'fields': ('start_date', 'end_date')}),
        ('Filters', {'fields': ('characters',)}),
        ('Metadata', {'fields': ('created_at',)}),
    )
