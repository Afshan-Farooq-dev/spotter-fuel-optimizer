from rest_framework import serializers
from ..models import FuelStation, StationLocation
from ..services.fuel_data import US_STATES


class StationFilters(serializers.Serializer):
    state = serializers.ChoiceField(choices=sorted(US_STATES), required=False)
    geocoded = serializers.BooleanField(required=False)
    source_id = serializers.CharField(max_length=64, required=False)


class StationLocationSerializer(serializers.ModelSerializer):
    coordinates = serializers.SerializerMethodField()

    class Meta:
        model = StationLocation
        fields = ("status", "coordinates", "provider", "matched_address", "country_code",
                  "region_code", "confidence", "precision", "checked_at")
        read_only_fields = fields

    def get_coordinates(self, location):
        if location.status != StationLocation.Status.VERIFIED or location.point is None:
            return None
        return {"longitude": location.point.x, "latitude": location.point.y}


class StationSerializer(serializers.ModelSerializer):
    location = StationLocationSerializer(read_only=True)
    dataset_checksum = serializers.CharField(source="active_dataset.checksum", read_only=True)

    class Meta:
        model = FuelStation
        fields = ("id", "source_id", "name", "aliases", "address", "city", "state",
                  "median_price", "price_conflict", "dataset_checksum", "location")
        read_only_fields = fields

    def to_representation(self, instance):
        result = super().to_representation(instance)
        if result["location"] is None:
            result["location"] = {"status": "unresolved", "coordinates": None}
        result["price_currency"] = "USD"
        result["price_unit"] = "US gallon"
        result["price_method"] = "median"
        return result
