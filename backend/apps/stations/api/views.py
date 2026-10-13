from django.db import DatabaseError, connection
from rest_framework import generics
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from ..models import FuelStation, StationLocation
from .serializers import StationFilters, StationSerializer


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return Response({"status": "unavailable", "database": "unavailable"}, status=503)
    return Response({"status": "ok", "database": "ok"})


class StationPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


class StationQueryMixin:
    serializer_class = StationSerializer
    permission_classes = [AllowAny]
    filter_backends = [SearchFilter]
    search_fields = ["name", "city", "source_id", "address"]

    def get_queryset(self):
        query = {key: self.request.query_params[key] for key in ("state", "geocoded", "source_id")
                 if key in self.request.query_params}
        if "state" in query:
            query["state"] = query["state"].upper()
        filters = StationFilters(data=query)
        filters.is_valid(raise_exception=True)
        params = filters.validated_data
        stations = FuelStation.objects.select_related("location", "active_dataset").order_by("id")
        if "state" in params:
            stations = stations.filter(state=params["state"])
        if "source_id" in params:
            stations = stations.filter(source_id=params["source_id"])
        if "geocoded" in params:
            if params["geocoded"]:
                stations = stations.filter(location__status=StationLocation.Status.VERIFIED, location__point__isnull=False)
            else:
                stations = stations.exclude(location__status=StationLocation.Status.VERIFIED)
        return stations


class StationList(StationQueryMixin, generics.ListAPIView):
    pagination_class = StationPagination


class StationDetail(StationQueryMixin, generics.RetrieveAPIView):
    pass
