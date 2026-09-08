from rest_framework.throttling import SimpleRateThrottle


class PublicEndpointThrottle(SimpleRateThrottle):
    scope = "public"

    def get_cache_key(self, request, view):
        return self.get_ident(request)