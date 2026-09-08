from rest_framework.throttling import AnonRateThrottle


class PublicEndpointThrottle(AnonRateThrottle):
    scope = "public"

    def get_cache_key(self, request, view):
        return f"{self.scope}:{self.get_ident(request)}"
