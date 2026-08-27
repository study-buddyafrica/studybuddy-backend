from django.http import JsonResponse
import uuid
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.decorators import api_view


@extend_schema(
    summary="Generate a Jitsi room link",
    responses={200: OpenApiResponse(description="Generated Jitsi room link")},
)
@api_view(["GET"])
def jitsi_room_link(request):
    room_name = f"studybuddy-room-{uuid.uuid4().hex[:8]}"
    link = f"https://meet.jit.si/{room_name}"
    return JsonResponse({"link": link})
