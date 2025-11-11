"""주문 관련 유틸."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, TypedDict

from . import auth
from .config import ApiSettings
from .types import HttpClient, Side, ensure_side

DEFAULT_TIMEOUT = 5


class OrderPayload(TypedDict, total=False):
    market: str
    side: Side
    ord_type: str
    price: str
    volume: str


def _format_decimal(value: float | int | str) -> str:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:  # pragma: no cover
        raise ValueError("주문 금액이 숫자가 아닙니다.") from exc

    if number <= 0:
        raise ValueError("주문 금액은 0보다 커야 합니다.")

    normalized = number.normalize()
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _headers(settings: ApiSettings, params: Mapping[str, Any] | None) -> dict[str, str]:
    token = auth.generate_jwt(
        access_key=settings.access_key,
        secret_key=settings.secret_key,
        params=params,
    )
    return {"Authorization": f"Bearer {token}"}


def _build_url(base_url: str, path: str, params: Mapping[str, Any] | None) -> str:
    query = auth.serialize_query(params)
    if not query:
        return f"{base_url}{path}"
    return f"{base_url}{path}?{query}"


def fetch_order_chance(
    *,
    client: HttpClient,
    settings: ApiSettings,
    market: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    params = {"market": market}
    response = client.get(
        _build_url(settings.base_url, "/v1/orders/chance", params),
        headers=_headers(settings, params),
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def place_market_order(
    *,
    client: HttpClient,
    settings: ApiSettings,
    market: str,
    amount: float,
    side: Side | str,
    dry_run: bool,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    side_value = ensure_side(side)

    payload: OrderPayload = {
        "market": market,
        "side": side_value,
    }
    if side_value == "bid":
        payload["ord_type"] = "price"
        payload["price"] = _format_decimal(amount)
    else:
        payload["ord_type"] = "market"
        payload["volume"] = _format_decimal(amount)

    if dry_run:
        return {"dry_run": True, **payload}

    response = client.post(
        f"{settings.base_url}/v1/orders",
        json=payload,
        headers=_headers(settings, payload),
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()
