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
    async def test_yescaptcha_token_extraction_with_async_polling(self):
        client = FlowClient(_DummyProxyManager())
        config.set_yescaptcha_api_key("dummy")
        config.set_yescaptcha_base_url("https://api.yescaptcha.com")

        fake_responses = [
            _FakeResponse({"taskId": 123}),
            _FakeResponse({"status": "processing"}),
            _FakeResponse({"status": "ready", "solution": {"token": "captcha-token"}}),
        ]

        with patch("src.services.flow_client.AsyncSession", return_value=_FakeSession(fake_responses)):
            with patch("src.services.flow_client.asyncio.sleep") as mock_sleep:
                token = await client._get_api_captcha_token("yescaptcha", "project-id")

        self.assertEqual(token, "captcha-token")
        mock_sleep.assert_awaited_once_with(3)

    async def test_yescaptcha_create_task_uses_enterprise_mode(self):
        client = FlowClient(_DummyProxyManager())
        config.set_yescaptcha_api_key("dummy")
        config.set_yescaptcha_base_url("https://api.yescaptcha.com")

        class _CaptureSession:
            def __init__(self):
                self.calls = []

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, url, *args, **kwargs):
                self.calls.append((url, kwargs.get("json", {})))
                if url.endswith("/createTask"):
                    return _FakeResponse({"taskId": 123})
                return _FakeResponse({"status": "ready", "solution": {"token": "captcha-token"}})

        session = _CaptureSession()
        with patch("src.services.flow_client.AsyncSession", return_value=session):
            token = await client._get_api_captcha_token("yescaptcha", "project-id", "IMAGE_GENERATION")

        self.assertEqual(token, "captcha-token")
        self.assertTrue(session.calls[0][1]["task"]["isEnterprise"])


if __name__ == "__main__":
    unittest.main()
