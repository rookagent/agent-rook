"""
Agent Rook — System prompt builder.

Reads personality from agent.yaml, injects user context and memory,
builds the full system prompt for Claude.
"""
import os
import logging
from datetime import datetime

import pytz

logger = logging.getLogger(__name__)


def build_system_prompt(user=None):
    """
    Build the complete system prompt from agent.yaml config + user context.

    The prompt has two parts:
    1. Static: agent personality, capabilities, rules (cacheable)
    2. Dynamic: current time, user context, memory (per-request)
    """
    from config.settings import Config

    agent_name = Config.AGENT_NAME
    personality = Config.AGENT_PERSONALITY
    categories = Config.MEMORY_CATEGORIES

    # User timezone for date/time
    tz_name = getattr(user, 'timezone', None) or 'US/Eastern'
    try:
        tz = pytz.timezone(tz_name)
    except pytz.UnknownTimeZoneError:
        tz = pytz.timezone('US/Eastern')
    now = datetime.now(tz)

    # Load personality override from file if it exists
    personality_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))),
        'agent', 'prompts', 'personality.md'
    )
    if os.path.exists(personality_file):
        try:
            with open(personality_file) as f:
                personality = f.read().strip()
        except Exception:
            pass

    # Build knowledge module list
    knowledge_summary = _get_knowledge_summary()

    # Build memory block
    memory_block = ""
    if Config.MEMORY_ENABLED and user:
        memory_block = _get_memory_block(user.id)

    prompt = f"""You are {agent_name}.

{personality}

CURRENT DATE & TIME: {now.strftime('%A, %B %d, %Y at %I:%M %p')} ({tz_name})

{f'KNOWLEDGE MODULES AVAILABLE:{chr(10)}{knowledge_summary}' if knowledge_summary else ''}

DATA ACCURACY — NEVER GUESS OR FABRICATE:
When asked about data, records, history, or facts — ALWAYS call the appropriate tool first. NEVER answer from memory or previous conversations. If you don't have fresh tool results in THIS conversation, say "Let me look that up for you" and call the tool.
Your memory is for preferences and goals — NOT for facts, dates, or records.

PAST DATE QUERIES — ALWAYS CALL TOOLS FIRST:
When the user asks about ANY past date ("yesterday", "last Monday", etc.), you MUST call the appropriate tool with the correct date parameter. NEVER say "nothing was found" without calling the tool first. Compute dates from CURRENT DATE & TIME above.

SELF-DIAGNOSIS — WHEN SOMETHING GOES WRONG:
When the user says "that wasn't right", "you messed up", or expresses frustration:
1. Review what tools you called (or didn't call) in this conversation
2. Explain in plain English what went wrong
3. If you can fix it now, fix it immediately
4. If it's a limitation, tell the user exactly what to report to their dev team
Never be defensive. Own the mistake, diagnose it, fix it or explain it.

HONESTY ABOUT YOUR LIMITATIONS:
You CANNOT send messages, emails, or notifications to anyone. You CANNOT "let someone know" or "pass that along." If a user reports a bug you can't handle, give them a clear, copy-paste-ready description of the issue to share with their dev team.

{f'WHAT YOU REMEMBER ABOUT THIS USER:{chr(10)}{memory_block}' if memory_block else ''}

Keep responses practical and actionable. If unsure, say so — better honest than wrong."""

    return prompt


def _get_knowledge_summary():
    """Get a brief list of available knowledge modules for the system prompt."""
    try:
        from app.knowledge.router import get_router
        router = get_router()
        modules = router.get_all_modules()
        if modules:
            lines = [f"- {m['name']}: {m['description']}" for m in modules]
            return '\n'.join(lines)
    except Exception:
        pass
    return ""


def _get_memory_block(user_id):
    """Load formatted memory block for system prompt injection."""
    try:
        from app.models.agent_memory import AgentMemory
        return AgentMemory.get_memories_for_prompt(user_id=user_id) or ""
    except Exception as e:
        logger.debug(f"Memory load failed: {e}")
        return ""
