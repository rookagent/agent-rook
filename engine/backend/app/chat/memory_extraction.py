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


# ── Save Extracted Memories ──

def save_extracted_memories(user_id, memories):
    """
    Save a list of extracted memories, handling dedup via the model's
    save_memories_from_session() which uses pg_trgm fuzzy matching.

    Returns:
        int: Number of memories saved (new or reinforced)
    """
    if not memories:
        return 0

    try:
        saved = AgentMemory.save_memories_from_session(
            memories_list=memories,
            user_id=user_id,
        )
        count = len(saved) if saved else 0
        logger.info(f"Saved {count} memories for user {user_id}")
        return count
    except Exception as e:
        logger.error(f"Failed to save memories for user {user_id}: {e}")
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
