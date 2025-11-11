"""환경 변수 기반 설정 로더."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from dotenv import load_dotenv


@dataclass(frozen=True)
class ApiSettings:
    base_url: str
    access_key: str
    secret_key: str
    default_market: str | None = None
    fallback_amount: float | None = None


def _coerce_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError as exc:  # pragma: no cover - 입력 검증
        raise ValueError("BITTHUMB_FALLBACK_AMOUNT 값이 숫자가 아닙니다.") from exc


def load_settings(dotenv_path: str | os.PathLike[str] | None = None) -> ApiSettings:
    if dotenv_path:
        load_dotenv(dotenv_path, override=True)
    else:
        default_dotenv = Path.cwd() / ".env"
        if default_dotenv.exists():
            load_dotenv(default_dotenv)

    base_url = os.getenv("BITTHUMB_BASE_URL", "https://api.bithumb.com").rstrip("/")
    access_key = os.getenv("BITTHUMB_ACCESS_KEY")
    secret_key = os.getenv("BITTHUMB_SECRET_KEY")

    if not access_key or not secret_key:
        raise ValueError("BITTHUMB_ACCESS_KEY/SECRET_KEY 환경 변수가 필요합니다.")

    return ApiSettings(
        base_url=base_url,
        access_key=access_key,
        secret_key=secret_key,
        default_market=os.getenv("BITTHUMB_DEFAULT_MARKET"),
        fallback_amount=_coerce_float(os.getenv("BITTHUMB_FALLBACK_AMOUNT")),
    )
