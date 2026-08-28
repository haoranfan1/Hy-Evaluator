"""FastAPI application entry point."""

from typing import Annotated, Literal

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from hy3_workbench import __version__
from hy3_workbench.config import Settings, get_settings


class ComponentHealth(BaseModel):
    status: Literal["ready", "not_configured"]
    detail: str


class HealthResponse(BaseModel):
    status: Literal["ready", "degraded"]
    version: str
    components: dict[str, ComponentHealth]


app = FastAPI(
    title="Hy3 Process Evaluation Workbench",
    version=__version__,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

SettingsDependency = Annotated[Settings, Depends(get_settings)]


@app.get("/api/health", response_model=HealthResponse)
def health(settings: SettingsDependency) -> HealthResponse:
    """Report configuration readiness without making a model or Docker request."""

    hy3_status = "ready" if settings.hy3_configured else "not_configured"
    overall_status = "ready" if settings.hy3_configured else "degraded"
    return HealthResponse(
        status=overall_status,
        version=__version__,
        components={
            "api": ComponentHealth(status="ready", detail="API process is responsive."),
            "hy3": ComponentHealth(
                status=hy3_status,
                detail=(
                    "Hy3 endpoint, model, and API key are configured."
                    if settings.hy3_configured
                    else "Set HY3_BASE_URL, HY3_MODEL, and HY3_API_KEY locally."
                ),
            ),
        },
    )
