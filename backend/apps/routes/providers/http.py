"""Small authenticated JSON transport with bounded retries and safe errors."""
import json
import time
import threading
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen
from django.core.cache import cache
from ..services.domain import ProviderError

_LOCK=threading.Lock()
_LAST_CALL=0.0


class RateLimited(ProviderError):
    code="provider_rate_limited"
    def __init__(self,retry_after=60):
        self.retry_after=retry_after
        super().__init__("ORS rate limit reached; retry after the indicated delay.")


def reject_constant(value):
    raise ValueError("Nonfinite JSON value")


class ORSClient:
    def __init__(self,key,*,timeout=15,retries=1,interval=1.6):
        self.key=key;self.timeout=timeout;self.retries=retries;self.interval=interval
        self.calls=0

    def json_request(self,url,*,body=None):
        global _LAST_CALL
        if not self.key:
            raise ProviderError("Set ORS_API_KEY in the local .env to enable live ORS calls.")
        cooldown=cache.get("ors-provider-cooldown",0)
        if cooldown>time.time():raise RateLimited(max(1,int(cooldown-time.time())))
        data=json.dumps(body,allow_nan=False).encode() if body is not None else None
        request=Request(url,data=data,headers={"Authorization":self.key,"Content-Type":"application/json",
                                            "User-Agent":"SpotterFuelOptimizer/2.0"})
        for attempt in range(self.retries+1):
            with _LOCK:
                time.sleep(max(0,self.interval-(time.monotonic()-_LAST_CALL)))
                _LAST_CALL=time.monotonic()
            self.calls+=1
            try:
                with urlopen(request,timeout=self.timeout) as response:
                    payload=response.read(12_000_001)
                if len(payload)>12_000_000:raise ProviderError("ORS response exceeded the size limit.")
                result=json.loads(payload,parse_constant=reject_constant)
                if not isinstance(result,dict):raise ProviderError("ORS returned an invalid JSON object.")
                return result
            except HTTPError as error:
                if error.code==429:
                    value=error.headers.get("Retry-After","60")
                    delay=max(1,min(3600,int(value))) if value.isdigit() else 60
                    cache.set("ors-provider-cooldown",time.time()+delay,timeout=delay)
                    raise RateLimited(delay) from None
                if error.code in (400,404):
                    raise ProviderError("ORS could not find a supported driving route or location.") from None
                if error.code in (401,403):
                    raise ProviderError("ORS rejected the API key or its permissions.") from None
                if error.code not in (500,502,503,504) or attempt==self.retries:
                    raise ProviderError(f"ORS returned HTTP {error.code}.") from None
            except (URLError,TimeoutError,OSError):
                if attempt==self.retries:raise ProviderError("ORS was unreachable or timed out.") from None
            except (ValueError,UnicodeError):
                raise ProviderError("ORS returned malformed JSON.") from None
            time.sleep(0.25*(2**attempt))
