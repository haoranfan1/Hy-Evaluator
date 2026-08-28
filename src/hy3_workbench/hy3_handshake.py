"""Explicit command for the bounded Hy3 endpoint handshake."""

import json

from hy3_workbench.config import get_settings
from hy3_workbench.hy3_client import Hy3Client


def main() -> None:
    settings = get_settings()
    if not settings.hy3_configured:
        raise SystemExit(
            "Hy3 is not configured. Set HY3_BASE_URL, HY3_MODEL, and HY3_API_KEY in .env."
        )

    result = Hy3Client(settings).handshake()
    print(json.dumps(result.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
