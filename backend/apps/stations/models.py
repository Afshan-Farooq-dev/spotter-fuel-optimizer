"""Station identities, immutable source observations, and verified geocoding results."""
import math
from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db.models.functions import Cast
from django.contrib.postgres.indexes import GistIndex
from .services.fuel_data import US_STATES


class FuelDataset(models.Model):
    checksum = models.CharField(max_length=64, unique=True)
    source_name = models.CharField(max_length=255)
    report = models.JSONField(default=dict)
    imported_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)


class FuelStation(models.Model):
    source_id = models.CharField(max_length=64, unique=True)
    name = models.TextField()
    aliases = models.JSONField(default=list)
    address = models.TextField()
    city = models.TextField()
    state = models.CharField(max_length=2, db_index=True)
    median_price = models.DecimalField(max_digits=18, decimal_places=10)
    active_dataset = models.ForeignKey(FuelDataset, on_delete=models.PROTECT)
    price_conflict = models.BooleanField(default=False)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(condition=Q(median_price__gt=0), name="station_positive_price"),
            models.CheckConstraint(condition=Q(state__in=sorted(US_STATES)), name="station_us_state"),
        ]

    def __str__(self):
        return f"{self.source_id}: {self.name}"


class FuelPrice(models.Model):
    station = models.ForeignKey(FuelStation, on_delete=models.CASCADE, related_name="prices")
    dataset = models.ForeignKey(FuelDataset, on_delete=models.PROTECT, related_name="prices")
    source_row = models.PositiveIntegerField()
    source_name = models.TextField()
    rack_id = models.CharField(max_length=64)
    price = models.DecimalField(max_digits=18, decimal_places=10)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["dataset", "source_row"], name="unique_dataset_price_row"),
            models.CheckConstraint(condition=Q(price__gt=0), name="source_positive_price"),
            models.CheckConstraint(condition=Q(source_row__gte=2), name="source_data_row"),
        ]
        indexes = [models.Index(fields=["station", "dataset"])]


class GeocodingCache(models.Model):
    key = models.CharField(max_length=64, unique=True)
    provider = models.CharField(max_length=64)
    query = models.JSONField()
    response = models.JSONField()
    fetched_at = models.DateTimeField(auto_now_add=True)


class StationLocation(models.Model):
    class Status(models.TextChoices):
        UNRESOLVED = "unresolved"
        VERIFIED = "verified"
        NO_MATCH = "no_match"
        AMBIGUOUS = "ambiguous"

    station = models.OneToOneField(FuelStation, on_delete=models.CASCADE, related_name="location")
    point = models.PointField(srid=4326, null=True, blank=True, spatial_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.UNRESOLVED)
    provider = models.CharField(max_length=64, blank=True)
    matched_address = models.TextField(blank=True)
    country_code = models.CharField(max_length=3, blank=True)
    region_code = models.CharField(max_length=2, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    precision = models.CharField(max_length=32, blank=True)
    cache = models.ForeignKey(GeocodingCache, null=True, blank=True, on_delete=models.SET_NULL)
    checked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [GistIndex(Cast("point",output_field=models.PointField(srid=4326,geography=True)),
                             name="station_point_geog_idx")]
        constraints = [
            models.CheckConstraint(
                condition=(Q(status="verified", point__isnull=False, country_code="USA")
                           | (~Q(status="verified") & Q(point__isnull=True))),
                name="verified_location_requires_us_point",
            ),
            models.CheckConstraint(
                condition=Q(confidence__isnull=True) | Q(confidence__gte=0, confidence__lte=1),
                name="geocode_confidence_range",
            ),
        ]

    def clean(self):
        if self.point is not None:
            if self.point.srid != 4326 or not all(math.isfinite(v) for v in self.point.coords):
                raise ValidationError("Coordinates must be finite WGS84 longitude/latitude.")
            if not (-180 <= self.point.x <= 180 and -90 <= self.point.y <= 90):
                raise ValidationError("Longitude or latitude is outside its valid range.")
        if self.status == self.Status.VERIFIED:
            if self.point is None or self.country_code != "USA" or self.region_code != self.station.state:
                raise ValidationError("Verified coordinates require a matching US country and state.")
