import pytest
from pydantic import ValidationError

from async_fetcher import FetcherConfig


def test_default_config_values() -> None:
    config = FetcherConfig()

    assert config.timeout == 10.0
    assert config.max_concurrency == 20
    assert config.max_connections == 20
    assert config.max_keepalive_connections == 10
    assert config.max_retries == 3
    assert config.backoff_factor == 0.5
    assert config.max_backoff == 30.0
    assert config.follow_redirects is True
    assert config.raise_on_http_error is False
    assert config.log_level == "INFO"


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf")])
def test_invalid_timeout(timeout: float) -> None:
    with pytest.raises(ValidationError):
        FetcherConfig(timeout=timeout)


@pytest.mark.parametrize("value", [-1, 0])
def test_invalid_max_concurrency(value: int) -> None:
    with pytest.raises(ValidationError):
        FetcherConfig(max_concurrency=value)


@pytest.mark.parametrize("value", [-1, 11])
def test_invalid_max_retries(value: int) -> None:
    with pytest.raises(ValidationError):
        FetcherConfig(max_retries=value)


def test_keepalive_cannot_exceed_max_connections() -> None:
    with pytest.raises(ValidationError):
        FetcherConfig(
            max_connections=5,
            max_keepalive_connections=6,
        )


def test_unknown_configuration_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        FetcherConfig(unknown_option=True)  # type: ignore[call-arg]


def test_config_is_immutable() -> None:
    config = FetcherConfig()

    with pytest.raises(ValidationError):
        config.timeout = 20.0  # type: ignore[misc]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_non_finite_backoff_values_are_rejected(value: float) -> None:
    with pytest.raises(ValidationError):
        FetcherConfig(backoff_factor=value)


def test_zero_backoff_is_valid() -> None:
    config = FetcherConfig(backoff_factor=0, max_backoff=0)

    assert config.backoff_factor == 0
    assert config.max_backoff == 0


def test_invalid_log_level_is_rejected() -> None:
    with pytest.raises(ValidationError):
        FetcherConfig(log_level="TRACE")
