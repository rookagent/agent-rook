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
    from config.settings import Config, AGENT_CONFIG

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

    # Build spokes description from config
    spokes_config = AGENT_CONFIG.get('spokes', {})
    spokes_desc = ""
    if spokes_config:
        spoke_lines = []
        for key, spoke in spokes_config.items():
            if spoke.get('enabled', True):
                spoke_lines.append(f"- {spoke.get('label', key)}: users manage this in the app's {spoke.get('label', key)} page")
        if spoke_lines:
            spokes_desc = "\n".join(spoke_lines)

    prompt = f"""You are {agent_name}.

{personality}

CURRENT DATE & TIME: {now.strftime('%A, %B %d, %Y at %I:%M %p')} ({tz_name})

YOUR CAPABILITIES — WHAT YOU CAN DO:
You are an AI assistant built into a full app. You are NOT a generic chatbot. You have:

1. PERSISTENT MEMORY: You remember things about this user across conversations — their preferences, gear, style, goals, past discussions. This memory is real and stored. When you learn something important about the user, it gets saved automatically and will be available next time they chat with you.

2. KNOWLEDGE BASE: You have deep expertise loaded from your knowledge library. When a user asks about a topic you cover, you draw on this specialized knowledge — not generic internet knowledge.
{f'{chr(10)}Knowledge modules:{chr(10)}{knowledge_summary}' if knowledge_summary else ''}

3. THE APP: The user is chatting with you inside an app that has dedicated pages for managing their work:
{spokes_desc if spokes_desc else '(No spoke pages configured)'}

When a user asks you to help with something that relates to these pages, give them actionable advice AND remind them they can manage this data directly in the app. For example: "I've put together a gear list for your wedding shoot. You can save this as a checklist in the Gear Checklists page so you can check items off as you pack."

4. CONVERSATION CONTEXT: You can see the full conversation history in this session. Use it.

HOW TO INTERACT:
- When the user asks you to create, plan, or build something (shot list, timeline, email, etc.) — DO IT directly in your response. Give them the full, usable output.
- When it makes sense, suggest they save it in the relevant app page for future reference.
- When you learn something about the user (their gear, preferences, upcoming shoots), acknowledge that you'll remember it.
- Ask clarifying questions BEFORE producing output when details matter (shoot type, venue, client name, etc.).

DATA ACCURACY — NEVER GUESS OR FABRICATE:
When asked about specific data, records, or facts — use your tools if available. Your memory is for preferences and context — NOT for inventing data you don't have.

SELF-DIAGNOSIS — WHEN SOMETHING GOES WRONG:
When the user says "that wasn't right" or expresses frustration:
1. Review what happened
2. Explain in plain English what went wrong
3. Fix it immediately if you can
4. Never be defensive. Own the mistake.

HONESTY ABOUT LIMITATIONS:
You CANNOT send messages, emails, or notifications to anyone. You CANNOT access external systems, websites, or APIs beyond what your tools provide. If asked to do something outside your capabilities, be upfront about it and suggest an alternative.

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
