import math
from decimal import Decimal
from rest_framework import serializers


class LocationField(serializers.Field):
    def to_internal_value(self,value):
        if isinstance(value,str):
            value=value.strip()
            if not value or len(value)>250:raise serializers.ValidationError("Provide a place/address of 1â€“250 characters.")
            return value
        if isinstance(value,dict) and set(value)=={"longitude","latitude"}:
            try:
                if any(isinstance(v,bool) for v in value.values()):raise ValueError()
                longitude=float(value["longitude"]);latitude=float(value["latitude"])
                if not all(math.isfinite(v) for v in (longitude,latitude)):raise ValueError()
                if not (-180<=longitude<=180 and -90<=latitude<=90):raise ValueError()
                return {"longitude":longitude,"latitude":latitude}
            except (TypeError,ValueError,OverflowError):pass
        raise serializers.ValidationError("Use US place text or an object with valid longitude and latitude.")


class OptimizeRouteSerializer(serializers.Serializer):
    start=LocationField()
    destination=LocationField()
    initial_fuel_gallons=serializers.DecimalField(max_digits=5,decimal_places=3,min_value=0,max_value=50,default=Decimal(50))
    reserve_gallons=serializers.DecimalField(max_digits=5,decimal_places=3,min_value=0,max_value=Decimal("49.999"),default=Decimal(0))
    corridor_metres=serializers.IntegerField(min_value=100,max_value=5000,required=False)

    def validate(self,data):
        unknown=set(self.initial_data)-set(self.fields)
        if unknown:raise serializers.ValidationError({key:"Unknown request field." for key in sorted(unknown)})
        if data["reserve_gallons"]>data["initial_fuel_gallons"]:
            raise serializers.ValidationError({"reserve_gallons":"Reserve cannot exceed initial fuel."})
        if data["start"]==data["destination"]:
            raise serializers.ValidationError("Start and destination must be different.")
        return data
