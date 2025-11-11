import pytest

from bitthumb_cli import config, orders


@pytest.fixture
def settings():
    return config.ApiSettings(
        base_url="https://api.test.com",
        access_key="ak",
        secret_key="sk",
    )


def test_fetch_order_chance_calls_endpoint(mocker, settings):
    token = "signed-token"
    mocker.patch("bitthumb_cli.auth.generate_jwt", return_value=token)

    mock_response = mocker.Mock()
    mock_response.json.return_value = {"status": "0000"}
    mock_response.raise_for_status.return_value = None

    client = mocker.Mock()
    client.get.return_value = mock_response

    result = orders.fetch_order_chance(client=client, settings=settings, market="KRW-BTC")

    client.get.assert_called_once()
    args, kwargs = client.get.call_args
    assert args[0] == "https://api.test.com/v1/orders/chance?market=KRW-BTC"
    assert kwargs["headers"] == {"Authorization": "Bearer signed-token"}
    assert "params" not in kwargs

    assert result == {"status": "0000"}


def test_place_market_order_posts_json_for_bid(mocker, settings):
    mocker.patch("bitthumb_cli.auth.generate_jwt", return_value="token")

    mock_response = mocker.Mock()
    mock_response.json.return_value = {"uuid": "order"}
    mock_response.raise_for_status.return_value = None

    client = mocker.Mock()
    client.post.return_value = mock_response

    result = orders.place_market_order(
        client=client,
        settings=settings,
        market="KRW-BTC",
        amount=6000,
        side="bid",
        dry_run=False,
    )

    payload = {
        "market": "KRW-BTC",
        "side": "bid",
        "ord_type": "price",
        "price": "6000",
    }

    client.post.assert_called_once_with(
        "https://api.test.com/v1/orders",
        json=payload,
        headers={"Authorization": "Bearer token"},
        timeout=5,
    )
    assert result == {"uuid": "order"}


def test_place_market_order_builds_payload_for_ask(mocker, settings):
    mocker.patch("bitthumb_cli.auth.generate_jwt", return_value="token")

    mock_response = mocker.Mock()
    mock_response.json.return_value = {"uuid": "ask-order"}
    mock_response.raise_for_status.return_value = None

    client = mocker.Mock()
    client.post.return_value = mock_response

    result = orders.place_market_order(
        client=client,
        settings=settings,
        market="KRW-XRP",
        amount=0.015,
        side="ask",
        dry_run=False,
    )

    payload = {
        "market": "KRW-XRP",
        "side": "ask",
        "ord_type": "market",
        "volume": "0.015",
    }

    client.post.assert_called_once_with(
        "https://api.test.com/v1/orders",
        json=payload,
        headers={"Authorization": "Bearer token"},
        timeout=5,
    )
    assert result == {"uuid": "ask-order"}


def test_place_market_order_skips_http_when_dry_run(mocker, settings):
    client = mocker.Mock()

    summary = orders.place_market_order(
        client=client,
        settings=settings,
        market="KRW-BTC",
        amount=7000,
        side="bid",
        dry_run=True,
    )

    client.post.assert_not_called()
    assert summary["market"] == "KRW-BTC"
    assert summary["price"] == "7000"


def test_place_market_order_skips_http_for_ask_dry_run(mocker, settings):
    client = mocker.Mock()

    summary = orders.place_market_order(
        client=client,
        settings=settings,
        market="KRW-XRP",
        amount=0.02,
        side="ask",
        dry_run=True,
    )

    client.post.assert_not_called()
    assert summary["volume"] == "0.02"


def test_place_market_order_rejects_invalid_side(mocker, settings):
    client = mocker.Mock()

    with pytest.raises(ValueError):
        orders.place_market_order(
            client=client,
            settings=settings,
            market="KRW-XRP",
            amount=0.02,
            side="sell",
            dry_run=True,
        )
