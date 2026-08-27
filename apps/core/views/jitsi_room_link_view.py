from django.http import JsonResponse
import uuid


def jitsi_room_link(request):
    room_name = f"studybuddy-room-{uuid.uuid4().hex[:8]}"
    link = f"https://meet.jit.si/{room_name}"
    return JsonResponse({"link": link})
