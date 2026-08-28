from pydantic import SecretStr

from hy3_workbench.config import Settings


def test_hy3_configuration_requires_all_three_values() -> None:
    assert not Settings(_env_file=None).hy3_configured

    configured = Settings(
        _env_file=None,
        hy3_base_url="https://example.invalid/v1",
        hy3_model="hy3",
        hy3_api_key=SecretStr("test-only-key"),
    )

    assert configured.hy3_configured
