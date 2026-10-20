from collections.abc import Mapping
from types import MappingProxyType

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)


class FetchRequest(BaseModel):
    """Validated, immutable HTTP fetch request."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_default=True,
    )

    url: HttpUrl
    method: str = "GET"
    headers: Mapping[str, str] = Field(default_factory=dict)
    params: Mapping[str, str | int | float | bool] = Field(default_factory=dict)
    timeout: float | None = Field(default=None, gt=0)

    @field_validator("method")
    @classmethod
    def validate_method(cls, value: str) -> str:
        normalized = value.strip().upper()

        if not normalized:
            raise ValueError("HTTP method cannot be empty.")

        if any(char.isspace() for char in normalized):
            raise ValueError("HTTP method cannot contain whitespace.")

        return normalized

    @field_validator("headers")
    @classmethod
    def validate_headers(
        cls,
        value: Mapping[str, str],
    ) -> Mapping[str, str]:
        validated: dict[str, str] = {}

        for name, content in value.items():
            if not name or not name.isascii():
                raise ValueError("Header names must be non-empty ASCII.")

            if any(char in name for char in '():<>@,;\\"/[]?={} \t'):
                raise ValueError(f"Invalid HTTP header name: {name!r}")

            if any(ord(char) < 32 and char != "\t" for char in content):
                raise ValueError("Header values contain invalid characters.")

            if "\r" in content or "\n" in content:
                raise ValueError("Header values cannot contain newlines.")

            validated[name] = content

        return MappingProxyType(validated)

    @field_validator("params")
    @classmethod
    def validate_params(
        cls,
        value: Mapping[str, str | int | float | bool],
    ) -> Mapping[str, str | int | float | bool]:
        validated: dict[str, str | int | float | bool] = {}

        for key, item in value.items():
            if not key:
                raise ValueError("Query parameter names cannot be empty.")

            if isinstance(item, float) and (
                item != item or item in (float("inf"), float("-inf"))
            ):
                raise ValueError("Query parameters must contain finite floats.")

            validated[key] = item

        return MappingProxyType(validated)

    @model_validator(mode="after")
    def validate_url_scheme(self) -> "FetchRequest":
        if self.url.scheme not in {"http", "https"}:
            raise ValueError("Only HTTP and HTTPS URLs are supported.")

        return self
