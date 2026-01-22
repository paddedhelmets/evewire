"""
Admin interface for fittings module.
"""

from django.contrib import admin
from django.utils.html import format_html

from core.doctrines.models import (
    Fitting,
    FittingEntry,
    FittingMatch,
    FittingCharge,
    FittingDrone,
    FittingCargoItem,
    FittingService,
    ShoppingList
)


class FittingEntryInline(admin.TabularInline):
    model = FittingEntry
    extra = 0
    readonly_fields = ('module_name', 'usage_percentage')
    fields = ('slot_type', 'position', 'module_type_id', 'is_offline', 'module_name', 'usage_percentage')


class FittingChargeInline(admin.TabularInline):
    model = FittingCharge
    extra = 0
    fields = ('fitting_entry', 'charge_type_id', 'quantity')


class FittingDroneInline(admin.TabularInline):
    model = FittingDrone
    extra = 0
    fields = ('drone_type_id', 'bay_type', 'quantity')


class FittingCargoItemInline(admin.TabularInline):
    model = FittingCargoItem
    extra = 0
    fields = ('item_type_id', 'quantity')


class FittingServiceInline(admin.TabularInline):
    model = FittingService
    extra = 0
    fields = ('service_type_id', 'position')


@admin.register(Fitting)
class FittingAdmin(admin.ModelAdmin):
    list_display = ('name', 'ship_type_name', 'is_active', 'fit_count', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'ship_type_id')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [
        FittingEntryInline,
        FittingChargeInline,
        FittingDroneInline,
        FittingCargoItemInline,
        FittingServiceInline,
    ]

    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'ship_type_id', 'is_active')
        }),
        ('Clustering Metadata', {
            'fields': ('cluster_id', 'fit_count', 'avg_similarity'),
            'classes': ('collapse',),
        }),
        ('Tags', {
            'fields': ('tags',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(FittingMatch)
class FittingMatchAdmin(admin.ModelAdmin):
    list_display = ('character', 'fitting', 'asset_link', 'is_match', 'match_score', 'calculated_at')
    list_filter = ('is_match', 'calculated_at')
    search_fields = ('character__name', 'fitting__name')
    readonly_fields = ('character', 'fitting', 'asset_id', 'is_match', 'match_score',
                       'missing_modules', 'calculated_at')

    def asset_link(self, obj):
        """Link to asset in admin."""
        from core.character.models import CharacterAsset
        try:
            asset = CharacterAsset.objects.get(item_id=obj.asset_id)
            url = f"/admin/core/characterasset/{asset.pk}/change/"
            return format_html('<a href="{}">Asset {}</a>', url, obj.asset_id)
        except CharacterAsset.DoesNotExist:
            return f"Asset {obj.asset_id} (deleted)"
    asset_link.short_description = 'Asset'


@admin.register(ShoppingList)
class ShoppingListAdmin(admin.ModelAdmin):
    list_display = ('character', 'fitting', 'quantity', 'location', 'status', 'total_cost', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('character__name', 'fitting__name')
    readonly_fields = ('created_at', 'updated_at', 'items_to_buy_display')

    fieldsets = (
        (None, {
            'fields': ('character', 'fitting', 'quantity', 'status')
        }),
        ('Location', {
            'fields': ('location_id', 'location_type')
        }),
        ('Results', {
            'fields': ('total_cost', 'items_to_buy_display')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'fulfilled_at'),
            'classes': ('collapse',),
        }),
    )

    def location(self, obj):
        return f"{obj.location_type}:{obj.location_id}"
    location.short_description = 'Location'

    def items_to_buy_display(self, obj):
        """Display items to buy in readable format."""
        if not obj.items_to_buy:
            return "None"

        lines = []
        for type_id, qty in obj.items_to_buy.items():
            from core.eve.models import ItemType
            try:
                item = ItemType.objects.get(id=type_id)
                lines.append(f"{item.name} x{qty}")
            except ItemType.DoesNotExist:
                lines.append(f"Type {type_id} x{qty}")

        return format_html('<br/>'.join(lines))
    items_to_buy_display.short_description = 'Items to Buy'
