import json
import logging

import pytest

from async_fetcher import FetcherConfig
from async_fetcher._logging import configure_logging, get_logger


def test_configure_logging_sets_log_level() -> None:
    configure_logging(FetcherConfig(log_level="WARNING"))

    assert logging.getLogger().level == logging.WARNING


def test_configure_logging_uses_json_renderer(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging(FetcherConfig())

    logger = get_logger("test_component")
    logger.info("test_event", action="test")

    output = capsys.readouterr().out.strip()
    event = json.loads(output)

    assert event["event"] == "test_event"
    assert event["component"] == "test_component"
    assert event["action"] == "test"
    assert event["level"] == "info"
    assert "timestamp" in event


def test_get_logger_binds_component_name() -> None:
    configure_logging(FetcherConfig())

    logger = get_logger("http_transport")

    assert logger is not None
    assert logger._context["component"] == "http_transport"
