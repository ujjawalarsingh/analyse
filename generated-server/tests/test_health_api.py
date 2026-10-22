# coding: utf-8

from fastapi.testclient import TestClient


from openapi_server.models.health_response import HealthResponse  # noqa: F401


def test_health(client: TestClient):
    """Test case for health

    Liveness check
    """

    headers = {
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/health",
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200

