from __future__ import annotations


def preprocess_api_canonical_endpoints(endpoints):
    """Keep only canonical API endpoints in OpenAPI output.

    - include only /api/... paths
    - when both /path and /path/ exist for same method, keep /path/
    """

    endpoint_keys = {(path, method) for path, _, method, _ in endpoints}

    def _should_drop_parameterized_duplicate(path: str, method: str) -> bool:
        # Keep canonical docs paths for compatibility endpoints and drop legacy variants
        # that only differ by an extra id segment.
        if path.startswith("/api/parent/profile/update/") and "{id}" in path:
            return ("/api/parent/profile/update/", method) in endpoint_keys

        if path.startswith("/api/student/profile/update/") and ("{id}" in path):
            return ("/api/student/profile/update/", method) in endpoint_keys

        if path.startswith("/api/student/session-bookings/") and ("{pk}" in path):
            return ("/api/student/session-bookings/", method) in endpoint_keys

        if (
            path.startswith("/api/parent/")
            and "{parent_id}" in path
            and "register-student" in path
        ):
            return ("/api/parent/register-student/", method) in endpoint_keys

        return False

    filtered = []

    for path, path_regex, method, callback in endpoints:
        if not path.startswith("/api/"):
            continue

        if "/undefined/" in path or path.endswith("/undefined"):
            continue

        if not path.endswith("/") and (f"{path}/", method) in endpoint_keys:
            continue

        if _should_drop_parameterized_duplicate(path, method):
            continue

        filtered.append((path, path_regex, method, callback))

    return filtered
