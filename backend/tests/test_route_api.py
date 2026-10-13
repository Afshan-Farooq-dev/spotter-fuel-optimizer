from unittest.mock import patch
from rest_framework.test import APIClient
from apps.routes.services.domain import ProviderError
from apps.routes.providers.http import RateLimited
from test_route_input import BASE


def test_invalid_body_does_not_plan():
    with patch("apps.routes.api.views.plan_route") as planner:
        response=APIClient().post("/api/routes/optimize/",{"start":""},format="json")
    assert response.status_code==400
    planner.assert_not_called()


def test_success_is_post_only():
    with patch("apps.routes.api.views.plan_route",return_value={"total_cost":"0.00","geometry":{"type":"LineString"}}):
        response=APIClient().post("/api/routes/optimize/",BASE,format="json")
    assert response.status_code==200 and response.json()["total_cost"]=="0.00"
    assert APIClient().get("/api/routes/optimize/").status_code==405


def test_provider_error_is_safe():
    with patch("apps.routes.api.views.plan_route",side_effect=ProviderError("ORS unavailable")):
        response=APIClient().post("/api/routes/optimize/",BASE,format="json")
    assert response.status_code==503 and response.json()["error"]["code"]=="routing_provider_unavailable"


def test_rate_limit_preserves_retry_header():
    with patch("apps.routes.api.views.plan_route",side_effect=RateLimited(12)):
        response=APIClient().post("/api/routes/optimize/",BASE,format="json")
    assert response.status_code==503 and response["Retry-After"]=="12"
