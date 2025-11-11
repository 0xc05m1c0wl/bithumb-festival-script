"""빗썸 API 인증 유틸리티."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
import hashlib
import time
from uuid import uuid4
from urllib.parse import quote_plus

import jwt


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def serialize_query(params: Mapping[str, Any] | None) -> str:
    if not params:
        return ""

    parts: list[str] = []

    # HTTP 요청과 동일한 순서를 유지해야 하므로 입력 순서를 그대로 사용한다.
    for key, value in params.items():
        if value is None:
            continue

        if _is_sequence(value):
            seq = [item for item in value if item is not None]
            if not seq:
                continue
            for item in seq:
                parts.append(
                    f"{quote_plus(f'{key}[]', safe='-_.~[]')}={quote_plus(str(item), safe='-_.~[]')}"
                )
            continue

        parts.append(f"{quote_plus(str(key), safe='-_.~[]')}={quote_plus(str(value), safe='-_.~[]')}")

    return "&".join(parts)


def hash_query_string(query: str, algorithm: str = "SHA512") -> str:
    if not query:
        return ""
    hasher = hashlib.new(algorithm)
    hasher.update(query.encode("utf-8"))
    return hasher.hexdigest()


def generate_jwt(
    *,
    access_key: str,
    secret_key: str,
    params: Mapping[str, Any] | None,
    nonce: str | None = None,
    timestamp: int | None = None,
    algorithm: str = "HS256",
    query_hash_algorithm: str = "SHA512",
) -> str:
    query = serialize_query(params)
    payload: dict[str, Any] = {
        "access_key": access_key,
        "nonce": nonce or str(uuid4()),
        "timestamp": timestamp or int(time.time() * 1000),
    }

    if query:
        payload["query_hash"] = hash_query_string(query, algorithm=query_hash_algorithm)
        payload["query_hash_alg"] = query_hash_algorithm

    return jwt.encode(payload, secret_key, algorithm=algorithm)
