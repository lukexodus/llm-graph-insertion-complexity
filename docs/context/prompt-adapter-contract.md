# Claude Automator Prompt Adapter Contract — v1

This document specifies Contract v1 of the claude-automator `prompt-adapter`.
The adapter provides a headless CLI interface to execute prompts sequentially against
Claude via the claude.ai web UI.

---

## 1. Specification

One process = one prompt = one FRESH claude.ai conversation; run sequentially.

### Standard Input (`stdin`)

Exactly one JSON object with the following fields:

- `prompt` (str, required): The prompt text to submit.
- `profile` (str, required): Browser profile name to use.
- `model` (str, optional, default `"sonnet"`): Model identifier requested.
- `effort` (str or null, optional, default `"low"`): Effort tier (`"low"`, `"medium"`, `"high"`, `"extra"`, `"max"`, or `null`).
- `thinking` (bool or null, optional, default `null`): Thinking mode toggle.
- `web_search` (bool, optional, default `false`): Enable web search tool.
- `memory` (bool, optional, default `false`): Enable memory retrieval. Must be `false` for benchmark runs.
- `headless` (bool, optional, default `false`): Run browser in headless mode.
- `timeout_s` (int, optional, default `300`): Maximum seconds to wait for conversation response.

### Standard Output (`stdout`)

Exactly one JSON object. Diagnostic logs are emitted to `stderr` only.

#### Success Response

```json
{
  "ok": true,
  "text": str,
  "tier": 1 | 2 | 3 | null,
  "model_requested": str,
  "model_observed": str | null,
  "effort_requested": str | null,
  "memory_requested": bool,
  "web_search_requested": bool,
  "elapsed_s": float,
  "adapter": {
    "name": "prompt-adapter",
    "version": str
  }
}
```

#### Failure Response

```json
{
  "ok": false,
  "error": CODE,
  "message": str,
  "reset_time": str | null
}
```

### Exit and Error Codes

| Code | Name | Meaning |
| :--- | :--- | :--- |
| `0` | `ok` | Successful execution |
| `1` | `other` | Unclassified error / internal adapter failure |
| `2` | `bad_request` | Invalid stdin JSON or missing required parameter |
| `10` | `rate_limit` | Rate limit or usage quota reached on claude.ai |
| `11` | `login_required` | Session expired, CAPTCHA challenge, or login required |
| `12` | `timeout` | Browser automation or response generation timed out |
| `13` | `refusal` | Model refused to respond or content blocked |
| `14` | `model_mismatch` | Observed UI model did not match requested model |

---

## 2. Fixtures

### Example Request (`stdin`)

```json
{
  "prompt": "You are a computer science curriculum expert. List 40 distinct core concept names in algorithms as a JSON array of lowercase snake_case strings.",
  "profile": "research-profile",
  "model": "sonnet",
  "effort": "low",
  "thinking": null,
  "web_search": false,
  "memory": false,
  "headless": true,
  "timeout_s": 300
}
```

### Example Responses (`stdout`)

#### Success (Exit Code 0)

```json
{
  "ok": true,
  "text": "[\"binary_search\", \"breadth_first_search\", \"depth_first_search\", \"dijkstra_algorithm\"]",
  "tier": 1,
  "model_requested": "sonnet",
  "model_observed": "Claude 3.5 Sonnet",
  "effort_requested": "low",
  "memory_requested": false,
  "web_search_requested": false,
  "elapsed_s": 14.82,
  "adapter": {
    "name": "prompt-adapter",
    "version": "1.0.0"
  }
}
```

#### Failure: Rate Limit (Error Code 10, Exit Code 3 in caller)

```json
{
  "ok": false,
  "error": 10,
  "message": "You have reached your usage limit for Claude 3.5 Sonnet.",
  "reset_time": "2026-10-07T23:00:00Z"
}
```

#### Failure: Login Required (Error Code 11, Exit Code 4 in caller)

```json
{
  "ok": false,
  "error": 11,
  "message": "Login session expired or Cloudflare turnstile challenge presented.",
  "reset_time": null
}
```

#### Failure: Model Mismatch (Error Code 14, Exit Code 5 in caller)

```json
{
  "ok": false,
  "error": 14,
  "message": "Model mismatch: requested 'sonnet' but observed 'Claude 3 Haiku' in UI.",
  "reset_time": null
}
```

#### Failure: Timeout (Error Code 12, Exit Code 6 in caller if 3 consecutive)

```json
{
  "ok": false,
  "error": 12,
  "message": "Response generation timed out after 300 seconds.",
  "reset_time": null
}
```

#### Failure: Refusal (Error Code 13, Exit Code 6 in caller if 3 consecutive)

```json
{
  "ok": false,
  "error": 13,
  "message": "Model refused to answer the prompt.",
  "reset_time": null
}
```

#### Failure: Bad Request (Error Code 2, Exit Code 1 in caller)

```json
{
  "ok": false,
  "error": 2,
  "message": "Missing required field 'prompt' in stdin JSON.",
  "reset_time": null
}
```

#### Failure: Other (Error Code 1, Exit Code 6 in caller if 3 consecutive)

```json
{
  "ok": false,
  "error": 1,
  "message": "Browser process crashed unexpectedly.",
  "reset_time": null
}
```
