"""공유 타입 정의."""

from __future__ import annotations

from typing import Any, Literal, Mapping, Protocol, cast


Side = Literal["bid", "ask"]


class SupportsJsonResponse(Protocol):
    def json(self) -> dict[str, Any]:
        ...

    def raise_for_status(self) -> None:
        ...


class HttpClient(Protocol):
    def get(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: int | float | None = None,
    ) -> SupportsJsonResponse:
        ...

    def post(
        self,
        url: str,
        *,
        json: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: int | float | None = None,
    ) -> SupportsJsonResponse:
        ...


def ensure_side(value: str) -> Side:
    if value not in ("bid", "ask"):
        raise ValueError("side는 bid 또는 ask 여야 합니다.")
    return cast(Side, value)
