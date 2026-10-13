import time
from django.db import DatabaseError
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from ..services.domain import PlanningError
from ..services.planning import plan_route
from .serializers import OptimizeRouteSerializer


class OptimizeRouteView(APIView):
    permission_classes=[AllowAny]
    authentication_classes=[]
    throttle_classes=[ScopedRateThrottle]
    throttle_scope="route_optimization"

    def post(self,request):
        serializer=OptimizeRouteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        started=time.perf_counter()
        try:result=plan_route(serializer.validated_data)
        except PlanningError as error:
            body={"error":{"code":error.code,"message":str(error),"details":getattr(error,"details",{})}}
            headers={}
            if hasattr(error,"retry_after"):headers["Retry-After"]=str(error.retry_after)
            return Response(body,status=error.status,headers=headers)
        except DatabaseError:
            return Response({"error":{"code":"database_unavailable","message":"Database unavailable."}},status=503)
        result["elapsed_ms"]=round((time.perf_counter()-started)*1000,2)
        return Response(result)
