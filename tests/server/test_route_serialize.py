"""Route serialization must never expose credentials."""

from server_support.route_generator import _serialize


class _FakeProvider:
    def __init__(self):
        self.base_url = "https://api.deepseek.com"
        self.api_key = "sk-secret-value"
        self.model = "deepseek-chat"


def test_serialize_redacts_api_key_from_objects():
    data = _serialize(_FakeProvider())
    assert data["base_url"] == "https://api.deepseek.com"
    assert data["model"] == "deepseek-chat"
    assert data["api_key"] == "***"


def test_serialize_redacts_sensitive_dict_keys():
    data = _serialize(
        {
            "api_key": "sk-123",
            "access_token": "tok",
            "client_secret": "shh",
            "model": "deepseek-chat",
        }
    )
    assert data["api_key"] == "***"
    assert data["access_token"] == "***"
    assert data["client_secret"] == "***"
    assert data["model"] == "deepseek-chat"


def test_serialize_keeps_non_secret_token_counts():
    data = _serialize({"prompt_tokens": 10, "completion_tokens": 3})
    assert data == {"prompt_tokens": 10, "completion_tokens": 3}
