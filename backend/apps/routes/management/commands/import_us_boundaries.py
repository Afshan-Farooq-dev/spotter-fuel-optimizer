import hashlib
from pathlib import Path
from ctypes import POINTER,c_char_p
from django.conf import settings
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.gdal.libgdal import lgdal
from django.contrib.gis.geos import MultiPolygon
from django.core.management.base import BaseCommand,CommandError
from django.db import transaction
from ...models import USStateBoundary
from apps.stations.services.fuel_data import US_STATES

SOURCE="https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_500k.zip"


class Command(BaseCommand):
    help="Import authoritative Census state boundaries for US endpoint and station validation."

    def add_arguments(self,parser):parser.add_argument("archive")

    def handle(self,*args,**options):
        path=Path(options["archive"]).resolve()
        if not path.is_file():raise CommandError("Boundary archive was not found.")
        checksum=hashlib.sha256(path.read_bytes()).hexdigest()
        if settings.PROJ_DATA_DIRECTORY:
            search_paths=(c_char_p*2)(settings.PROJ_DATA_DIRECTORY.encode(),None)
            lgdal.OSRSetPROJSearchPaths.argtypes=[POINTER(c_char_p)]
            lgdal.OSRSetPROJSearchPaths.restype=None
            lgdal.OSRSetPROJSearchPaths(search_paths)
        datasource=DataSource(f"/vsizip/{path.as_posix()}/cb_2024_us_state_500k.shp")
        rows=[]
        for feature in datasource[0]:
            code=feature.get("STUSPS")
            if code not in US_STATES:continue
            geometry=feature.geom.transform(4326,clone=True).geos
            geometry.srid=4326
            if geometry.geom_type=="Polygon":geometry=MultiPolygon(geometry,srid=4326)
            if geometry.geom_type!="MultiPolygon" or not geometry.valid:raise CommandError(f"Invalid boundary: {code}")
            rows.append(USStateBoundary(code=code,geometry=geometry,source_url=SOURCE,source_checksum=checksum))
        if {r.code for r in rows}!=US_STATES:raise CommandError("Archive does not contain all 50 states and DC.")
        with transaction.atomic():
            USStateBoundary.objects.bulk_create(rows,update_conflicts=True,unique_fields=["code"],
                update_fields=["geometry","source_url","source_checksum"])
        self.stdout.write(f"Imported {len(rows)} Census boundaries; SHA-256 {checksum}")
