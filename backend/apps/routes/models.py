from django.contrib.gis.db import models


class RouteGeometryCache(models.Model):
    key=models.CharField(max_length=64,unique=True)
    provider=models.CharField(max_length=64)
    coordinates=models.JSONField()
    payload=models.JSONField()
    expires_at=models.DateTimeField(db_index=True)
    created_at=models.DateTimeField(auto_now_add=True)


class USStateBoundary(models.Model):
    code=models.CharField(max_length=2,unique=True)
    geometry=models.MultiPolygonField(srid=4326,spatial_index=True)
    source_url=models.URLField()
    source_checksum=models.CharField(max_length=64)
