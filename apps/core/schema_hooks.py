from __future__ import annotations


def preprocess_api_canonical_endpoints(endpoints):
    """Keep only canonical API endpoints in OpenAPI output.

    - include only /api/... paths
    - when both /path and /path/ exist for same method, keep /path/
    """

    endpoint_keys = {(path, method) for path, _, method, _ in endpoints}
    filtered = []

    for path, path_regex, method, callback in endpoints:
        if not path.startswith("/api/"):
            continue

        if not path.endswith("/") and (f"{path}/", method) in endpoint_keys:
            continue

        filtered.append((path, path_regex, method, callback))

    return filtered
