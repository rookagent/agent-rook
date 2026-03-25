"""
Agent Rook — Memory extraction from conversations.

Three layers (from Daisy's battle-tested architecture):
1. Write-through: Real-time keyword catch for critical facts (10ms, no LLM)
2. Session-end: Full conversation sent to fast model for structured extraction
3. Regex fallback: If LLM fails, keyword patterns catch the basics

Extraction categories are config-driven from agent.yaml.
"""
import re
import json
import logging
from datetime import datetime

import pytz
from sqlalchemy import text as sa_text

from app.utils.ai_client import ai_complete_json, MODEL_FAST
from app.models.agent_memory import AgentMemory
from app.extensions import db

logger = logging.getLogger(__name__)


# ── Layer 1: Write-Through (Real-Time, No LLM) ──

# Patterns that MUST be caught immediately, not deferred to session end.
WRITE_THROUGH_PATTERNS = [
    # Explicit memory requests (highest priority)
    (r'\b(?:remember|don\'?t forget|keep in mind|note that|save this)\b',
     'preference', 'user_stated', 0.95),
    # Location declarations
    (r'\b(?:i\'?m (?:in|from|based in|located in)|my (?:city|state|country) is)\b',
     'fact', 'location', 0.95),
    # Capacity / team size
    (r'\b(?:we (?:have|serve|manage|handle)|my team (?:is|has)|i work with)\s+\d+',
     'fact', 'operational', 0.9),
    # Goal declarations
    (r'\b(?:i\'?m (?:trying to|working on|learning|studying)|my goal is|i want to)\b',
     'goal', 'professional', 0.9),
    # Tool / tech declarations
    (r'\b(?:i use|we use|i work with|our stack|i prefer)\b',
     'preference', 'tools', 0.9),
]


def write_through_memory(user_id, user_message):
    """
    Layer 1: Scan message for must-save patterns. No LLM call.
    Called in real-time during conversation (~10ms).
    """
    if not user_message or len(user_message) < 15:
        return

    msg_lower = user_message.lower()

    for pattern, mem_type, category, confidence in WRITE_THROUGH_PATTERNS:
        if re.search(pattern, msg_lower):
            # Truncate to 250 chars
            content = user_message[:250].strip()
            AgentMemory.save_memories_from_session(
                memories_list=[{
                    'type': mem_type,
                    'content': content,
                    'category': category,
                    'confidence': confidence,
                }],
                user_id=user_id,
            )
            logger.info(f"Write-through memory saved for user {user_id}: {category}")
            return  # One match per message to avoid spam


# ── Layer 2: Session-End LLM Extraction ──

def extract_memories_from_conversation(user_id, conversation_messages):
    """
    Layer 2: Send full conversation to fast model for structured extraction.
    Called when a chat session ends (frontend detects inactivity or page unload).

    Args:
        user_id: The user's ID
        conversation_messages: List of {role, content} dicts from the conversation

    Returns:
        list: Extracted memories (dicts with type, content, category, confidence)
    """
    from config.settings import Config, AGENT_CONFIG

    if not conversation_messages or len(conversation_messages) < 2:
        return []

    # Build conversation transcript
    transcript_lines = []
    for msg in conversation_messages:
        role = msg.get('role', 'user').upper()
        content = msg.get('content', '')
        if isinstance(content, str) and content.strip():
            transcript_lines.append(f"{role}: {content}")
        elif isinstance(content, list):
            # Handle structured content blocks
            text_parts = [b.get('text', '') for b in content if isinstance(b, dict) and b.get('type') == 'text']
            if text_parts:
                transcript_lines.append(f"{role}: {' '.join(text_parts)}")

    transcript = '\n'.join(transcript_lines[-40:])  # Cap at 40 exchanges

    if len(transcript) < 30:
        return []

    # Get extraction categories from config
    categories = AGENT_CONFIG.get('memory', {}).get('extraction_categories', [
        'preferences', 'facts', 'goals', 'schedule', 'personal',
    ])
    agent_name = Config.AGENT_NAME

    extraction_prompt = f"""Analyze this conversation and extract key things you learned about the USER.

RULES:
- Only extract facts explicitly stated by the USER, not suggestions made by {agent_name}
- Keep each memory under 200 characters
- Categorize each memory accurately
- Do NOT extract greetings, thank-yous, or trivial exchanges
- Do NOT extract anything {agent_name} said — only what the USER shared
- If user corrected earlier information, use the CORRECTED version only
- For schedule/timing info, capture the full context ("Works Mon-Fri 9-5" not just "9-5")

CATEGORIES: {', '.join(categories)}

CONVERSATION:
{transcript}

Return a JSON array of extracted memories. Each item:
{{"type": "preference|fact|goal|interaction", "content": "what you learned", "category": "one of the categories above", "confidence": 0.7-0.95}}

If nothing worth remembering was said, return an empty array: []
"""

    try:
        result = ai_complete_json(
            prompt=extraction_prompt,
            system="You extract structured facts from conversations. Return valid JSON only.",
            model=MODEL_FAST,
            max_tokens=500,
            context="Memory extraction",
        )

        if isinstance(result, list):
            memories = []
            for item in result:
                if isinstance(item, dict) and item.get('content'):
                    memories.append({
                        'type': item.get('type', 'fact'),
                        'content': str(item['content'])[:250],
                        'category': item.get('category', 'general'),
                        'confidence': min(float(item.get('confidence', 0.8)), 0.95),
                    })
            return memories

        return []

    except Exception as e:
        logger.warning(f"LLM extraction failed, falling back to regex: {e}")
        return extract_memories_regex(conversation_messages)


# ── Layer 3: Regex Fallback ──

# Patterns for when LLM extraction fails
REGEX_PATTERNS = [
    (r'(?:i use|we use|i prefer|our stack is)\s+(.{5,80})', 'preference', 'tools'),
    (r'(?:i\'?m (?:in|from|based in))\s+(.{3,50})', 'fact', 'location'),
    (r'(?:my (?:name|business|company|shop) is)\s+(.{3,60})', 'fact', 'personal'),
    (r'(?:i have|we have|i manage)\s+(\d+\s+\w+)', 'fact', 'operational'),
    (r'(?:i\'?m (?:trying to|learning|studying|working on))\s+(.{5,80})', 'goal', 'professional'),
    (r'(?:every|each)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|morning|evening|week)\s+(.{5,60})',
     'fact', 'schedule'),
    (r'(?:i (?:like|love|enjoy|prefer))\s+(.{5,60})', 'preference', 'personal'),
    (r'(?:i (?:don\'?t|hate|dislike|avoid))\s+(.{5,60})', 'preference', 'personal'),
]


def extract_memories_regex(conversation_messages):
    """
    Layer 3: Regex-based extraction when LLM fails.
    Catches common patterns but less nuanced than LLM extraction.
    """
    memories = []
    seen = set()

    for msg in conversation_messages:
        if msg.get('role') != 'user':
            continue
        content = msg.get('content', '')
        if isinstance(content, list):
            content = ' '.join(b.get('text', '') for b in content if isinstance(b, dict))
        if not content or len(content) < 15:
            continue

        content_lower = content.lower()

        for pattern, mem_type, category in REGEX_PATTERNS:
            match = re.search(pattern, content_lower)
            if match:
                extracted = match.group(1).strip() if match.lastindex else content[:200]
                if extracted not in seen and len(extracted) > 4:
                    seen.add(extracted)
                    memories.append({
                        'type': mem_type,
                        'content': extracted[:250],
                        'category': category,
                        'confidence': 0.7,
                    })

    return memories[:10]  # Cap at 10 regex extractions per session


# ── 4-Way Memory Classification Pipeline ──

def _find_similar_memories(content, user_id, threshold=0.3, limit=3):
    """
    Find the top N most similar existing memories using pg_trgm.
    Returns list of AgentMemory objects, or empty list if pg_trgm unavailable.
    """
    try:
        results = (
            AgentMemory.query
            .filter(
                AgentMemory.user_id == user_id,
                AgentMemory.is_active == True,
                sa_text("similarity(content, :new_content) > :threshold"),
            )
            .params(new_content=content, threshold=threshold)
            .order_by(sa_text("similarity(content, :new_content) DESC"))
            .params(new_content=content)
            .limit(limit)
            .all()
        )
        return results
    except Exception as e:
        logger.debug(f"pg_trgm similarity query failed (expected if not installed): {e}")
        db.session.rollback()
        return []


def classify_memory_action(new_content, similar_memories, ai_complete_func=None):
    """
    Classify whether a new memory should be ADDed, UPDATE an existing one,
    DELETE an existing one, or be skipped (NOOP).

    Uses Haiku (MODEL_FAST) to make the decision when similar memories exist.

    Args:
        new_content: The new memory candidate text
        similar_memories: List of AgentMemory objects (top 3 most similar)
        ai_complete_func: Optional override for the LLM call (for testing).
                          Defaults to ai_complete_json with MODEL_FAST.

    Returns:
        dict with {action: 'ADD'|'UPDATE'|'DELETE'|'NOOP', target_id: int|None, reason: str}
    """
    if not similar_memories:
        return {'action': 'ADD', 'target_id': None, 'reason': 'No similar memories found'}

    # Build the existing memories block for the prompt
    existing_lines = []
    valid_ids = set()
    for mem in similar_memories:
        existing_lines.append(
            f"ID {mem.id}: {mem.content} (confidence: {mem.confidence})"
        )
        valid_ids.add(mem.id)

    existing_block = "\n".join(existing_lines)

    prompt = f"""You are a memory manager. A new fact has been learned:
"{new_content}"

Here are the most similar existing memories:
{existing_block}

Classify what to do:
- ADD: This is genuinely new information, save it
- UPDATE: This corrects or replaces an existing memory — specify which ID
- DELETE: This contradicts and invalidates an existing memory — specify which ID
- NOOP: This is already known, skip it

Return ONLY JSON: {{"action": "ADD|UPDATE|DELETE|NOOP", "target_id": null|<id>, "reason": "<brief reason>"}}"""

    call_func = ai_complete_func or ai_complete_json

    try:
        raw = call_func(
            prompt=prompt,
            model=MODEL_FAST,
            max_tokens=150,
            context="Memory classification",
        )

        # Parse the result — ai_complete_json returns a string
        if isinstance(raw, str):
            result = json.loads(raw)
        elif isinstance(raw, dict):
            result = raw
        else:
            raise ValueError(f"Unexpected response type: {type(raw)}")

        action = str(result.get('action', 'ADD')).upper()
        if action not in ('ADD', 'UPDATE', 'DELETE', 'NOOP'):
            action = 'ADD'

        target_id = result.get('target_id')

        # Validate target_id — must reference one of the similar memories
        if action in ('UPDATE', 'DELETE') and target_id not in valid_ids:
            logger.warning(
                f"Classification returned target_id={target_id} not in similar set "
                f"{valid_ids}, falling back to ADD"
            )
            action = 'ADD'
            target_id = None

        return {
            'action': action,
            'target_id': target_id,
            'reason': str(result.get('reason', ''))[:200],
        }

    except Exception as e:
        logger.warning(f"Memory classification failed, defaulting to ADD: {e}")
        return {'action': 'ADD', 'target_id': None, 'reason': f'Classification error: {e}'}


def _execute_memory_action(action_result, new_mem_data, user_id):
    """
    Execute the classified action on a single memory candidate.

    Returns:
        str: What happened — 'added', 'updated', 'deleted', 'skipped', 'reinforced'
    """
    action = action_result['action']
    target_id = action_result.get('target_id')
    content = new_mem_data.get('content', '').strip()

    if action == 'ADD':
        memory = AgentMemory(
            user_id=user_id,
            memory_type=new_mem_data.get('type', 'fact'),
            content=content,
            category=new_mem_data.get('category'),
            confidence=new_mem_data.get('confidence', 0.8),
        )
        db.session.add(memory)
        return 'added'

    elif action == 'UPDATE' and target_id:
        target = AgentMemory.query.get(target_id)
        if target and target.user_id == user_id and target.is_active:
            target.content = content
            target.reinforce()
            return 'updated'
        else:
            # Target not found or doesn't belong to user — fall back to ADD
            memory = AgentMemory(
                user_id=user_id,
                memory_type=new_mem_data.get('type', 'fact'),
                content=content,
                category=new_mem_data.get('category'),
                confidence=new_mem_data.get('confidence', 0.8),
            )
            db.session.add(memory)
            return 'added'

    elif action == 'DELETE' and target_id:
        target = AgentMemory.query.get(target_id)
        if target and target.user_id == user_id and target.is_active:
            target.is_active = False
            target.confidence = 0.0
            return 'deleted'
        return 'skipped'

    elif action == 'NOOP':
        # Reinforce the most similar existing memory
        if target_id:
            target = AgentMemory.query.get(target_id)
            if target and target.user_id == user_id and target.is_active:
                target.reinforce()
                return 'reinforced'
        return 'skipped'

    return 'skipped'


# ── Save Extracted Memories ──

def save_extracted_memories(user_id, memories):
    """
    Save a list of extracted memories using the 4-way classification pipeline.

    For each memory candidate:
    1. Query top 3 similar memories (pg_trgm, threshold 0.3)
    2. If no similar memories → ADD directly (no LLM call, saves money)
    3. If similar memories exist → classify via Haiku (ADD/UPDATE/DELETE/NOOP)
    4. Execute the classified action

    Falls back to simple dedup (save_memories_from_session) if classification
    errors out — the pipeline is an enhancement, not a gate.

    Returns:
        int: Number of memories added, updated, or reinforced
    """
    if not memories:
        return 0

    actions_taken = {'added': 0, 'updated': 0, 'deleted': 0, 'reinforced': 0, 'skipped': 0}

    try:
        for mem_data in memories:
            content = mem_data.get('content', '').strip()
            if not content:
                continue

            # Step 1: Find similar existing memories
            similar = _find_similar_memories(content, user_id, threshold=0.3, limit=3)

            if not similar:
                # Step 2: No similar memories — ADD directly, skip LLM call
                memory = AgentMemory(
                    user_id=user_id,
                    memory_type=mem_data.get('type', 'fact'),
                    content=content,
                    category=mem_data.get('category'),
                    confidence=mem_data.get('confidence', 0.8),
                )
                db.session.add(memory)
                actions_taken['added'] += 1
            else:
                # Step 3: Similar memories found — classify via Haiku
                try:
                    action_result = classify_memory_action(content, similar)
                    result = _execute_memory_action(action_result, mem_data, user_id)
                    actions_taken[result] += 1
                    logger.debug(
                        f"Memory classification: {action_result['action']} "
                        f"(reason: {action_result.get('reason', 'n/a')})"
                    )
                except Exception as e:
                    # Classification failed — fall back to old dedup behavior
                    # similarity > 0.6 = reinforce, else save new
                    logger.warning(f"Classification pipeline error, using fallback dedup: {e}")
                    high_sim = _find_similar_memories(content, user_id, threshold=0.6, limit=1)
                    if high_sim:
                        high_sim[0].reinforce()
                        actions_taken['reinforced'] += 1
                    else:
                        memory = AgentMemory(
                            user_id=user_id,
                            memory_type=mem_data.get('type', 'fact'),
                            content=content,
                            category=mem_data.get('category'),
                            confidence=mem_data.get('confidence', 0.8),
                        )
                        db.session.add(memory)
                        actions_taken['added'] += 1

        db.session.commit()

        total = actions_taken['added'] + actions_taken['updated'] + actions_taken['reinforced']
        logger.info(
            f"Memory pipeline for user {user_id}: "
            f"{actions_taken['added']} added, {actions_taken['updated']} updated, "
            f"{actions_taken['deleted']} deleted, {actions_taken['reinforced']} reinforced, "
            f"{actions_taken['skipped']} skipped"
        )
        return total

    except Exception as e:
        logger.error(f"Memory pipeline failed for user {user_id}, falling back to bulk save: {e}")
        db.session.rollback()
        # Full fallback — use the original simple dedup method
        try:
            saved = AgentMemory.save_memories_from_session(
                memories_list=memories,
                user_id=user_id,
            )
            count = len(saved) if saved else 0
            logger.info(f"Fallback save: {count} memories for user {user_id}")
            return count
        except Exception as e2:
            logger.error(f"Fallback save also failed for user {user_id}: {e2}")
            db.session.rollback()
            return 0


# ── Full Extraction Pipeline ──

def extract_and_save(user_id, conversation_messages):
    """
    Run the full extraction pipeline and save results.
    Called from the memory API endpoint when a session ends.

    Returns:
        dict: {extracted: int, saved: int}
    """
    memories = extract_memories_from_conversation(user_id, conversation_messages)
    saved = save_extracted_memories(user_id, memories)
    return {'extracted': len(memories), 'saved': saved}
