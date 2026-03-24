"""
Agent Rook — AI client abstraction layer.

Centralizes all LLM API calls behind simple functions.
Currently backed by Anthropic Claude. Designed for easy swap
to OpenAI/Gemini later.

Three core functions:
  - ai_complete()      — standard completion (tools, caching, retry)
  - ai_complete_json() — single-prompt JSON extraction (temp=0)
  - ai_stream()        — returns streaming context manager for SSE
"""
import logging
import os
import time

import httpx

logger = logging.getLogger(__name__)

# ── Model aliases ──
# Override via env vars AI_MODEL_FAST / AI_MODEL_SMART
MODEL_FAST = os.environ.get('AI_MODEL_FAST', 'claude-haiku-4-20250514')
MODEL_SMART = os.environ.get('AI_MODEL_SMART', 'claude-sonnet-4-20250514')

# ── Retry configuration ──
MAX_RETRIES = 3
TRANSIENT_ERRORS = ('overloaded', '529', 'timeout', 'connection', 'timed out')


def _get_client():
    """
    Get Anthropic client instance. Lazy import to avoid cold-start penalty.
    Returns None if API key isn't configured.
    """
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not configured — AI not available")
        return None

    import anthropic
    return anthropic.Anthropic(
        api_key=api_key,
        timeout=httpx.Timeout(connect=60.0, read=120.0, write=60.0, pool=60.0),
    )


def _is_transient(error):
    """Check if an error is transient and retryable."""
    err_s = str(error).lower()
    return any(t in err_s for t in TRANSIENT_ERRORS)


def _retry_call(fn, max_retries=MAX_RETRIES, context="AI"):
    """
    Execute fn() with retry logic for transient API failures.
    Exponential backoff: 2s, 4s, 6s.
    """
    last_err = None
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            last_err = e
            if _is_transient(e):
                logger.warning(f"{context} transient error (attempt {attempt + 1}/{max_retries}): {e}")
                time.sleep(2 * (attempt + 1))
            else:
                raise
    raise last_err


def ai_complete(
    messages,
    system=None,
    model=None,
    max_tokens=1024,
    tools=None,
    temperature=None,
    cache_system=False,
    context="AI",
):
    """
    Send a completion request to the AI provider.

    Args:
        messages: List of {"role": ..., "content": ...} dicts
        system: System prompt — string or list of dicts (for cache_control).
        model: Model ID or alias. Defaults to MODEL_FAST.
        max_tokens: Max response tokens.
        tools: List of tool definitions (Anthropic format).
        temperature: Optional temperature override.
        cache_system: If True and system is a string, wraps with ephemeral cache.
        context: Label for log messages.

    Returns:
        The raw API response object (Anthropic Message).
    """
    client = _get_client()
    if not client:
        raise RuntimeError("AI service not configured")

    model = model or MODEL_FAST

    system_payload = system
    if cache_system and isinstance(system, str):
        system_payload = [
            {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
        ]

    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system_payload is not None:
        kwargs["system"] = system_payload
    if tools:
        kwargs["tools"] = tools
    if temperature is not None:
        kwargs["temperature"] = temperature

    return _retry_call(
        lambda: client.messages.create(**kwargs),
        context=context,
    )


def ai_complete_json(
    prompt,
    model=None,
    max_tokens=500,
    temperature=0,
    context="AI JSON",
):
    """
    Send a single-message completion expecting JSON back.
    Strips markdown code fences automatically.
    """
    response = ai_complete(
        messages=[{"role": "user", "content": prompt}],
        model=model or MODEL_FAST,
        max_tokens=max_tokens,
        temperature=temperature,
        context=context,
    )

    text = response.content[0].text.strip()

    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3].strip()

    return text


def ai_stream(
    messages,
    system=None,
    model=None,
    max_tokens=4096,
    tools=None,
    cache_system=False,
    context="AI stream",
):
    """
    Get a streaming context manager for SSE endpoints.

    Returns a context manager from client.messages.stream().
    Usage:
        with ai_stream(messages=..., system=...) as stream:
            for event in stream:
                ...
            final = stream.get_final_message()
    """
    client = _get_client()
    if not client:
        raise RuntimeError("AI service not configured")

    model = model or MODEL_FAST

    system_payload = system
    if cache_system and isinstance(system, str):
        system_payload = [
            {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
        ]

    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system_payload is not None:
        kwargs["system"] = system_payload
    if tools:
        kwargs["tools"] = tools

    return _retry_call(
        lambda: client.messages.stream(**kwargs),
        context=context,
    )
