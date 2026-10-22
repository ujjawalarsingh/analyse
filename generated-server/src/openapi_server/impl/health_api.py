from openapi_server.apis.health_api_base import BaseHealthApi
from openapi_server.models.health_response import HealthResponse


class HealthApi(BaseHealthApi):
    async def health(self) -> HealthResponse:
        return HealthResponse(status="ok")