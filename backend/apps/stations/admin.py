from django.contrib import admin
from .models import FuelDataset, FuelPrice, FuelStation, GeocodingCache, StationLocation


@admin.register(FuelStation)
class FuelStationAdmin(admin.ModelAdmin):
    list_display = ("source_id", "name", "city", "state", "median_price")
    list_filter = ("state", "price_conflict")
    search_fields = ("source_id", "name", "city")


admin.site.register([FuelDataset, FuelPrice, StationLocation, GeocodingCache])
