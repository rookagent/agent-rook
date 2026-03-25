"""
Agent Rook — Self-managed memory tools.

The agent can manage its OWN memory through tool calls during conversation,
not just background extraction. Three tools:

1. save_memory   — Agent decides to remember something important
2. search_memory — Agent searches what it knows about the user
3. forget_memory — Agent removes a memory (user asked to forget something)

These are appended to the tool registry and dispatched alongside other tools.
Memory tools should NEVER crash the chat — all errors are caught and returned
as friendly messages.
"""
import logging
from datetime import datetime

import pytz
from sqlalchemy import text as sa_text

from app.models.agent_memory import AgentMemory
from app.extensions import db

logger = logging.getLogger(__name__)

# Eastern timezone for all timestamps
_ET = pytz.timezone('US/Eastern')

# Importance → confidence mapping
_IMPORTANCE_MAP = {
    'high': 0.95,
    'medium': 0.85,
    'low': 0.7,
}


# ---------------------------------------------------------------------------
# Tool Definitions (Claude tool_use format)
# ---------------------------------------------------------------------------

MEMORY_TOOL_DEFINITIONS = [
    {
        'name': 'save_memory',
        'description': (
            'Save something important you learned about the user to your long-term memory. '
            'Use this when the user shares a preference, personal fact, or goal that you '
            'should remember across conversations. Do NOT save trivial things like greetings. '
            'Only save what the USER told you — never save your own suggestions.'
        ),
        'input_schema': {
            'type': 'object',
            'properties': {
                'content': {
                    'type': 'string',
                    'description': (
                        'What to remember, in your own words. Keep it concise and specific. '
                        'Good: "Prefers bullet points over paragraphs". '
                        'Bad: "The user said they like bullet points and also sometimes paragraphs '
                        'but mostly bullet points when reading summaries".'
                    ),
                },
                'type': {
                    'type': 'string',
                    'enum': ['preference', 'fact', 'goal'],
                    'description': (
                        'preference = how the user likes things done. '
                        'fact = something true about the user (job, location, tools). '
                        'goal = something the user is working toward.'
                    ),
                },
                'category': {
                    'type': 'string',
                    'description': (
                        'A short grouping label: workflow, tools, personal, professional, '
                        'communication, schedule, project, or any other relevant category.'
                    ),
                },
                'importance': {
                    'type': 'string',
                    'enum': ['high', 'medium', 'low'],
                    'description': (
                        'high = core identity or strong preference (always relevant). '
                        'medium = useful context (relevant in some conversations). '
                        'low = minor detail (nice to know, not critical).'
                    ),
                },
            },
            'required': ['content', 'type', 'category', 'importance'],
        },
    },
    {
        'name': 'search_memory',
        'description': (
            'Search your long-term memory for what you know about the user. '
            'Use this when you need to recall something specific — a preference, '
            'a fact they shared, or a goal they mentioned in a previous conversation. '
            'Returns matching memories ranked by relevance.'
        ),
        'input_schema': {
            'type': 'object',
            'properties': {
                'query': {
                    'type': 'string',
                    'description': (
                        'What to search for. Can be a topic, keyword, or natural phrase. '
                        'Examples: "programming language", "work schedule", "communication style".'
                    ),
                },
                'type': {
                    'type': 'string',
                    'enum': ['preference', 'fact', 'goal'],
                    'description': 'Optional: filter results to a specific memory type.',
                },
            },
            'required': ['query'],
        },
    },
    {
        'name': 'forget_memory',
        'description': (
            'Remove a memory about the user. Use this when the user explicitly asks '
            'you to forget something, or when information is outdated and they correct it. '
            'Finds the closest matching memory and deactivates it (soft delete).'
        ),
        'input_schema': {
            'type': 'object',
            'properties': {
                'query': {
                    'type': 'string',
                    'description': (
                        'Describe the memory to forget. Will find the closest match. '
                        'Examples: "my old job", "that I prefer dark mode", "my Python version".'
                    ),
                },
            },
            'required': ['query'],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool Executors
# ---------------------------------------------------------------------------

def _execute_save_memory(params, user):
    """Save a memory about the user. Deduplicates via pg_trgm similarity."""
    content = (params.get('content') or '').strip()
    if not content:
        return 'Nothing to save — content was empty.'

    if len(content) > 500:
        content = content[:500]

    mem_type = params.get('type', 'fact')
    if mem_type not in ('preference', 'fact', 'goal'):
        mem_type = 'fact'

    category = (params.get('category') or 'general').strip()[:50]
    importance = params.get('importance', 'medium')
    confidence = _IMPORTANCE_MAP.get(importance, 0.85)

    try:
        saved = AgentMemory.save_memories_from_session(
            memories_list=[{
                'type': mem_type,
                'content': content,
                'category': category,
                'confidence': confidence,
            }],
            user_id=user.id,
        )

        if saved:
            mem = saved[0]
            if mem.times_reinforced > 1:
                return (
                    f'Memory reinforced (seen {mem.times_reinforced} times): "{content}" '
                    f'[{mem_type}, {category}]'
                )
            else:
                return (
                    f'Saved to memory: "{content}" '
                    f'[{mem_type}, {category}, {importance} importance]'
                )
        else:
            return f'Memory saved: "{content}"'

    except Exception as e:
        logger.error(f"save_memory failed for user {user.id}: {e}", exc_info=True)
        db.session.rollback()
        return f'I tried to save that to memory but hit an error. I\'ll remember it for this conversation at least.'


def _execute_search_memory(params, user):
    """Search memories using pg_trgm similarity. Falls back to ILIKE if pg_trgm unavailable."""
    query = (params.get('query') or '').strip()
    if not query:
        return 'No search query provided.'

    mem_type_filter = params.get('type')
    limit = 10

    try:
        # Try pg_trgm similarity search first (threshold 0.3 for search — looser than dedup's 0.6)
        base_filters = [
            AgentMemory.user_id == user.id,
            AgentMemory.is_active == True,  # noqa: E712
        ]
        if mem_type_filter and mem_type_filter in ('preference', 'fact', 'goal'):
            base_filters.append(AgentMemory.memory_type == mem_type_filter)

        try:
            results = (
                AgentMemory.query
                .filter(*base_filters)
                .filter(sa_text("similarity(content, :query) > 0.3"))
                .params(query=query)
                .order_by(sa_text("similarity(content, :query) DESC"))
                .params(query=query)
                .limit(limit)
                .all()
            )
        except Exception:
            # pg_trgm not available — fall back to ILIKE
            db.session.rollback()
            like_pattern = f'%{query}%'
            results = (
                AgentMemory.query
                .filter(*base_filters)
                .filter(AgentMemory.content.ilike(like_pattern))
                .order_by(AgentMemory.confidence.desc(), AgentMemory.last_reinforced.desc())
                .limit(limit)
                .all()
            )

        if not results:
            type_clause = f' (type: {mem_type_filter})' if mem_type_filter else ''
            return f'No memories found matching "{query}"{type_clause}.'

        lines = [f'Found {len(results)} matching memories:\n']
        for i, mem in enumerate(results, 1):
            reinforced = f' (reinforced {mem.times_reinforced}x)' if mem.times_reinforced > 1 else ''
            created = ''
            if mem.created_at:
                created = f' — saved {mem.created_at.strftime("%b %d, %Y")}'
            lines.append(
                f'{i}. [{mem.memory_type}] {mem.content}{reinforced}{created}'
            )

        return '\n'.join(lines)

    except Exception as e:
        logger.error(f"search_memory failed for user {user.id}: {e}", exc_info=True)
        db.session.rollback()
        return 'Memory search hit an error. Try a different query.'


def _execute_forget_memory(params, user):
    """Find the closest matching memory and soft-delete it."""
    query = (params.get('query') or '').strip()
    if not query:
        return 'No query provided — I need to know what to forget.'

    try:
        # Find best match using pg_trgm similarity
        best_match = None
        try:
            best_match = (
                AgentMemory.query
                .filter(
                    AgentMemory.user_id == user.id,
                    AgentMemory.is_active == True,  # noqa: E712
                )
                .filter(sa_text("similarity(content, :query) > 0.2"))
                .params(query=query)
                .order_by(sa_text("similarity(content, :query) DESC"))
                .params(query=query)
                .first()
            )
        except Exception:
            # pg_trgm not available — fall back to ILIKE
            db.session.rollback()
            like_pattern = f'%{query}%'
            best_match = (
                AgentMemory.query
                .filter(
                    AgentMemory.user_id == user.id,
                    AgentMemory.is_active == True,  # noqa: E712
                    AgentMemory.content.ilike(like_pattern),
                )
                .order_by(AgentMemory.confidence.desc())
                .first()
            )

        if not best_match:
            return f'No memory found matching "{query}". Nothing to forget.'

        # Soft delete
        forgotten_content = best_match.content
        best_match.is_active = False
        best_match.confidence = 0.0
        best_match.updated_at = datetime.now(_ET)
        db.session.commit()

        # Invalidate cache so the forgotten memory disappears from prompts immediately
        from app.models.agent_memory import _invalidate_cache
        _invalidate_cache(user_id=user.id)

        logger.info(
            f"Memory forgotten for user {user.id}: "
            f"[{best_match.memory_type}] {forgotten_content[:80]}"
        )
        return f'Forgotten: "{forgotten_content}" — I won\'t bring this up again.'

    except Exception as e:
        logger.error(f"forget_memory failed for user {user.id}: {e}", exc_info=True)
        db.session.rollback()
        return 'Hit an error trying to forget that. The memory may still be active.'


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_TOOL_EXECUTORS = {
    'save_memory': _execute_save_memory,
    'search_memory': _execute_search_memory,
    'forget_memory': _execute_forget_memory,
}


def execute_memory_tool(tool_name, params, user):
    """
    Dispatch a memory tool call to the right executor.

    Args:
        tool_name: One of 'save_memory', 'search_memory', 'forget_memory'
        params: Dict of tool parameters from Claude's tool_use block
        user: The User model instance (must have .id)

    Returns:
        str: Human-readable result message for the agent to relay to the user.
             Never raises — all errors are caught and returned as messages.
    """
    executor = _TOOL_EXECUTORS.get(tool_name)
    if not executor:
        return f'Unknown memory tool: {tool_name}'

    try:
        return executor(params, user)
    except Exception as e:
        logger.error(
            f"Memory tool {tool_name} crashed for user {user.id}: {e}",
            exc_info=True,
        )
        db.session.rollback()
        return f'Memory tool error — this won\'t affect our conversation, but the operation didn\'t complete.'
