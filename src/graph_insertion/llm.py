"""
llm.py — INFRA-006
==================
Metered LLM client abstractions, transport handling, and DeepSeek client.

Decisions recorded here:
  - LLM = DeepSeek V4 Flash via DeepSeek's official API, non-thinking mode, temperature 0 ([D-29])
  - Client transport via httpx with exponential backoff on 429/5xx ([D-29])
  - Token and timing tracking via MeteredLLMClient with snapshot subtraction ([D-29])
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol, Sequence, Union, runtime_checkable

import httpx


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class LLMTransportError(RuntimeError):
    """Raised when an LLM API request fails after retries or encounters non-retryable error."""

    def __init__(
        self,
        message: str,
        *,
        attempts: int = 1,
        retry_wait_s: float = 0.0,
    ) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.retry_wait_s = retry_wait_s


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LLMResponse:
    """Structured response from an LLM completion request.

    Attributes
    ----------
    text:
        Raw text completion returned by the model.
    input_tokens:
        Number of prompt tokens processed.
    output_tokens:
        Number of completion tokens generated.
    reasoning_tokens:
        Number of tokens generated for chain-of-thought (0 if not reported).
    cache_hit_tokens:
        Number of prompt tokens that hit context cache (0 if not reported).
    cache_miss_tokens:
        Number of prompt tokens that missed context cache (0 if not reported).
    latency_s:
        Wall-clock latency in seconds for the successful request attempt.
    model_id:
        Model identifier string as reported by the API.
    attempts:
        Total number of request attempts made (1 + retries).
    retry_wait_s:
        Cumulative seconds spent waiting in retry backoff before success.
    """
    text: str
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int = 0
    cache_hit_tokens: int = 0
    cache_miss_tokens: int = 0
    latency_s: float = 0.0
    model_id: str = ""
    attempts: int = 1
    retry_wait_s: float = 0.0


@dataclass(frozen=True)
class LLMSnapshot:
    """Frozen point-in-time snapshot of cumulative LLM usage and metrics.

    Supports subtraction (`snap2 - snap1`) to measure per-insertion or
    per-operation resource deltas.
    """
    calls: int
    attempts: int
    retries: int
    parse_failures: int
    latency_s: float
    retry_wait_s: float
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    cache_hit_tokens: int
    cache_miss_tokens: int
    failed_parses: tuple[str, ...] = ()

    def __sub__(self, other: LLMSnapshot) -> LLMSnapshot:
        if not isinstance(other, LLMSnapshot):
            return NotImplemented
        sub_failed: tuple[str, ...]
        if len(self.failed_parses) >= len(other.failed_parses):
            sub_failed = self.failed_parses[len(other.failed_parses):]
        else:
            sub_failed = ()
        return LLMSnapshot(
            calls=self.calls - other.calls,
            attempts=self.attempts - other.attempts,
            retries=self.retries - other.retries,
            parse_failures=self.parse_failures - other.parse_failures,
            latency_s=self.latency_s - other.latency_s,
            retry_wait_s=self.retry_wait_s - other.retry_wait_s,
            input_tokens=self.input_tokens - other.input_tokens,
            output_tokens=self.output_tokens - other.output_tokens,
            reasoning_tokens=self.reasoning_tokens - other.reasoning_tokens,
            cache_hit_tokens=self.cache_hit_tokens - other.cache_hit_tokens,
            cache_miss_tokens=self.cache_miss_tokens - other.cache_miss_tokens,
            failed_parses=sub_failed,
        )


# ---------------------------------------------------------------------------
# Client Protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class LLMClient(Protocol):
    """Protocol for LLM completions."""

    def complete(self, system: str, user: str) -> LLMResponse:
        """Generate a completion for the given system and user prompts."""
        ...


# ---------------------------------------------------------------------------
# Metered LLM Client Wrapper
# ---------------------------------------------------------------------------

class MeteredLLMClient:
    """Wraps any LLMClient to track call counts, latencies, tokens, and parse failures.

    Provides point-in-time snapshots and snapshot subtraction for delta accounting.
    """

    def __init__(
        self,
        client: LLMClient,
        *,
        on_call: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        self.client = client
        self.on_call = on_call
        self.calls: int = 0
        self.attempts: int = 0
        self.retries: int = 0
        self.parse_failures: int = 0
        self.cumulative_latency_s: float = 0.0
        self.cumulative_retry_wait_s: float = 0.0
        self.input_tokens: int = 0
        self.output_tokens: int = 0
        self.reasoning_tokens: int = 0
        self.cache_hit_tokens: int = 0
        self.cache_miss_tokens: int = 0
        self.failed_parses: list[str] = []
        self.model_ids_seen: set[str] = set()
        self.failed_calls: list[dict[str, Any]] = []

    def set_on_call(self, on_call: Optional[Callable[[int, int], None]]) -> None:
        """Register or update a callback invoked with (calls_done, cumulative_retries) on every LLM call."""
        self.on_call = on_call

    def complete(self, system: str, user: str) -> LLMResponse:
        """Delegate completion to wrapped client and record usage."""
        try:
            resp = self.client.complete(system, user)
        except Exception as exc:
            self.calls += 1
            attempts = getattr(exc, "attempts", 1)
            retry_wait_s = getattr(exc, "retry_wait_s", 0.0)
            self.attempts += attempts
            self.retries += max(0, attempts - 1)
            self.cumulative_retry_wait_s += retry_wait_s
            self.failed_calls.append({
                "attempts": attempts,
                "retry_wait_s": retry_wait_s,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            })
            if self.on_call is not None:
                try:
                    self.on_call(self.calls, self.retries)
                except Exception:
                    pass
            raise

        self.calls += 1
        self.attempts += resp.attempts
        self.retries += max(0, resp.attempts - 1)
        self.cumulative_latency_s += resp.latency_s
        self.cumulative_retry_wait_s += resp.retry_wait_s
        self.input_tokens += resp.input_tokens
        self.output_tokens += resp.output_tokens
        self.reasoning_tokens += resp.reasoning_tokens
        self.cache_hit_tokens += resp.cache_hit_tokens
        self.cache_miss_tokens += resp.cache_miss_tokens
        if resp.model_id:
            self.model_ids_seen.add(resp.model_id)
        if self.on_call is not None:
            try:
                self.on_call(self.calls, self.retries)
            except Exception:
                pass
        return resp

    def record_parse_failure(self, raw_text: str) -> None:
        """Record an unparseable response string."""
        self.parse_failures += 1
        self.failed_parses.append(raw_text)

    def snapshot(self) -> LLMSnapshot:
        """Capture an immutable point-in-time metrics snapshot."""
        return LLMSnapshot(
            calls=self.calls,
            attempts=self.attempts,
            retries=self.retries,
            parse_failures=self.parse_failures,
            latency_s=self.cumulative_latency_s,
            retry_wait_s=self.cumulative_retry_wait_s,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            reasoning_tokens=self.reasoning_tokens,
            cache_hit_tokens=self.cache_hit_tokens,
            cache_miss_tokens=self.cache_miss_tokens,
            failed_parses=tuple(self.failed_parses),
        )

    def reset(self) -> None:
        """Reset all counters and logs to zero."""
        self.calls = 0
        self.attempts = 0
        self.retries = 0
        self.parse_failures = 0
        self.cumulative_latency_s = 0.0
        self.cumulative_retry_wait_s = 0.0
        self.input_tokens = 0
        self.output_tokens = 0
        self.reasoning_tokens = 0
        self.cache_hit_tokens = 0
        self.cache_miss_tokens = 0
        self.failed_parses.clear()
        self.model_ids_seen.clear()
        self.failed_calls.clear()



# ---------------------------------------------------------------------------
# DeepSeek API Client
# ---------------------------------------------------------------------------

class DeepSeekClient:
    """Official DeepSeek API client via OpenAI-compatible HTTP endpoints.

    Configured for non-thinking mode, temperature 0, and pairwise candidate evaluation.
    """

    DEFAULT_BASE_URL: str = "https://api.deepseek.com"
    DEFAULT_MODEL: str = "deepseek-flash"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        *,
        timeout: float = 60.0,
        max_retries: int = 3,
        backoff_delays: Sequence[float] = (1.0, 2.0, 4.0),
        client: Optional[httpx.Client] = None,
    ) -> None:
        key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not key:
            raise ValueError(
                "DEEPSEEK_API_KEY is required. Pass it explicitly or set the DEEPSEEK_API_KEY environment variable."
            )
        self.api_key = key
        self.base_url = (base_url or os.environ.get("DEEPSEEK_BASE_URL") or self.DEFAULT_BASE_URL).rstrip("/")
        self.model = model or os.environ.get("DEEPSEEK_MODEL") or self.DEFAULT_MODEL
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_delays = tuple(backoff_delays)
        self._external_client = client is not None
        self._client = client or httpx.Client(timeout=self.timeout)
        self.temperature: float = 0.0
        self.max_tokens: int = 16
        self.thinking: dict[str, Any] = {"type": "disabled"}
        self.thinking_mode: str = "disabled"

    def close(self) -> None:
        """Close the underlying HTTP client if internally managed."""
        if not self._external_client:
            self._client.close()

    def __enter__(self) -> DeepSeekClient:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def complete(self, system: str, user: str) -> LLMResponse:
        """Send completion request to DeepSeek API with retry handling."""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "thinking": self.thinking,
        }

        attempts = 0
        total_retry_wait_s = 0.0
        last_exception: Optional[Exception] = None

        while attempts <= self.max_retries:
            attempts += 1
            t0 = time.perf_counter()
            try:
                resp = self._client.post(url, json=payload, headers=headers)
                latency_s = time.perf_counter() - t0

                # Check status
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                    except Exception as e:
                        last_exception = LLMTransportError(
                            f"HTTP 200 with invalid JSON response: {e}",
                            attempts=attempts,
                            retry_wait_s=total_retry_wait_s,
                        )
                    else:
                        choices = data.get("choices", [])
                        if not choices:
                            last_exception = LLMTransportError(
                                f"DeepSeek API response missing choices: {data}",
                                attempts=attempts,
                                retry_wait_s=total_retry_wait_s,
                            )
                        else:
                            content = choices[0].get("message", {}).get("content", "")
                            usage = data.get("usage", {})
                            input_tokens = usage.get("prompt_tokens", 0)
                            output_tokens = usage.get("completion_tokens", 0)
                            reasoning_tokens = (
                                usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0)
                                or usage.get("reasoning_tokens", 0)
                            )
                            cache_hit_tokens = (
                                usage.get("prompt_cache_hit_tokens", 0)
                                or usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)
                            )
                            cache_miss_tokens = usage.get("prompt_cache_miss_tokens", 0) or max(
                                0, input_tokens - cache_hit_tokens
                            )
                            model_id = data.get("model") or ""

                            return LLMResponse(
                                text=content,
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                reasoning_tokens=reasoning_tokens,
                                cache_hit_tokens=cache_hit_tokens,
                                cache_miss_tokens=cache_miss_tokens,
                                latency_s=latency_s,
                                model_id=model_id,
                                attempts=attempts,
                                retry_wait_s=total_retry_wait_s,
                            )

                # Retryable HTTP status codes
                elif resp.status_code in (429, 500, 502, 503, 504):
                    err_msg = f"HTTP {resp.status_code}: {resp.text}"
                    last_exception = LLMTransportError(
                        err_msg,
                        attempts=attempts,
                        retry_wait_s=total_retry_wait_s,
                    )
                else:
                    # Non-retryable 4xx
                    raise LLMTransportError(
                        f"Non-retryable HTTP {resp.status_code} from DeepSeek API: {resp.text}",
                        attempts=attempts,
                        retry_wait_s=total_retry_wait_s,
                    )

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_exception = e
            except LLMTransportError:
                raise

            # If retries remain, back off
            if attempts <= self.max_retries:
                delay_idx = min(attempts - 1, len(self.backoff_delays) - 1)
                delay = self.backoff_delays[delay_idx]
                time.sleep(delay)
                total_retry_wait_s += delay

        raise LLMTransportError(
            f"DeepSeek API call failed after {attempts} attempts. Last error: {last_exception}",
            attempts=attempts,
            retry_wait_s=total_retry_wait_s,
        )


# ---------------------------------------------------------------------------
# Fake / Mock Client for Testing & Simulation
# ---------------------------------------------------------------------------

class FakeLLMClient:
    """Deterministic, scriptable LLMClient for unit tests and offline simulation.

    Supports canned responses, simulated latencies, token counts, and scripted transport errors.
    """

    def __init__(
        self,
        responses: Optional[Union[dict[Union[str, tuple[str, str]], str], Callable[[str, str], str], str]] = None,
        *,
        latency_s: float = 0.0,
        errors: Optional[Sequence[Exception]] = None,
        input_tokens: int = 15,
        output_tokens: int = 2,
        reasoning_tokens: int = 0,
        cache_hit_tokens: int = 0,
        cache_miss_tokens: int = 15,
        model_id: str = "fake-deepseek-flash",
    ) -> None:
        self.responses = responses
        self.latency_s = latency_s
        self.errors: list[Exception] = list(errors) if errors is not None else []
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.reasoning_tokens = reasoning_tokens
        self.cache_hit_tokens = cache_hit_tokens
        self.cache_miss_tokens = cache_miss_tokens
        self.model_id = model_id
        self.model = model_id
        self.base_url = "fake://localhost"
        self.temperature = 0.0
        self.max_tokens = 16
        self.thinking = {"type": "disabled"}
        self.thinking_mode = "disabled"
        self.call_history: list[dict[str, Any]] = []

    def complete(self, system: str, user: str) -> LLMResponse:
        """Return scripted response or raise scripted error."""
        self.call_history.append({"system": system, "user": user})

        if self.errors:
            err = self.errors.pop(0)
            raise err

        if callable(self.responses):
            text = self.responses(system, user)
        elif isinstance(self.responses, dict):
            # Try (system, user), then user alone
            if (system, user) in self.responses:
                text = self.responses[(system, user)]
            elif user in self.responses:
                text = self.responses[user]
            else:
                text = "NONE"
        elif isinstance(self.responses, str):
            text = self.responses
        else:
            text = "NONE"

        return LLMResponse(
            text=text,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            reasoning_tokens=self.reasoning_tokens,
            cache_hit_tokens=self.cache_hit_tokens,
            cache_miss_tokens=self.cache_miss_tokens,
            latency_s=self.latency_s,
            model_id=self.model_id,
            attempts=1,
            retry_wait_s=0.0,
        )
