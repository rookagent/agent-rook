"""
Agent Rook — Chat engine core.

The tool dispatch loop: sends messages to Claude, handles tool_use responses,
executes tools, feeds results back, repeats up to 3 rounds.

This is the heart of the framework — extracted from Daisy's provider_chat.py
and genericized for any domain.
"""
import json
import logging
import importlib

from app.utils.ai_client import ai_complete, MODEL_FAST, MODEL_SMART
from .routing import is_simple_query
from .access import check_and_deduct_access
from .prompts import build_system_prompt

logger = logging.getLogger(__name__)

# ── Tool Registry ──
# Built at startup from agent.yaml. Maps tool_name → executor function.
_tool_registry = {}
_tool_definitions = []
_knowledge_tool_names = set()


def register_tools(app):
    """
    Read tool definitions from agent.yaml and build the registry.
    Called once at app startup.
    """
    global _tool_registry, _tool_definitions, _knowledge_tool_names
    from config.settings import Config, AGENT_CONFIG

    tools_config = AGENT_CONFIG.get('tools', [])

    for tool_conf in tools_config:
        name = tool_conf['name']
        is_knowledge = tool_conf.get('knowledge_tool', False)

        if name == 'knowledge_base':
            # Built-in knowledge base tool
            _tool_definitions.append({
                'name': 'knowledge_base',
                'description': 'Search the knowledge library for information.',
                'input_schema': {
                    'type': 'object',
                    'properties': {
                        'query': {'type': 'string', 'description': 'What to search for'},
                    },
                    'required': ['query'],
                },
            })
            _knowledge_tool_names.add('knowledge_base')
            continue

        # Custom tools — load from module path
        if 'module' in tool_conf and 'function' in tool_conf:
            try:
                mod = importlib.import_module(tool_conf['module'])
                fn = getattr(mod, tool_conf['function'])
                _tool_registry[name] = fn
            except Exception as e:
                logger.error(f"Failed to load tool '{name}': {e}")
                continue

        # Build tool definition for Claude
        schema = tool_conf.get('schema', {
            'type': 'object',
            'properties': {'action': {'type': 'string'}},
        })
        _tool_definitions.append({
            'name': name,
            'description': tool_conf.get('description', f'Tool: {name}'),
            'input_schema': schema,
        })

        if is_knowledge:
            _knowledge_tool_names.add(name)

    logger.info(f"Registered {len(_tool_definitions)} tools: {[t['name'] for t in _tool_definitions]}")


def _execute_tool(tool_name, tool_params, user):
    """
    Execute a single tool call. Routes to the appropriate executor.
    """
    # Built-in: knowledge base
    if tool_name == 'knowledge_base':
        return _execute_knowledge(tool_params)

    # Custom tools from registry
    if tool_name in _tool_registry:
        try:
            return _tool_registry[tool_name](tool_params, user=user)
        except Exception as e:
            logger.error(f"Tool '{tool_name}' failed: {e}")
            return f"Tool error: {str(e)}"

    return f"Unknown tool: {tool_name}"


def _execute_knowledge(params):
    """Execute the built-in knowledge base lookup."""
    from app.knowledge.router import get_router
    router = get_router()
    query = params.get('query', '')

    result = router.route_knowledge_query(query)
    if result:
        name, description, content = result
        return f"[Knowledge: {description}]\n\n{content}"

    return "No matching knowledge found. Try rephrasing your question, or I can answer from my general knowledge."


def chat(user, message, conversation_history=None):
    """
    Process a chat message through the full engine pipeline.

    Args:
        user: User model instance (for access control, memory).
        message: The user's message text.
        conversation_history: Optional list of prior messages.

    Returns:
        dict: {message, data, credits, remaining, access_type}
    """
    from config.settings import Config

    # ── Access check ──
    access = check_and_deduct_access(
        user,
        daily_limit=Config.FREE_MESSAGES_PER_DAY,
    )
    if not access['allowed']:
        return {
            'message': access['message'],
            'data': None,
            'credits': access.get('credits', 0),
            'remaining': access.get('remaining', 0),
            'access_type': access['access_type'],
            'limit_reached': True,
        }

    # ── Model selection ──
    model = MODEL_FAST if is_simple_query(message) else MODEL_SMART

    # ── Build conversation ──
    messages = []
    if conversation_history:
        messages = conversation_history[-Config.CHAT_MAX_HISTORY:]
    messages.append({'role': 'user', 'content': message})

    # ── System prompt ──
    system_prompt = build_system_prompt(user)

    # ── Tools (only for smart model) ──
    tools = _tool_definitions if model == MODEL_SMART and _tool_definitions else None

    # ── Initial API call ──
    try:
        response = ai_complete(
            messages=messages,
            system=system_prompt,
            model=model,
            max_tokens=Config.AI_MAX_TOKENS,
            tools=tools,
            cache_system=True,
            context="Agent chat",
        )
    except Exception as e:
        logger.error(f"AI call failed: {e}")
        return {
            'message': f"I'm having trouble right now. Please try again in a moment.",
            'data': None,
            'credits': access.get('credits', 0),
            'remaining': access.get('remaining', 0),
            'access_type': access['access_type'],
        }

    # ── Tool dispatch loop (max 3 rounds) ──
    assistant_message = ""
    response_data = None
    current_messages = list(messages)
    current_response = response
    tools_used = []

    for _round in range(3):
        tool_used = False

        # Collect text blocks
        for block in current_response.content:
            if block.type == 'text':
                assistant_message += block.text

        # Handle tool_use blocks
        tool_blocks = [b for b in current_response.content if b.type == 'tool_use']
        tool_used = len(tool_blocks) > 0

        if tool_used:
            tool_results = []

            for block in tool_blocks:
                tool_name = block.name
                tool_params = block.input
                tools_used.append(tool_name)

                # Execute the tool
                tool_result = _execute_tool(tool_name, tool_params, user)

                # Track last tool response as data
                response_data = {
                    'tool': tool_name,
                    'action': tool_params.get('action'),
                    'result': tool_result if isinstance(tool_result, (dict, list)) else None,
                }

                tool_results.append({
                    'type': 'tool_result',
                    'tool_use_id': block.id,
                    'content': str(tool_result),
                })

            # Feed results back to Claude
            current_messages = current_messages + [
                {'role': 'assistant', 'content': current_response.content},
                {'role': 'user', 'content': tool_results},
            ]

            # Cost optimization: use fast model for knowledge-only followups
            round_tools = {b.name for b in tool_blocks}
            followup_model = MODEL_FAST if round_tools.issubset(_knowledge_tool_names) else MODEL_SMART

            current_response = ai_complete(
                messages=current_messages,
                system=system_prompt,
                model=followup_model,
                max_tokens=Config.AI_MAX_TOKENS,
                tools=tools,
                context=f"Agent chat followup ({'fast' if followup_model == MODEL_FAST else 'smart'})",
            )

            # Reset for fresh response
            assistant_message = ""

        if not tool_used:
            break

    # Extract final text if empty
    if not assistant_message:
        for block in current_response.content:
            if block.type == 'text':
                assistant_message += block.text

    return {
        'message': assistant_message,
        'data': response_data,
        'credits': access.get('credits', 0),
        'remaining': access.get('remaining', 0),
        'access_type': access['access_type'],
        'tools_used': tools_used,
    }
