import json
import unittest
from unittest.mock import patch, MagicMock
import io
from urllib.error import HTTPError
from server import llm


class TransportTests(unittest.TestCase):
    def test_request_matches_working_cli_encoding(self):
        response = MagicMock()
        response.__enter__.return_value = io.BytesIO(json.dumps({"choices": [{
            "finish_reason": "stop", "message": {"content": "{}"}}]}).encode())
        with patch.object(llm, "require_api_key", return_value="test-only"), \
             patch.object(llm, "urlopen", return_value=response) as send:
            self.assertEqual(llm.chat([{"role": "user", "content": "Catan — café"}]), "{}")
        request = send.call_args.args[0]
        payload = request.data
        self.assertTrue(payload.isascii())
        self.assertEqual(json.loads(payload)["messages"][0]["content"], "Catan — café")
        self.assertEqual(json.loads(payload)["reasoning_effort"], "low")
        self.assertTrue(request.full_url.endswith("/chat/completions"))
        self.assertEqual(request.get_header("Authorization"), "Bearer test-only")

    def test_rate_limit_is_reported_without_retry(self):
        error = HTTPError("https://example.invalid", 429, "limited",
                          {"Retry-After": "60"}, io.BytesIO(b"limited"))
        with patch.object(llm, "require_api_key", return_value="test-only"), \
             patch.object(llm, "urlopen", side_effect=error) as send:
            with self.assertRaisesRegex(llm.LLMError, "Retry-After=60"):
                llm.chat([])
            self.assertEqual(send.call_count, 1)


if __name__ == "__main__":
    unittest.main()
