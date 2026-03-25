"""
Agent Rook — Streaming chat endpoint (SSE).
Words appear in real-time as the AI generates them.
"""
import json
import logging
import time

from flask import Blueprint, request, Response, stream_with_context
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import limiter
from app.models.user import User
from app.chat.access import check_and_deduct_access
from app.chat.prompts import build_system_prompt
from app.chat.routing import is_simple_query
from app.utils.ai_client import ai_complete, MODEL_FAST, MODEL_SMART

logger = logging.getLogger(__name__)

chat_stream_bp = Blueprint('chat_stream', __name__)


def _sse_event(data, event_type=None):
    """Format a Server-Sent Event."""
    payload = json.dumps(data)
    if event_type:
        return f"event: {event_type}\ndata: {payload}\n\n"
    return f"data: {payload}\n\n"


@chat_stream_bp.route('/stream', methods=['POST'])
@jwt_required()
@limiter.limit("30 per minute")
def stream_message():
    """
    Stream a chat response via Server-Sent Events.
    Sends token, status, heartbeat, error, and done events.
    """
    from config.settings import Config
    from app.chat.engine import _tool_definitions, _execute_tool, _knowledge_tool_names

    data = request.get_json()
    if not data or not data.get('message', '').strip():
        return Response(
            _sse_event({'type': 'error', 'text': 'Message is required'}),
            mimetype='text/event-stream',
        )

    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user:
        return Response(
            _sse_event({'type': 'error', 'text': 'User not found'}),
            mimetype='text/event-stream',
        )

    message = data['message'].strip()[:2000]
    history = data.get('history', [])

    # Access check
    access = check_and_deduct_access(user, daily_limit=Config.FREE_MESSAGES_PER_DAY)
    if not access['allowed']:
        return Response(
            _sse_event({'type': 'error', 'text': access['message']}),
            mimetype='text/event-stream',
        )

    def generate():
        try:
            model = MODEL_FAST if is_simple_query(message) else MODEL_SMART
            messages = (history[-Config.CHAT_MAX_HISTORY:] if history else []) + [{'role': 'user', 'content': message}]
            system_prompt = build_system_prompt(user)
            tools = _tool_definitions if model == MODEL_SMART and _tool_definitions else None

            # Tool dispatch loop (max 3 rounds)
            for _round in range(3):
                # Try streaming first (Anthropic supports it)
                try:
                    from app.utils.ai_client import _get_provider
                    provider = _get_provider()

                    if provider == 'anthropic':
                        yield from _stream_anthropic(messages, system_prompt, model, Config.AI_MAX_TOKENS, tools, user, _round)
                        return
                    else:
                        # Non-streaming fallback for OpenAI/Gemini
                        yield from _stream_fallback(messages, system_prompt, model, Config.AI_MAX_TOKENS, tools, user)
                        return
                except Exception as e:
                    from app.chat.diagnostics import diagnose_api_error
                    diagnosis = diagnose_api_error(e)
                    yield _sse_event({'type': 'error', 'text': diagnosis.summary})
                    return

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield _sse_event({'type': 'error', 'text': 'Something went wrong. Try again.'})

        yield _sse_event({
            'type': 'done',
            'credits_remaining': access.get('remaining', 0),
        })

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        },
    )


def _stream_anthropic(messages, system_prompt, model, max_tokens, tools, user, round_num):
    """Stream using Anthropic's native streaming API with tool dispatch."""
    from app.utils.ai_client import _get_anthropic_client
    from app.chat.engine import _execute_tool, _knowledge_tool_names

    client = _get_anthropic_client()

    system_payload = [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}]
    kwargs = {"model": model, "max_tokens": max_tokens, "messages": messages}
    kwargs["system"] = system_payload
    if tools:
        kwargs["tools"] = tools

    full_text = ""
    tool_blocks = []
    heartbeat_counter = 0

    with client.messages.stream(**kwargs) as stream:
        for event in stream:
            if hasattr(event, 'type'):
                if event.type == 'content_block_delta':
                    if hasattr(event.delta, 'text'):
                        full_text += event.delta.text
                        yield _sse_event({'type': 'token', 'text': event.delta.text})

            # Heartbeat every ~5 seconds worth of events
            heartbeat_counter += 1
            if heartbeat_counter % 50 == 0:
                yield _sse_event({'type': 'heartbeat'})

        # Get final message for tool use detection
        final = stream.get_final_message()

    # Check for tool use
    tool_use_blocks = [b for b in final.content if b.type == 'tool_use']

    if tool_use_blocks and round_num < 3:
        # Execute tools
        tool_results = []
        for block in tool_use_blocks:
            yield _sse_event({'type': 'status', 'text': f'Working on it...'})
            result = _execute_tool(block.name, block.input, user)
            tool_results.append({
                'type': 'tool_result',
                'tool_use_id': block.id,
                'content': str(result),
            })

        # Feed results back and stream the follow-up
        followup_messages = messages + [
            {'role': 'assistant', 'content': final.content},
            {'role': 'user', 'content': tool_results},
        ]

        round_tools = {b.name for b in tool_use_blocks}
        followup_model = MODEL_FAST if round_tools.issubset(_knowledge_tool_names) else model

        yield from _stream_anthropic(followup_messages, system_prompt, followup_model, max_tokens, tools, user, round_num + 1)
    else:
        yield _sse_event({'type': 'done', 'data': None})


def _stream_fallback(messages, system_prompt, model, max_tokens, tools, user):
    """Non-streaming fallback — sends the full response as a single token event."""
    from app.chat.engine import _execute_tool

    response = ai_complete(
        messages=messages, system=system_prompt, model=model,
        max_tokens=max_tokens, tools=tools, cache_system=True, context="Stream fallback",
    )

    text = ""
    for block in response.content:
        if block.type == 'text':
            text += block.text

    # Handle tool use
    tool_blocks = [b for b in response.content if b.type == 'tool_use']
    if tool_blocks:
        yield _sse_event({'type': 'status', 'text': 'Working on it...'})
        tool_results = []
        for block in tool_blocks:
            result = _execute_tool(block.name, block.input, user)
            tool_results.append({
                'type': 'tool_result',
                'tool_use_id': block.id,
                'content': str(result),
            })

        # Follow-up call
        followup_messages = messages + [
            {'role': 'assistant', 'content': response.content},
            {'role': 'user', 'content': tool_results},
        ]
        followup = ai_complete(
            messages=followup_messages, system=system_prompt, model=model,
            max_tokens=max_tokens, tools=tools, context="Stream fallback followup",
        )
        text = ""
        for block in followup.content:
            if block.type == 'text':
                text += block.text

    # Send as chunks to simulate streaming
    words = text.split(' ')
    for i, word in enumerate(words):
        chunk = word + (' ' if i < len(words) - 1 else '')
        yield _sse_event({'type': 'token', 'text': chunk})

    yield _sse_event({'type': 'done', 'data': None})
