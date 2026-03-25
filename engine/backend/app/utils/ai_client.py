"""
Agent Rook — Multi-provider AI client.

Supports Anthropic (Claude), OpenAI (GPT), and Google (Gemini).
Provider configured in agent.yaml under ai.provider.
All providers expose the same interface: ai_complete(), ai_complete_json(), ai_stream().

Tool use is supported on Anthropic and OpenAI. Gemini support is text-only for now.
"""
import logging
import os
import time
import json

import httpx

logger = logging.getLogger(__name__)

# ── Model aliases (override via env vars) ──
MODEL_FAST = os.environ.get('AI_MODEL_FAST', 'claude-haiku-4-20250514')
MODEL_SMART = os.environ.get('AI_MODEL_SMART', 'claude-sonnet-4-20250514')

# ── Provider detection ──
_provider = None

def _get_provider():
    """Determine AI provider from config. Cached after first call."""
    global _provider
    if _provider:
        return _provider
    try:
        from config.settings import AGENT_CONFIG
        _provider = AGENT_CONFIG.get('ai', {}).get('provider', 'anthropic').lower()
    except Exception:
        _provider = 'anthropic'
    return _provider

# ── Retry configuration ──
MAX_RETRIES = 3
TRANSIENT_ERRORS = ('overloaded', '529', 'timeout', 'connection', 'timed out', 'rate_limit', '429', '503')

def _is_transient(error):
    err_s = str(error).lower()
    return any(t in err_s for t in TRANSIENT_ERRORS)

def _retry_call(fn, max_retries=MAX_RETRIES, context="AI"):
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


# ═══════════════════════════════════════════════════════════════
# ANTHROPIC (Claude)
# ═══════════════════════════════════════════════════════════════

def _get_anthropic_client():
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")
    import anthropic
    return anthropic.Anthropic(
        api_key=api_key,
        timeout=httpx.Timeout(connect=60.0, read=120.0, write=60.0, pool=60.0),
    )

def _anthropic_complete(messages, system=None, model=None, max_tokens=1024, tools=None, temperature=None, cache_system=False, context="AI"):
    client = _get_anthropic_client()
    model = model or MODEL_FAST

    system_payload = system
    if cache_system and isinstance(system, str):
        system_payload = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]

    kwargs = {"model": model, "max_tokens": max_tokens, "messages": messages}
    if system_payload is not None:
        kwargs["system"] = system_payload
    if tools:
        kwargs["tools"] = tools
    if temperature is not None:
        kwargs["temperature"] = temperature

    return _retry_call(lambda: client.messages.create(**kwargs), context=context)

def _anthropic_stream(messages, system=None, model=None, max_tokens=4096, tools=None, cache_system=False, context="AI stream"):
    client = _get_anthropic_client()
    model = model or MODEL_FAST

    system_payload = system
    if cache_system and isinstance(system, str):
        system_payload = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]

    kwargs = {"model": model, "max_tokens": max_tokens, "messages": messages}
    if system_payload is not None:
        kwargs["system"] = system_payload
    if tools:
        kwargs["tools"] = tools

    return _retry_call(lambda: client.messages.stream(**kwargs), context=context)


# ═══════════════════════════════════════════════════════════════
# OPENAI (GPT)
# ═══════════════════════════════════════════════════════════════

def _get_openai_client():
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")
    try:
        import openai
        return openai.OpenAI(api_key=api_key)
    except ImportError:
        raise RuntimeError("openai package not installed. Run: pip install openai")

def _openai_convert_messages(messages, system=None):
    """Convert Anthropic-style messages to OpenAI format."""
    oai_messages = []
    if system:
        oai_messages.append({"role": "system", "content": system if isinstance(system, str) else system[0].get("text", str(system))})

    for msg in messages:
        content = msg.get("content", "")
        role = msg.get("role", "user")

        # Handle Anthropic tool_result format
        if role == "user" and isinstance(content, list):
            # Tool results — convert to assistant function responses
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    oai_messages.append({
                        "role": "tool",
                        "tool_call_id": block.get("tool_use_id", ""),
                        "content": str(block.get("content", "")),
                    })
            continue

        # Handle Anthropic assistant response with tool_use blocks
        if role == "assistant" and not isinstance(content, str):
            text_parts = []
            tool_calls = []
            for block in content:
                if hasattr(block, 'type'):
                    if block.type == 'text':
                        text_parts.append(block.text)
                    elif block.type == 'tool_use':
                        tool_calls.append({
                            "id": block.id,
                            "type": "function",
                            "function": {"name": block.name, "arguments": json.dumps(block.input)},
                        })
            msg_dict = {"role": "assistant", "content": "\n".join(text_parts) if text_parts else None}
            if tool_calls:
                msg_dict["tool_calls"] = tool_calls
            oai_messages.append(msg_dict)
            continue

        oai_messages.append({"role": role, "content": str(content)})

    return oai_messages

def _openai_convert_tools(tools):
    """Convert Anthropic tool format to OpenAI function format."""
    if not tools:
        return None
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
            }
        }
        for t in tools
    ]

class _OpenAIResponseAdapter:
    """Wraps OpenAI response to look like Anthropic Message for the engine."""
    def __init__(self, oai_response):
        self._raw = oai_response
        self.content = []
        choice = oai_response.choices[0]
        msg = choice.message

        if msg.content:
            self.content.append(_TextBlock(msg.content))

        if msg.tool_calls:
            for tc in msg.tool_calls:
                self.content.append(_ToolUseBlock(
                    id=tc.id,
                    name=tc.function.name,
                    input=json.loads(tc.function.arguments),
                ))

class _TextBlock:
    def __init__(self, text):
        self.type = 'text'
        self.text = text

class _ToolUseBlock:
    def __init__(self, id, name, input):
        self.type = 'tool_use'
        self.id = id
        self.name = name
        self.input = input

def _openai_complete(messages, system=None, model=None, max_tokens=1024, tools=None, temperature=None, cache_system=False, context="AI"):
    client = _get_openai_client()
    model = model or 'gpt-4o'

    oai_messages = _openai_convert_messages(messages, system)
    oai_tools = _openai_convert_tools(tools)

    kwargs = {"model": model, "messages": oai_messages, "max_tokens": max_tokens}
    if oai_tools:
        kwargs["tools"] = oai_tools
    if temperature is not None:
        kwargs["temperature"] = temperature

    response = _retry_call(lambda: client.chat.completions.create(**kwargs), context=context)
    return _OpenAIResponseAdapter(response)

def _openai_stream(messages, system=None, model=None, max_tokens=4096, tools=None, cache_system=False, context="AI stream"):
    # OpenAI streaming returns a different format — for now, fall back to non-streaming
    logger.info("OpenAI streaming not yet implemented — using non-streaming fallback")
    return _openai_complete(messages, system, model, max_tokens, tools, context=context)


# ═══════════════════════════════════════════════════════════════
# GOOGLE (Gemini)
# ═══════════════════════════════════════════════════════════════

def _get_gemini_client():
    api_key = os.environ.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY or GEMINI_API_KEY not configured")
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        return genai
    except ImportError:
        raise RuntimeError("google-generativeai package not installed. Run: pip install google-generativeai")

def _gemini_complete(messages, system=None, model=None, max_tokens=1024, tools=None, temperature=None, cache_system=False, context="AI"):
    genai = _get_gemini_client()
    model_name = model or 'gemini-2.0-flash'

    # Build conversation
    system_text = system if isinstance(system, str) else (system[0].get("text", "") if isinstance(system, list) else "")

    gemini_model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_text if system_text else None,
    )

    # Convert messages to Gemini format
    gemini_history = []
    for msg in messages[:-1]:  # History (all but last)
        role = 'user' if msg['role'] == 'user' else 'model'
        content = msg.get('content', '')
        if isinstance(content, str):
            gemini_history.append({"role": role, "parts": [content]})

    last_msg = messages[-1]
    last_content = last_msg.get('content', '')
    if not isinstance(last_content, str):
        last_content = str(last_content)

    chat = gemini_model.start_chat(history=gemini_history)

    gen_config = {}
    if max_tokens:
        gen_config['max_output_tokens'] = max_tokens
    if temperature is not None:
        gen_config['temperature'] = temperature

    response = _retry_call(
        lambda: chat.send_message(last_content, generation_config=gen_config if gen_config else None),
        context=context,
    )

    # Wrap in Anthropic-compatible format
    return _GeminiResponseAdapter(response)

class _GeminiResponseAdapter:
    def __init__(self, response):
        self.content = [_TextBlock(response.text)]

def _gemini_stream(messages, system=None, model=None, max_tokens=4096, tools=None, cache_system=False, context="AI stream"):
    logger.info("Gemini streaming not yet implemented — using non-streaming fallback")
    return _gemini_complete(messages, system, model, max_tokens, tools, context=context)


# ═══════════════════════════════════════════════════════════════
# PUBLIC API — Provider-agnostic interface
# ═══════════════════════════════════════════════════════════════

_PROVIDERS = {
    'anthropic': {'complete': _anthropic_complete, 'stream': _anthropic_stream},
    'openai': {'complete': _openai_complete, 'stream': _openai_stream},
    'gemini': {'complete': _gemini_complete, 'stream': _gemini_stream},
    'google': {'complete': _gemini_complete, 'stream': _gemini_stream},
}

def ai_complete(messages, system=None, model=None, max_tokens=1024, tools=None, temperature=None, cache_system=False, context="AI"):
    """
    Send a completion request to the configured AI provider.
    Returns a response object with .content list of text/tool_use blocks.
    """
    provider = _get_provider()
    handler = _PROVIDERS.get(provider, {}).get('complete')
    if not handler:
        raise RuntimeError(f"Unknown AI provider: {provider}. Supported: {', '.join(_PROVIDERS.keys())}")
    return handler(messages, system, model, max_tokens, tools, temperature, cache_system, context)

def ai_complete_json(prompt, model=None, max_tokens=500, temperature=0, context="AI JSON"):
    """Single-message completion expecting JSON back. Strips markdown fences."""
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

def ai_stream(messages, system=None, model=None, max_tokens=4096, tools=None, cache_system=False, context="AI stream"):
    """Get a streaming response. Falls back to non-streaming on providers that don't support it yet."""
    provider = _get_provider()
    handler = _PROVIDERS.get(provider, {}).get('stream')
    if not handler:
        raise RuntimeError(f"Unknown AI provider: {provider}")
    return handler(messages, system, model, max_tokens, tools, cache_system, context)
