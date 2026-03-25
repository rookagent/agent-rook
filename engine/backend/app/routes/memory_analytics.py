"""
Agent Rook — Memory analytics and consolidation API routes.

GET  /api/memories/analytics    — Aggregated memory stats for the user
POST /api/memories/consolidate  — AI-powered memory consolidation by category
"""
import logging
from collections import defaultdict
from datetime import datetime, timedelta

import pytz
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func

from app.extensions import db, limiter
from app.models.user import User
from app.models.agent_memory import AgentMemory, _invalidate_cache

logger = logging.getLogger(__name__)

memory_analytics_bp = Blueprint('memory_analytics', __name__)


def _user_tz(user):
    """Resolve user timezone, falling back to US/Eastern."""
    tz_name = getattr(user, 'timezone', None) or 'US/Eastern'
    try:
        return pytz.timezone(tz_name)
    except pytz.UnknownTimeZoneError:
        return pytz.timezone('US/Eastern')


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/memories/analytics
# ──────────────────────────────────────────────────────────────────────────────

@memory_analytics_bp.route('', methods=['GET'])
@jwt_required()
def get_analytics():
    """Return aggregated memory statistics for the current user."""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify(error="User not found"), 404

    tz = _user_tz(user)
    now = datetime.now(tz)

    # Base query: all memories for this user (active and inactive)
    all_memories = AgentMemory.query.filter_by(user_id=user_id).all()
    active_memories = [m for m in all_memories if m.is_active]

    total = len(all_memories)
    active = len(active_memories)

    # --- Group by type ---
    by_type = defaultdict(int)
    for m in active_memories:
        by_type[m.memory_type or 'unknown'] += 1

    # --- Group by category ---
    by_category = defaultdict(int)
    for m in active_memories:
        by_category[m.category or 'uncategorized'] += 1

    # --- Confidence distribution ---
    confidence_dist = {'high': 0, 'medium': 0, 'low': 0, 'fading': 0}
    total_confidence = 0.0
    for m in active_memories:
        c = m.confidence or 0.0
        total_confidence += c
        if c >= 0.8:
            confidence_dist['high'] += 1
        elif c >= 0.5:
            confidence_dist['medium'] += 1
        elif c >= 0.2:
            confidence_dist['low'] += 1
        else:
            confidence_dist['fading'] += 1

    avg_confidence = round(total_confidence / active, 2) if active else 0.0

    # --- Most reinforced (top 5) ---
    most_reinforced = sorted(
        active_memories,
        key=lambda m: m.times_reinforced or 0,
        reverse=True,
    )[:5]
    most_reinforced_list = [
        {'content': m.content, 'times_reinforced': m.times_reinforced or 0}
        for m in most_reinforced
    ]

    # --- Date boundaries ---
    dates = [m.created_at for m in active_memories if m.created_at]
    oldest = min(dates).isoformat() if dates else None
    newest = max(dates).isoformat() if dates else None

    # --- Recency counts (week / month in user timezone) ---
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # Convert naive UTC datetimes to tz-aware for comparison
    utc = pytz.utc
    memories_this_week = 0
    memories_this_month = 0
    for m in active_memories:
        if not m.created_at:
            continue
        created_aware = utc.localize(m.created_at) if m.created_at.tzinfo is None else m.created_at
        created_local = created_aware.astimezone(tz)
        if created_local >= week_ago:
            memories_this_week += 1
        if created_local >= month_ago:
            memories_this_month += 1

    return jsonify(
        total_memories=total,
        active_memories=active,
        by_type=dict(by_type),
        by_category=dict(by_category),
        confidence_distribution=confidence_dist,
        avg_confidence=avg_confidence,
        most_reinforced=most_reinforced_list,
        oldest_memory=oldest,
        newest_memory=newest,
        memories_this_week=memories_this_week,
        memories_this_month=memories_this_month,
    )


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/memories/consolidate
# ──────────────────────────────────────────────────────────────────────────────

@memory_analytics_bp.route('/consolidate', methods=['POST'])
@jwt_required()
@limiter.limit("3 per day")
def consolidate_memories():
    """
    Hierarchical memory consolidation.

    For each category with 5+ active memories, call Haiku to produce a single
    summary. The summary is saved as a new 'consolidated' memory, and the
    originals are tagged (not deleted).
    """
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify(error="User not found"), 404

    # Fetch all active, non-consolidated memories
    active = AgentMemory.query.filter_by(
        user_id=user_id,
        is_active=True,
    ).filter(
        db.or_(
            AgentMemory.category != 'consolidated',
            AgentMemory.category.is_(None),
        )
    ).all()

    if not active:
        return jsonify(consolidated=0, categories=[], message="No memories to consolidate")

    # Group by category
    grouped = defaultdict(list)
    for m in active:
        grouped[m.category or 'uncategorized'].append(m)

    # Only consolidate categories with 5+ memories
    eligible = {cat: mems for cat, mems in grouped.items() if len(mems) >= 5}

    if not eligible:
        return jsonify(
            consolidated=0,
            categories=[],
            message="No categories have 5+ memories to consolidate",
        )

    # Import AI client lazily to avoid circular imports
    from app.utils.ai_client import ai_complete, MODEL_FAST

    consolidated_count = 0
    consolidated_categories = []
    errors = []

    for category, memories in eligible.items():
        # Build the consolidation prompt
        memory_lines = "\n".join(
            f"- {m.content}" for m in memories
        )
        prompt = (
            f"Here are {len(memories)} memories in the category '{category}'. "
            f"Create ONE concise summary (under 200 chars) that captures the key information:\n"
            f"{memory_lines}\n"
            f"Return just the summary text, nothing else."
        )

        try:
            response = ai_complete(
                messages=[{"role": "user", "content": prompt}],
                model=MODEL_FAST,
                max_tokens=300,
                temperature=0,
                context="memory_consolidation",
            )
            summary = response.content[0].text.strip()

            # Truncate to 250 chars as a safety net
            summary = summary[:250]

            if not summary:
                errors.append(f"Empty summary for category '{category}'")
                continue

            # Save consolidated memory
            consolidated_mem = AgentMemory(
                user_id=user_id,
                memory_type='fact',
                content=summary,
                category='consolidated',
                confidence=0.9,
                source_session=f"consolidation:{category}",
            )
            db.session.add(consolidated_mem)

            # Tag originals as consolidated (keep active, add source marker)
            for m in memories:
                if not m.source_session:
                    m.source_session = f"consolidated_into:{category}"
                else:
                    m.source_session = f"{m.source_session}|consolidated_into:{category}"

            consolidated_count += 1
            consolidated_categories.append({
                'category': category,
                'memories_merged': len(memories),
                'summary': summary,
            })

        except Exception as e:
            logger.error(f"Consolidation failed for category '{category}': {e}")
            errors.append(f"AI error for category '{category}': {str(e)}")
            continue

    if consolidated_count > 0:
        db.session.commit()
        _invalidate_cache(user_id=user_id)

    result = {
        'consolidated': consolidated_count,
        'categories': consolidated_categories,
    }
    if errors:
        result['errors'] = errors

    return jsonify(**result)
