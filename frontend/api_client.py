import os

import requests

BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")


class APIConnectionError(RuntimeError):
    pass


def request(method, path, token=None, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        return requests.request(method, f"{BASE}{path}", headers=headers, timeout=30, **kwargs)
    except requests.RequestException as exc:
        raise APIConnectionError(
            "Unable to reach the PortfolioPulse API. Confirm the backend is running and try again."
        ) from exc
