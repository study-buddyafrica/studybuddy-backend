from rest_framework.throttling import AnonRateThrottle


class PublicEndpointThrottle(AnonRateThrottle):
    scope = "public"