"""Small OpenAI-compatible client for the Hy3 endpoint."""

from typing import Any, Literal

from openai import OpenAI
from pydantic import BaseModel

from hy3_workbench.config import Settings
from hy3_workbench.contracts import SemanticReviewOutput


class Hy3HandshakeResult(BaseModel):
    """Non-secret result of one bounded compatibility request."""

    response_id: str | None
    model: str | None
    content_received: bool
    reasoning_content_received: bool


class Hy3StructuredCompatibilityResult(BaseModel):
    """Sanitized result of one structured semantic-schema request."""

    response_id: str | None
    model: str | None
    response_format: Literal["json_object"] = "json_object"
    reasoning_content_received: bool
    semantic_output: SemanticReviewOutput


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

    def structured_compatibility(self) -> Hy3StructuredCompatibilityResult:
        """Request one JSON object and validate it against the semantic contract.

        The Hy3 endpoint is asked for JSON-object mode while Pydantic remains the
        source of truth. Full JSON Schema enforcement by the server is not assumed.
        """

        response = self._client.chat.completions.create(
            model=self.settings.hy3_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return exactly one JSON object and no Markdown. The object must "
                        "match the semantic-review-v1 contract described by the user."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Compatibility case: no material process error exists. Return these "
                        "fields: schema_version='semantic-review-v1'; process_status='valid'; "
                        "first_error with location='none', null step_id, null tool_call_id, "
                        "and null primary_category; findings=[]; and a non-empty summary."
                    ),
                },
            ],
            temperature=self.settings.hy3_temperature,
            top_p=self.settings.hy3_top_p,
            response_format={"type": "json_object"},
            extra_body={
                "chat_template_kwargs": {
                    "reasoning_effort": self.settings.hy3_reasoning_effort,
                }
            },
        )

        message = response.choices[0].message
        content = message.content or ""
        if not content.strip():
            raise ValueError("Hy3 structured compatibility response contained no JSON content.")
        semantic_output = SemanticReviewOutput.model_validate_json(content)
        return Hy3StructuredCompatibilityResult(
            response_id=getattr(response, "id", None),
            model=getattr(response, "model", None),
            reasoning_content_received=bool(getattr(message, "reasoning_content", None)),
            semantic_output=semantic_output,
        )
