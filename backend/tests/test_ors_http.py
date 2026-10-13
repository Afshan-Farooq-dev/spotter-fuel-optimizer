import io,json
from unittest.mock import patch
from urllib.error import HTTPError
import pytest
from django.core.cache import cache
from apps.routes.providers.http import ORSClient,RateLimited
from apps.routes.services.domain import ProviderError


def test_missing_key_makes_no_request():
    with patch("apps.routes.providers.http.urlopen") as request:
        with pytest.raises(ProviderError):ORSClient("").json_request("https://example.test")
    request.assert_not_called()


def test_success_and_no_credential_in_url():
    with patch("apps.routes.providers.http.urlopen",return_value=io.BytesIO(b'{"ok":true}')) as request:
        assert ORSClient("private-key",interval=0).json_request("https://example.test",body={"a":1})=={"ok":True}
    outgoing=request.call_args.args[0]
    assert "private-key" not in outgoing.full_url
    assert outgoing.get_header("Authorization")=="private-key"


def test_rate_limit_is_not_retried():
    cache.delete("ors-provider-cooldown")
    error=HTTPError("https://example.test",429,"limited",{"Retry-After":"2"},None)
    with patch("apps.routes.providers.http.urlopen",side_effect=error) as request:
        with pytest.raises(RateLimited) as caught:ORSClient("key",interval=0).json_request("https://example.test")
    assert caught.value.retry_after==2 and request.call_count==1
    cache.delete("ors-provider-cooldown")


def test_nonfinite_provider_json_is_rejected():
    with patch("apps.routes.providers.http.urlopen",return_value=io.BytesIO(b'{"x":NaN}')):
        with pytest.raises(ProviderError):ORSClient("key",interval=0).json_request("https://example.test")
