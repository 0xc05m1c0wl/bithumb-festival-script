from types import SimpleNamespace

import pytest

from bitthumb_cli import cli
from bitthumb_cli.config import ApiSettings


@pytest.fixture
def settings():
    return ApiSettings(
        base_url="https://api.test.com",
        access_key="ak",
        secret_key="sk",
        default_market="KRW-XRP",
    )


@pytest.fixture
def chance():
    return {
        "market": {
            "bid": {"currency": "KRW", "min_total": "5500"},
            "ask": {"currency": "BTC", "min_total": "0.001"},
        },
        "bid_account": {"available": "7500.5"},
        "ask_account": {"available": "0.015"},
    }


def test_resolve_market_prefers_cli(settings):
    assert cli._resolve_market("KRW-BTC", settings) == "KRW-BTC"


def test_resolve_market_falls_back_to_default(settings):
    assert cli._resolve_market(None, settings) == "KRW-XRP"


def test_resolve_market_raises_when_missing(settings):
    empty = ApiSettings(
        base_url=settings.base_url,
        access_key=settings.access_key,
        secret_key=settings.secret_key,
    )
    with pytest.raises(ValueError):
        cli._resolve_market(None, empty)


def test_order_min_total_reads_bid_section(chance):
    assert cli._order_min_total(chance, "bid") == pytest.approx(5500.0)


def test_order_min_total_reads_ask_section(chance):
    assert cli._order_min_total(chance, "ask") == pytest.approx(0.001)


def test_resolve_amount_prefers_guide():
    assert cli._resolve_amount(5500, 6100) == 5500


def test_resolve_amount_falls_back_to_env():
    assert cli._resolve_amount(None, 6400) == 6400


def test_resolve_amount_raises_when_missing():
    with pytest.raises(ValueError):
        cli._resolve_amount(None, None)


def test_available_balance_reads_side_specific_account(chance):
    assert cli._available_balance(chance, "bid") == pytest.approx(7500.5)
    assert cli._available_balance(chance, "ask") == pytest.approx(0.015)


def test_available_balance_errors_when_missing():
    with pytest.raises(ValueError):
        cli._available_balance({}, "bid")


def test_assert_sufficient_balance_passes_when_enough():
    cli._assert_sufficient_balance(5000, 8000, "KRW")


def test_assert_sufficient_balance_raises_when_short():
    with pytest.raises(ValueError):
        cli._assert_sufficient_balance(6000, 5500, "KRW")


def test_parser_no_longer_accepts_amount():
    parser = cli._build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--amount", "6000"])


def test_parse_cli_options_defaults_to_live_mode():
    _, options = cli._parse_cli_options([])

    assert options.dry_run is False


def test_parse_cli_options_accepts_dry_run_flag():
    _, options = cli._parse_cli_options(["--dry-run"])

    assert options.dry_run is True


def test_main_handles_ask_side(mocker, settings, chance):
    parser = mocker.Mock()
    parser.parse_args.return_value = SimpleNamespace(
        market=None,
        side="ask",
        dotenv=None,
        dry_run=False,
    )
    mocker.patch("bitthumb_cli.cli._build_parser", return_value=parser)

    mocker.patch("bitthumb_cli.cli.config.load_settings", return_value=settings)
    mocker.patch("bitthumb_cli.cli._resolve_market", return_value="KRW-XRP")

    client_ctx = mocker.MagicMock()
    mocker.patch("bitthumb_cli.cli.httpx.Client", return_value=client_ctx)
    fake_client = mocker.Mock()
    client_ctx.__enter__.return_value = fake_client

    plan = cli.OrderPlan(
        market="KRW-XRP",
        side="ask",
        amount=0.001,
        available=0.02,
        currency_label="BTC",
        dry_run=False,
    )

    exec_mock = mocker.patch(
        "bitthumb_cli.cli.execute_trade_cycle",
        return_value=(plan, chance["ask_account"], {"ok": True}),
    )

    cli.main([])

    exec_mock.assert_called_once()
    kwargs = exec_mock.call_args.kwargs
    assert kwargs["client"] is fake_client
    assert kwargs["config"].side == "ask"
    assert kwargs["config"].dry_run is False


def test_main_converts_value_error_to_cli_error(mocker, settings):
    parser = mocker.Mock()
    parser.parse_args.return_value = SimpleNamespace(
        market=None,
        side="bid",
        dotenv=None,
        dry_run=True,
    )
    parser.error.side_effect = SystemExit(2)
    mocker.patch("bitthumb_cli.cli._build_parser", return_value=parser)

    mocker.patch("bitthumb_cli.cli.config.load_settings", return_value=settings)
    mocker.patch("bitthumb_cli.cli._resolve_market", return_value="KRW-BTC")

    mocker.patch(
        "bitthumb_cli.cli.execute_trade_cycle",
        side_effect=ValueError("bad-data"),
    )

    client_ctx = mocker.MagicMock()
    client_ctx.__enter__.return_value = mocker.Mock()
    mocker.patch("bitthumb_cli.cli.httpx.Client", return_value=client_ctx)

    with pytest.raises(SystemExit):
        cli.main([])

    parser.error.assert_called_once_with("bad-data")


def test_build_order_plan_returns_expected_values(settings, chance):
    plan = cli.build_order_plan(
        chance=chance,
        side="bid",
        market="KRW-BTC",
        fallback_amount=6400,
        dry_run=True,
    )

    assert plan.market == "KRW-BTC"
    assert plan.side == "bid"
    assert plan.amount == pytest.approx(5500.0)
    assert plan.available == pytest.approx(7500.5)
    assert plan.currency_label == "KRW"
    assert plan.dry_run is True


def test_build_order_plan_handles_ask_side_currency(settings, chance):
    plan = cli.build_order_plan(
        chance=chance,
        side="ask",
        market="KRW-XRP",
        fallback_amount=6400,
        dry_run=False,
    )

    assert plan.currency_label == "BTC"
    assert plan.amount == pytest.approx(0.001)
    assert plan.dry_run is False


def test_build_order_plan_validates_balance(settings, chance):
    chance["bid_account"]["available"] = "1000"

    with pytest.raises(ValueError):
        cli.build_order_plan(
            chance=chance,
            side="bid",
            market="KRW-BTC",
            fallback_amount=None,
            dry_run=True,
        )


def test_prepare_execution_config_uses_defaults(settings):
    options = cli.CliOptions(market=None, side="ask", dotenv=None, dry_run=True)

    config = cli.prepare_execution_config(options, settings)

    assert config.market == "KRW-XRP"
    assert config.side == "ask"
    assert config.dry_run is True


def test_execute_trade_cycle_returns_plan_and_snapshots(mocker, settings, chance):
    client = mocker.Mock()
    mocker.patch("bitthumb_cli.orders.fetch_order_chance", return_value=chance)
    mocker.patch("bitthumb_cli.orders.place_market_order", return_value={"uuid": "placed"})

    config = cli.ExecutionConfig(market="KRW-BTC", side="bid", dry_run=True)

    plan, account_snapshot, result = cli.execute_trade_cycle(
        client=client,
        settings=settings,
        config=config,
    )

    assert plan.market == "KRW-BTC"
    assert plan.side == "bid"
    assert account_snapshot == chance["bid_account"]
    assert result == {"uuid": "placed"}
