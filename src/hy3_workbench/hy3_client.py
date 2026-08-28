"""Small OpenAI-compatible client for the Hy3 endpoint."""

from typing import Any

from openai import OpenAI
from pydantic import BaseModel

from hy3_workbench.config import Settings


class Hy3HandshakeResult(BaseModel):
    """Non-secret result of one bounded compatibility request."""

    response_id: str | None
    model: str | None
    content_received: bool
    reasoning_content_received: bool


class Hy3Client:
    """Wrap the exact Hy3 Chat Completions configuration used by the evaluator."""

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        if not settings.hy3_configured:
            raise ValueError("HY3_BASE_URL, HY3_MODEL, and HY3_API_KEY are required.")

        self.settings = settings
        self._client = client or OpenAI(
            api_key=settings.hy3_api_key.get_secret_value(),
            base_url=str(settings.hy3_base_url),
            timeout=settings.hy3_timeout_seconds,
            max_retries=0,
        )

    def handshake(self) -> Hy3HandshakeResult:
        """Make one minimal request; callers decide when an external call is allowed."""

        response = self._client.chat.completions.create(
            model=self.settings.hy3_model,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Reply with exactly HY3_HANDSHAKE_OK. Do not add explanation or Markdown."
                    ),
                }
            ],
            temperature=self.settings.hy3_temperature,
            top_p=self.settings.hy3_top_p,
            extra_body={
                "chat_template_kwargs": {
                    "reasoning_effort": self.settings.hy3_reasoning_effort,
                }
            },
        )

        message = response.choices[0].message
        content = message.content or ""
        reasoning_content = getattr(message, "reasoning_content", None)
        return Hy3HandshakeResult(
            response_id=getattr(response, "id", None),
            model=getattr(response, "model", None),
            content_received=bool(content.strip()),
            reasoning_content_received=bool(reasoning_content),
        )
