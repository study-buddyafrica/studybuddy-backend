from django.conf import settings
from django.http import JsonResponse


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
