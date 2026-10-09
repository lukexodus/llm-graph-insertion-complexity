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

Note: Unknown additive fields (e.g., `profile_used`) may be present in responses and must be tolerated by callers.

#### Failure Response

```json
{
  "ok": false,
  "error": str,
  "message": str,
  "reset_time": str | null
}
```

### Exit and Error Codes

| Exit Code | Error String (`error`) | Meaning |
| :--- | :--- | :--- |
| `0` | (none / `ok`) | Successful execution |
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
  "prompt": "You are a computer science curriculum expert. When prompted with a computer science subfield, generate a JSON array of core concept names taught in undergraduate and graduate courses in that subfield.\nRules:\n1. Return ONLY a valid JSON array of strings: [\"concept_one\", \"concept_two\", ...].\n2. No conversational text, no Markdown code fences, no descriptions, and no numbers.\n3. Each concept name must be lowercase snake_case (e.g. 'binary_search_tree', 'page_table').\n4. Each concept name must be 1 to 4 words long.\n5. Do NOT include file extensions (never end in '.txt').\n6. Focus on distinct, canonical foundational concepts.\n\nList 40 distinct, specific core concept names taught in a computer science curriculum for the subfield 'algorithms'.\nOutput must be a valid JSON array of 40 lowercase snake_case strings (1-4 words each, no file extensions, concept names only).",
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
  "text": "[\"binary_search\", \"merge_sort\", \"quick_sort\", \"heap_sort\"]",
  "tier": 2,
  "model_requested": "sonnet",
  "model_observed": "Sonnet 5.5 Low",
  "effort_requested": "low",
  "memory_requested": false,
  "web_search_requested": false,
  "profile_used": "Profile 24",
  "elapsed_s": 35.91,
  "adapter": {
    "name": "prompt-adapter",
    "version": "a4f117c-dirty"
  }
}
```

#### Failure: Rate Limit (Exit Code 10, Exit Code 3 in caller)

```json
{
  "ok": false,
  "error": "rate_limit",
  "message": "You have reached your usage limit for Sonnet 5.5 Low.",
  "reset_time": "2026-10-07T23:00:00Z"
}
```

#### Failure: Login Required (Exit Code 11, Exit Code 4 in caller)

```json
{
  "ok": false,
  "error": "login_required",
  "message": "Login session expired or Cloudflare turnstile challenge presented.",
  "reset_time": null
}
```

#### Failure: Model Mismatch (Exit Code 14, Exit Code 5 in caller)

```json
{
  "ok": false,
  "error": "model_mismatch",
  "message": "Model mismatch: requested 'sonnet' but observed 'Sonnet 5.5 Low' in UI.",
  "reset_time": null
}
```

#### Failure: Timeout (Exit Code 12, Exit Code 6 in caller if 3 consecutive)

```json
{
  "ok": false,
  "error": "timeout",
  "message": "Response generation timed out after 300 seconds.",
  "reset_time": null
}
```

#### Failure: Refusal (Exit Code 13, Exit Code 6 in caller if 3 consecutive)

```json
{
  "ok": false,
  "error": "refusal",
  "message": "Model refused to answer the prompt.",
  "reset_time": null
}
```

#### Failure: Bad Request (Exit Code 2, Exit Code 1 in caller)

```json
{
  "ok": false,
  "error": "bad_request",
  "message": "Missing required field 'prompt' in stdin JSON.",
  "reset_time": null
}
```

#### Failure: Other (Exit Code 1, Exit Code 6 in caller if 3 consecutive)

```json
{
  "ok": false,
  "error": "other",
  "message": "Browser process crashed unexpectedly.",
  "reset_time": null
}
```
