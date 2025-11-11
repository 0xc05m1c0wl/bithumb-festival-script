import jwt
import pytest

from bitthumb_cli import auth


def test_serialize_query_preserves_insertion_order():
    params = {
        "market": "KRW-BTC",
        "uuids": ["C1", "C2"],
        "limit": 50,
    }

    encoded = auth.serialize_query(params)

    assert encoded == "market=KRW-BTC&uuids[]=C1&uuids[]=C2&limit=50"


def test_generate_jwt_contains_expected_payload():
    access_key = "test-access"
    secret_key = "secret"
    params = {"market": "KRW-BTC"}

    token = auth.generate_jwt(
        access_key=access_key,
        secret_key=secret_key,
        params=params,
        nonce="fixed-nonce",
        timestamp=1700000000000,
    )

    decoded = jwt.decode(token, secret_key, algorithms=["HS256"])

    assert decoded["access_key"] == access_key
    assert decoded["nonce"] == "fixed-nonce"
    assert decoded["timestamp"] == 1700000000000
    assert decoded["query_hash_alg"] == "SHA512"
    assert decoded["query_hash"] == auth.hash_query_string("market=KRW-BTC")


def test_generate_jwt_respects_query_hash_algorithm():
    access_key = "test-access"
    secret_key = "secret"
    params = {"market": "KRW-BTC"}

    token = auth.generate_jwt(
        access_key=access_key,
        secret_key=secret_key,
        params=params,
        nonce="fixed-nonce",
        timestamp=1700000000000,
        query_hash_algorithm="MD5",
    )

    decoded = jwt.decode(token, secret_key, algorithms=["HS256"])

    assert decoded["query_hash_alg"] == "MD5"
    assert decoded["query_hash"] == auth.hash_query_string("market=KRW-BTC", algorithm="MD5")


@pytest.mark.parametrize("params,expected", [
    ({}, ""),
    ({"market": "KRW-BTC"}, "market=KRW-BTC"),
    ({"uuids": []}, ""),
])
def test_serialize_query_edge_cases(params, expected):
    assert auth.serialize_query(params) == expected


def test_serialize_query_handles_mixed_type_keys_without_reordering():
    params = {2: "b", "1": "a"}

    assert auth.serialize_query(params) == "2=b&1=a"


def test_serialize_query_preserves_safe_characters_in_sequence_keys():
    params = {"field-name": ["value~1"]}

    assert auth.serialize_query(params) == "field-name[]=value~1"
