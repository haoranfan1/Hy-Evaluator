import pytest
from httpx import ASGITransport, AsyncClient

from hy3_workbench.api import app
from hy3_workbench.config import Settings, get_settings


@pytest.mark.asyncio
async def test_health_does_not_call_or_expose_hy3() -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["components"]["hy3"]["status"] == "not_configured"
    assert "test-only-key" not in response.text
