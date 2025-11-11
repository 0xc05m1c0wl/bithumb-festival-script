"""CLI 엔트리포인트."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any, Mapping

import httpx

from . import config, orders
from .types import HttpClient, Side, ensure_side


@dataclass(frozen=True)
class OrderPlan:
    market: str
    side: Side
    amount: float
    available: float
    currency_label: str
    dry_run: bool


@dataclass(frozen=True)
class CliOptions:
    market: str | None
    side: Side
    dotenv: str | None
    dry_run: bool


@dataclass(frozen=True)
class ExecutionConfig:
    market: str
    side: Side
    dry_run: bool


def _resolve_market(market: str | None, settings: config.ApiSettings) -> str:
    if market:
        return market
    if settings.default_market:
        return settings.default_market
    raise ValueError("--market 또는 BITTHUMB_DEFAULT_MARKET가 필요합니다.")


def _order_min_total(chance: Mapping[str, Any], side: Side) -> float | None:
    market = chance.get("market")
    if not isinstance(market, dict):
        return None
    info = market.get("bid" if side == "bid" else "ask")
    if not isinstance(info, dict):
        return None
    minimum = info.get("min_total") or info.get("min")
    if minimum in (None, ""):
        return None
    try:
        return float(minimum)
    except (TypeError, ValueError) as exc:
        raise ValueError("orders/chance 응답의 최소 주문 금액이 숫자가 아닙니다.") from exc


def _resolve_amount(guide_amount: float | None, fallback_amount: float | None) -> float:
    if guide_amount is not None:
        return guide_amount
    if fallback_amount is not None:
        return fallback_amount
    raise ValueError("orders/chance 응답 또는 BITTHUMB_FALLBACK_AMOUNT 중 최소 주문 금액이 필요합니다.")


def _available_balance(chance: Mapping[str, Any], side: Side) -> float:
    account_key = "bid_account" if side == "bid" else "ask_account"
    account = chance.get(account_key)
    if not isinstance(account, dict):
        raise ValueError("orders/chance 응답에서 계좌 정보를 찾을 수 없습니다.")
    available = account.get("available")
    if available in (None, ""):
        available = account.get("balance")
    if available in (None, ""):
        raise ValueError("orders/chance 응답에 사용 가능 잔액 정보가 없습니다.")
    try:
        return float(available)
    except (TypeError, ValueError) as exc:
        raise ValueError("orders/chance 응답의 사용 가능 금액이 숫자가 아닙니다.") from exc


def _resolve_currency_label(chance: Mapping[str, Any], side: Side, market: str) -> str:
    market_info = chance.get("market")
    currency_from_market: str | None = None
    if isinstance(market_info, dict):
        section = market_info.get("bid" if side == "bid" else "ask")
        if isinstance(section, dict):
            raw_currency = section.get("currency")
            if isinstance(raw_currency, str) and raw_currency:
                currency_from_market = raw_currency

    if side == "bid":
        return (chance.get("payment_currency") or currency_from_market or "KRW")
    return (
        chance.get("order_currency")
        or currency_from_market
        or market.split("-", 1)[-1]
    )


def _assert_sufficient_balance(required: float, available: float, currency: str) -> None:
    if available + 1e-9 < required:
        raise ValueError(
            f"경고: 최소 주문 금액 {required} {currency}보다 사용 가능 금액 {available} {currency}가 적습니다."
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="빗썸 API 이벤트 스크립트",
    )
    parser.add_argument("--market", help="거래 마켓 (예: KRW-BTC)")
    parser.add_argument("--side", choices=["bid", "ask"], default="bid", help="주문 방향")
    parser.add_argument("--dotenv", help="커스텀 .env 경로", default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 주문 대신 시뮬레이션으로 실행 (기본은 LIVE)",
    )
    return parser


def _parse_cli_options(argv: list[str] | None) -> tuple[argparse.ArgumentParser, CliOptions]:
    parser = _build_parser()
    namespace = parser.parse_args(argv)
    try:
        side = ensure_side(namespace.side)
    except ValueError as exc:
        parser.error(str(exc))
    return parser, CliOptions(
        market=namespace.market,
        side=side,
        dotenv=namespace.dotenv,
        dry_run=namespace.dry_run,
    )


def _print(label: str, payload: Any) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    print(f"\n[{label}]\n{text}")


def prepare_execution_config(options: CliOptions, settings: config.ApiSettings) -> ExecutionConfig:
    market = _resolve_market(options.market, settings)
    return ExecutionConfig(
        market=market,
        side=options.side,
        dry_run=options.dry_run,
    )


def _announce_execution(config: ExecutionConfig) -> None:
    print("주문 준비 중...")
    print(f"- 마켓: {config.market}")
    print(f"- 모드: {'DRY-RUN' if config.dry_run else 'LIVE'}")


def _summarize_plan(plan: OrderPlan, account_snapshot: Mapping[str, Any] | None) -> None:
    print(f"- 금액: {plan.amount} {plan.currency_label}")
    print(f"- 사용 가능: {plan.available} {plan.currency_label}")
    if account_snapshot is not None:
        _print("주문 가능 정보", account_snapshot)


def _fail(parser: argparse.ArgumentParser, exc: Exception) -> None:
    parser.error(str(exc))


def _handle_http_status_error(exc: httpx.HTTPStatusError) -> None:
    _print(
        "API 오류",
        {"status_code": exc.response.status_code, "body": exc.response.text},
    )
    sys.exit(1)

def build_order_plan(
    *,
    chance: Mapping[str, Any],
    side: Side,
    market: str,
    fallback_amount: float | None,
    dry_run: bool,
) -> OrderPlan:
    guide_amount = _order_min_total(chance, side)
    amount = _resolve_amount(guide_amount, fallback_amount)
    available = _available_balance(chance, side)
    currency_label = _resolve_currency_label(chance, side, market)
    _assert_sufficient_balance(amount, available, currency_label)
    return OrderPlan(
        market=market,
        side=side,
        amount=amount,
        available=available,
        currency_label=currency_label,
        dry_run=dry_run,
    )


def execute_trade_cycle(
    *,
    client: HttpClient,
    settings: config.ApiSettings,
    config: ExecutionConfig,
) -> tuple[OrderPlan, Mapping[str, Any] | None, Mapping[str, Any]]:
    chance = orders.fetch_order_chance(
        client=client,
        settings=settings,
        market=config.market,
    )
    plan = build_order_plan(
        chance=chance,
        side=config.side,
        market=config.market,
        fallback_amount=settings.fallback_amount,
        dry_run=config.dry_run,
    )
    result = orders.place_market_order(
        client=client,
        settings=settings,
        market=plan.market,
        amount=plan.amount,
        side=plan.side,
        dry_run=plan.dry_run,
    )
    account_snapshot = chance.get("bid_account") if plan.side == "bid" else chance.get("ask_account")
    return plan, account_snapshot, result


def main(argv: list[str] | None = None) -> None:
    parser, options = _parse_cli_options(argv)
    try:
        settings = config.load_settings(options.dotenv)
        exec_config = prepare_execution_config(options, settings)
    except ValueError as exc:
        _fail(parser, exc)
        return

    _announce_execution(exec_config)

    try:
        with httpx.Client(timeout=orders.DEFAULT_TIMEOUT) as client:
            plan, account_snapshot, result = execute_trade_cycle(
                client=client,
                settings=settings,
                config=exec_config,
            )
    except httpx.HTTPStatusError as exc:
        _handle_http_status_error(exc)
    except httpx.HTTPError as exc:
        _fail(parser, RuntimeError(f"네트워크 오류: {exc}"))
    except ValueError as exc:
        _fail(parser, exc)
    else:
        _summarize_plan(plan, account_snapshot)
        _print("주문 결과", result)


if __name__ == "__main__":  # pragma: no cover
    main()
