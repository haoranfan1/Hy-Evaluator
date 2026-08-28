"""Local development command."""

import uvicorn

from hy3_workbench.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "hy3_workbench.api:app",
        host=settings.workbench_host,
        port=settings.workbench_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
