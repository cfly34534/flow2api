import unittest
from unittest.mock import patch

from src.core.config import config
from src.services.flow_client import FlowClient


class _DummyProxyManager:
    async def get_proxy_url(self):
        return None


class _FakeResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


class _FakeSession:
    def __init__(self, responses):
        self._responses = responses
        self._index = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        response = self._responses[self._index]
        self._index += 1
        return response


class ThirdPartyCaptchaTests(unittest.IsolatedAsyncioTestCase):
    async def test_yescaptcha_accepts_token_field_without_blocking_sleep(self):
        client = FlowClient(_DummyProxyManager())
        config.set_yescaptcha_api_key("dummy")
        config.set_yescaptcha_base_url("https://api.yescaptcha.com")

        fake_responses = [
            _FakeResponse({"taskId": 123}),
            _FakeResponse({"status": "processing"}),
            _FakeResponse({"status": "ready", "solution": {"token": "captcha-token"}}),
        ]

        with patch("src.services.flow_client.AsyncSession", return_value=_FakeSession(fake_responses)):
            with patch("src.services.flow_client.time.sleep", side_effect=AssertionError("time.sleep should not be called")):
                token = await client._get_api_captcha_token("yescaptcha", "project-id")

        self.assertEqual(token, "captcha-token")


if __name__ == "__main__":
    unittest.main()
