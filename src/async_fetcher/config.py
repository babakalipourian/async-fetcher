import math
from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class FetcherConfig(BaseModel):
    """Validated, immutable configuration for the async fetcher."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_default=True,
    )

    timeout: float = Field(default=10.0, gt=0)
    max_concurrency: int = Field(default=20, ge=1)
    max_connections: int = Field(default=20, ge=1)
    max_keepalive_connections: int = Field(default=10, ge=0)
    max_retries: int = Field(default=3, ge=0, le=10)
    backoff_factor: float = Field(default=0.5, ge=0)
    max_backoff: float = Field(default=30.0, ge=0)
    follow_redirects: bool = True
    raise_on_http_error: bool = False
    log_level: Literal[
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ] = "INFO"

    @field_validator("timeout", "backoff_factor", "max_backoff")
    @classmethod
    def validate_finite_values(cls, value: float) -> float:
        """Reject NaN and infinite numeric values."""
        if not math.isfinite(value):
            raise ValueError("Value must be finite.")

        return value

    @model_validator(mode="after")
    def validate_connection_limits(self) -> Self:
        """Ensure connection pool limits are consistent."""
        if self.max_keepalive_connections > self.max_connections:
            raise ValueError("max_keepalive_connections cannot exceed max_connections.")

        return self
