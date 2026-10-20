import logging

import structlog

from async_fetcher.config import FetcherConfig


def configure_logging(config: FetcherConfig) -> None:
    """Configure structured logging for async-fetcher."""

    level = getattr(logging, config.log_level)

    logging.basicConfig(
        level=level,
        format="%(message)s",
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a structured logger bound to a component name."""

    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name).bind(
        component=name
    )
    return logger
