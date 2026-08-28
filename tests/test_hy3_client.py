from types import SimpleNamespace
from typing import Any

from pydantic import SecretStr

from hy3_workbench.config import Settings
from hy3_workbench.hy3_client import Hy3Client


class FakeCompletions:
    def __init__(self) -> None:
        self.arguments: dict[str, Any] | None = None

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.arguments = kwargs
        message = SimpleNamespace(content="HY3_HANDSHAKE_OK", reasoning_content="checked")
        return SimpleNamespace(
            id="chatcmpl-test",
            model="hy3-test",
            choices=[SimpleNamespace(message=message)],
        )


def test_handshake_uses_nested_hy3_reasoning_configuration() -> None:
    completions = FakeCompletions()
    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    settings = Settings(
        _env_file=None,
        hy3_base_url="https://example.invalid/v1",
        hy3_model="hy3-test",
        hy3_api_key=SecretStr("test-only-key"),
        hy3_reasoning_effort="high",
    )

    result = Hy3Client(settings, client=fake_client).handshake()

    assert result.content_received
    assert result.reasoning_content_received
    assert completions.arguments is not None
    assert completions.arguments["extra_body"] == {
        "chat_template_kwargs": {"reasoning_effort": "high"}
    }
