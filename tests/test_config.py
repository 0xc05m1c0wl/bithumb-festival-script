import os

import pytest

from bitthumb_cli import config


def test_load_settings_reads_environment(monkeypatch, tmp_path):
    monkeypatch.delenv("BITTHUMB_ACCESS_KEY", raising=False)
    monkeypatch.delenv("BITTHUMB_SECRET_KEY", raising=False)
    monkeypatch.delenv("BITTHUMB_FALLBACK_AMOUNT", raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "BITTHUMB_BASE_URL=https://api.test.com/",
                "BITTHUMB_ACCESS_KEY=foo",
                "BITTHUMB_SECRET_KEY=bar",
                "BITTHUMB_DEFAULT_MARKET=KRW-XRP",
                "BITTHUMB_FALLBACK_AMOUNT=6400",
            ]
        )
    )

    settings = config.load_settings(env_file)

    assert settings.base_url == "https://api.test.com"
    assert settings.access_key == "foo"
    assert settings.secret_key == "bar"
    assert settings.default_market == "KRW-XRP"
    assert settings.fallback_amount == 6400


def test_load_settings_requires_keys(monkeypatch, tmp_path):
    monkeypatch.delenv("BITTHUMB_ACCESS_KEY", raising=False)
    monkeypatch.delenv("BITTHUMB_SECRET_KEY", raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text("BITTHUMB_BASE_URL=https://api.test.com")

    with pytest.raises(ValueError):
        config.load_settings(env_file)


def test_coerce_fallback_validates(monkeypatch, tmp_path):
    monkeypatch.delenv("BITTHUMB_ACCESS_KEY", raising=False)
    monkeypatch.delenv("BITTHUMB_SECRET_KEY", raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "BITTHUMB_ACCESS_KEY=foo",
                "BITTHUMB_SECRET_KEY=bar",
                "BITTHUMB_FALLBACK_AMOUNT=not-a-number",
            ]
        )
    )

    with pytest.raises(ValueError):
        config.load_settings(env_file)
