from django.conf import settings
from django.http import JsonResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.decorators import api_view, throttle_classes
from apps.core.throttling import PublicEndpointThrottle


@extend_schema(
    summary="Get the Excalidraw whiteboard link",
    responses={200: OpenApiResponse(description="Configured whiteboard link")},
)
@api_view(["GET"])
@throttle_classes([PublicEndpointThrottle])
def whiteboard_link(request):
    return JsonResponse(
        {
            "link": getattr(
                settings,
                "DEFAULT_WHITEBOARD_LINK",
                "https://excalidraw.com/",
            )
        }
    )
