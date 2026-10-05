"""
llm.py - the ONLY place that talks to the AI model.

- Uses the OpenAI-compatible API on OpenRouter (production: Azure OpenAI in Bellcourt's tenant,
  which has a HIPAA BAA - change LLM_BASE_URL and the key, nothing else).
- temperature 0 = as repeatable as possible.
- Every answer is saved in llm_cache/ by a fingerprint of (model + prompt). Asking the same thing
  again returns the saved answer: no extra cost, and the demo works offline once it has run.
"""
import hashlib
import json

from config import LLM_BASE_URL, LLM_CACHE_DIR, LLM_MODEL, OPENROUTER_API_KEY


class AIUnavailable(Exception):
    """Raised when the AI can't be reached. The rest of the tool still works without it."""


def fingerprint(system: str, user: str) -> str:
    return hashlib.sha256(f"{LLM_MODEL}\n{system}\n{user}".encode("utf-8")).hexdigest()[:16]


def ask(system: str, user: str, use_cache: bool = True) -> dict:
    """Send one prompt. Returns {"text", "model", "fingerprint", "from_cache"}."""
    fp = fingerprint(system, user)
    cache_file = LLM_CACHE_DIR / f"{fp}.json"
    if use_cache and cache_file.exists():
        saved = json.loads(cache_file.read_text(encoding="utf-8"))
        saved["from_cache"] = True
        return saved

    if not OPENROUTER_API_KEY:
        raise AIUnavailable("No OPENROUTER_API_KEY found. Put it in pa-copilot/.env (see .env.example).")
    try:
        from openai import OpenAI
        client = OpenAI(base_url=LLM_BASE_URL, api_key=OPENROUTER_API_KEY, timeout=90, max_retries=2)
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            temperature=0,
            max_tokens=4000,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        text = resp.choices[0].message.content or ""
    except Exception as err:                               # network, wrong key, wrong model name...
        raise AIUnavailable(f"AI call failed: {type(err).__name__}: {err}") from err

    out = {"text": text, "model": LLM_MODEL, "fingerprint": fp, "from_cache": False}
    LLM_CACHE_DIR.mkdir(exist_ok=True)
    cache_file.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out
