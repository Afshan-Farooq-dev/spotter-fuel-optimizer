from django.urls import path
from .views import StationDetail, StationList, health

urlpatterns = [
    path("health/", health, name="health"),
    path("stations/", StationList.as_view(), name="station-list"),
    path("stations/<int:pk>/", StationDetail.as_view(), name="station-detail"),
]
