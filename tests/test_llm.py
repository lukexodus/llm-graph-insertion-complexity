"""
test_llm.py — INFRA-006 Unit Tests
==================================
Tests for LLMResponse, LLMSnapshot, MeteredLLMClient, DeepSeekClient, and FakeLLMClient.
"""

from __future__ import annotations

import json
import pytest
import httpx

from graph_insertion.llm import (
    DeepSeekClient,
    FakeLLMClient,
    LLMClient,
    LLMResponse,
    LLMSnapshot,
    LLMTransportError,
    MeteredLLMClient,
)


class TestLLMDataStructures:
    """Test LLMResponse, LLMSnapshot, and snapshot subtraction."""

    def test_llm_response_frozen(self):
        resp = LLMResponse(
            text="NONE",
            input_tokens=10,
            output_tokens=2,
            reasoning_tokens=0,
            cache_hit_tokens=5,
            cache_miss_tokens=5,
            latency_s=0.05,
            model_id="deepseek-v4-flash",
            attempts=1,
            retry_wait_s=0.0,
        )
        assert resp.text == "NONE"
        assert resp.latency_s == 0.05
        with pytest.raises(AttributeError):
            resp.text = "MUTATE"  # type: ignore[misc]

    def test_llm_snapshot_subtraction(self):
        s1 = LLMSnapshot(
            calls=2,
            attempts=3,
            retries=1,
            parse_failures=1,
            latency_s=0.20,
            retry_wait_s=1.0,
            input_tokens=100,
            output_tokens=20,
            reasoning_tokens=0,
            cache_hit_tokens=40,
            cache_miss_tokens=60,
            failed_parses=("junk1",),
        )
        s2 = LLMSnapshot(
            calls=5,
            attempts=7,
            retries=2,
            parse_failures=3,
            latency_s=0.55,
            retry_wait_s=3.0,
            input_tokens=260,
            output_tokens=55,
            reasoning_tokens=5,
            cache_hit_tokens=110,
            cache_miss_tokens=150,
            failed_parses=("junk1", "junk2", "junk3"),
        )
        delta = s2 - s1
        assert delta.calls == 3
        assert delta.attempts == 4
        assert delta.retries == 1
        assert delta.parse_failures == 2
        assert pytest.approx(delta.latency_s) == 0.35
        assert pytest.approx(delta.retry_wait_s) == 2.0
        assert delta.input_tokens == 160
        assert delta.output_tokens == 35
        assert delta.reasoning_tokens == 5
        assert delta.cache_hit_tokens == 70
        assert delta.cache_miss_tokens == 90
        assert delta.failed_parses == ("junk2", "junk3")

    def test_llm_snapshot_subtraction_type_error(self):
        s = LLMSnapshot(
            calls=1, attempts=1, retries=0, parse_failures=0,
            latency_s=0.1, retry_wait_s=0.0, input_tokens=10,
            output_tokens=2, reasoning_tokens=0, cache_hit_tokens=0, cache_miss_tokens=10
        )
        with pytest.raises(TypeError):
            _ = s - 42  # type: ignore[operator]


class TestMeteredLLMClient:
    """Test MeteredLLMClient tracking, snapshots, and resets."""

    def test_metered_client_accounting_and_reset(self):
        fake = FakeLLMClient(
            responses="NONE",
            latency_s=0.05,
            input_tokens=20,
            output_tokens=3,
            cache_hit_tokens=5,
            cache_miss_tokens=15,
        )
        meter = MeteredLLMClient(fake)
        assert isinstance(meter, LLMClient)

        resp1 = meter.complete("sys", "usr1")
        assert resp1.text == "NONE"
        assert meter.calls == 1
        assert meter.attempts == 1
        assert meter.retries == 0
        assert pytest.approx(meter.cumulative_latency_s) == 0.05
        assert meter.input_tokens == 20
        assert meter.output_tokens == 3

        resp2 = meter.complete("sys", "usr2")
        assert meter.calls == 2
        assert meter.attempts == 2
        assert pytest.approx(meter.cumulative_latency_s) == 0.10

        meter.record_parse_failure("invalid_token_response")
        assert meter.parse_failures == 1
        assert meter.failed_parses == ["invalid_token_response"]

        snap = meter.snapshot()
        assert snap.calls == 2
        assert snap.parse_failures == 1
        assert snap.failed_parses == ("invalid_token_response",)

        meter.reset()
        assert meter.calls == 0
        assert meter.parse_failures == 0
        assert meter.failed_parses == []
        assert meter.cumulative_latency_s == 0.0


class TestDeepSeekClient:
    """Test DeepSeekClient with mocked transport for retries, timing, and errors."""

    def test_missing_api_key_raises_value_error(self, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        with pytest.raises(ValueError, match="DEEPSEEK_API_KEY is required"):
            DeepSeekClient(api_key=None)

    def test_client_payload_and_headers(self):
        captured_requests = []

        def mock_handler(request: httpx.Request) -> httpx.Response:
            captured_requests.append(request)
            data = {
                "model": "deepseek-v4-flash",
                "choices": [{"message": {"content": "X_PREREQ_Y"}}],
                "usage": {
                    "prompt_tokens": 25,
                    "completion_tokens": 2,
                    "prompt_cache_hit_tokens": 10,
                    "prompt_cache_miss_tokens": 15,
                    "completion_tokens_details": {"reasoning_tokens": 0},
                },
            }
            return httpx.Response(200, json=data)

        transport = httpx.MockTransport(mock_handler)
        http_client = httpx.Client(transport=transport)

        client = DeepSeekClient(
            api_key="test-secret-key",
            base_url="https://api.deepseek.com/v1/",
            model="deepseek-v4-flash",
            client=http_client,
        )

        resp = client.complete("System instruction", "User query")
        assert resp.text == "X_PREREQ_Y"
        assert resp.input_tokens == 25
        assert resp.output_tokens == 2
        assert resp.cache_hit_tokens == 10
        assert resp.cache_miss_tokens == 15
        assert resp.reasoning_tokens == 0
        assert resp.attempts == 1
        assert resp.retry_wait_s == 0.0

        assert len(captured_requests) == 1
        req = captured_requests[0]
        assert req.url == "https://api.deepseek.com/v1/chat/completions"
        assert req.headers["Authorization"] == "Bearer test-secret-key"
        body = json.loads(req.content)
        assert body["model"] == "deepseek-v4-flash"
        assert body["temperature"] == 0.0
        assert body["max_tokens"] == 16
        assert body["thinking"] == {"type": "disabled"}
        assert body["messages"] == [
            {"role": "system", "content": "System instruction"},
            {"role": "user", "content": "User query"},
        ]

    def test_retry_on_429_and_500_excludes_wait_from_latency(self):
        attempt_counter = [0]

        def mock_handler(request: httpx.Request) -> httpx.Response:
            attempt_counter[0] += 1
            if attempt_counter[0] == 1:
                return httpx.Response(429, text="Rate limit exceeded")
            if attempt_counter[0] == 2:
                return httpx.Response(500, text="Internal server error")
            return httpx.Response(
                200,
                json={
                    "model": "deepseek-v4-flash",
                    "choices": [{"message": {"content": "NONE"}}],
                    "usage": {"prompt_tokens": 12, "completion_tokens": 1},
                },
            )

        transport = httpx.MockTransport(mock_handler)
        http_client = httpx.Client(transport=transport)

        client = DeepSeekClient(
            api_key="dummy-key",
            client=http_client,
            backoff_delays=(0.01, 0.02, 0.04),
        )

        resp = client.complete("sys", "usr")
        assert resp.text == "NONE"
        assert resp.attempts == 3
        # Backoff delays were 0.01 + 0.02 = 0.03
        assert pytest.approx(resp.retry_wait_s, abs=1e-3) == 0.03
        # Successful latency is positive and does NOT include the 0.03s sleep
        assert resp.latency_s < 0.03

    def test_non_retryable_400_raises_immediately(self):
        attempt_counter = [0]

        def mock_handler(request: httpx.Request) -> httpx.Response:
            attempt_counter[0] += 1
            return httpx.Response(400, text="Bad Request: invalid parameter")

        transport = httpx.MockTransport(mock_handler)
        http_client = httpx.Client(transport=transport)

        client = DeepSeekClient(
            api_key="dummy-key",
            client=http_client,
            backoff_delays=(0.01,),
        )

        with pytest.raises(LLMTransportError, match="Non-retryable HTTP 400"):
            client.complete("sys", "usr")
        assert attempt_counter[0] == 1

    def test_retry_exhaustion_raises_transport_error(self):
        attempt_counter = [0]

        def mock_handler(request: httpx.Request) -> httpx.Response:
            attempt_counter[0] += 1
            return httpx.Response(503, text="Service Unavailable")

        transport = httpx.MockTransport(mock_handler)
        http_client = httpx.Client(transport=transport)

        client = DeepSeekClient(
            api_key="dummy-key",
            client=http_client,
            max_retries=2,
            backoff_delays=(0.01, 0.01),
        )

        with pytest.raises(LLMTransportError, match="failed after 3 attempts"):
            client.complete("sys", "usr")
        assert attempt_counter[0] == 3
