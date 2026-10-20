from collections.abc import Mapping
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class FetchResponse(BaseModel):
    """Validated HTTP response returned by the fetcher."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_default=True,
    )

    url: HttpUrl
    status_code: int = Field(ge=100, le=599)
    headers: Mapping[str, str] = Field(default_factory=dict)
    body: bytes
    elapsed_seconds: float = Field(ge=0)
    attempts: int = Field(ge=1)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("elapsed_seconds")
    @classmethod
    def validate_elapsed_seconds(cls, value: float) -> float:
        import math

        if not math.isfinite(value):
            raise ValueError("elapsed_seconds must be finite.")

        return value

    @field_validator("headers")
    @classmethod
    def validate_headers(
        cls,
        value: Mapping[str, str],
    ) -> Mapping[str, str]:
        from types import MappingProxyType

        return MappingProxyType(dict(value))

    @field_validator("fetched_at")
    @classmethod
    def normalize_fetched_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("fetched_at must be timezone-aware.")

        return value.astimezone(UTC)
