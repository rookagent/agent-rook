"""
Agent Rook — Memory management API routes.

GET    /api/memories           — List all user memories
POST   /api/memories/extract   — Trigger extraction from conversation
PUT    /api/memories/<id>      — Edit a memory
DELETE /api/memories/<id>      — Delete a single memory
POST   /api/memories/purge     — Soft-delete all memories
GET    /api/memories/export    — Export all memories as JSON
"""
import logging
from datetime import datetime

import pytz
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db, limiter
from app.models.user import User
from app.models.agent_memory import AgentMemory, _invalidate_cache
from app.chat.memory_extraction import (
    extract_and_save,
    write_through_memory,
)

logger = logging.getLogger(__name__)

memories_bp = Blueprint('memories', __name__)


def _user_now(user):
    """Get current time in user's timezone."""
    tz_name = getattr(user, 'timezone', None) or 'US/Eastern'
    try:
        tz = pytz.timezone(tz_name)
    except pytz.UnknownTimeZoneError:
        tz = pytz.timezone('US/Eastern')
    return datetime.now(tz)


@memories_bp.route('', methods=['GET'])
@jwt_required()
def list_memories():
    """List all active memories for the current user."""
    user_id = int(get_jwt_identity())

    memories = AgentMemory.query.filter_by(
        user_id=user_id,
        is_active=True,
    ).order_by(
        AgentMemory.confidence.desc(),
        AgentMemory.last_reinforced.desc(),
    ).all()

    return jsonify(memories=[{
        'id': m.id,
        'type': m.memory_type,
        'content': m.content,
        'category': m.category,
        'confidence': round(m.confidence, 2),
        'times_reinforced': m.times_reinforced,
        'created_at': m.created_at.isoformat() if m.created_at else None,
        'last_reinforced': m.last_reinforced.isoformat() if m.last_reinforced else None,
    } for m in memories])


@memories_bp.route('/extract', methods=['POST'])
@jwt_required()
@limiter.limit("10 per hour")
def extract_memories():
    """
    Trigger memory extraction from a conversation.
    Called by frontend when a chat session ends (inactivity or page unload).

    Request body:
        {"messages": [{role, content}, ...]}
    """
    user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data or not data.get('messages'):
        return jsonify(error="messages array is required"), 400

    messages = data['messages']
    if len(messages) < 2:
        return jsonify(extracted=0, saved=0)

    result = extract_and_save(user_id, messages)
    return jsonify(**result)


@memories_bp.route('/<int:memory_id>', methods=['PUT'])
@jwt_required()
def edit_memory(memory_id):
    """Edit a memory's content."""
    user_id = int(get_jwt_identity())

    memory = AgentMemory.query.filter_by(
        id=memory_id,
        user_id=user_id,
        is_active=True,
    ).first()

    if not memory:
        return jsonify(error="Memory not found"), 404

    data = request.get_json()
    if not data or not data.get('content', '').strip():
        return jsonify(error="content is required"), 400

    memory.content = data['content'].strip()[:250]
    if data.get('category'):
        memory.category = data['category']

    # Invalidate cache
    _invalidate_cache(user_id=user_id)

    db.session.commit()
    return jsonify(success=True)


@memories_bp.route('/<int:memory_id>', methods=['DELETE'])
@jwt_required()
def delete_memory(memory_id):
    """Soft-delete a single memory."""
    user_id = int(get_jwt_identity())

    memory = AgentMemory.query.filter_by(
        id=memory_id,
        user_id=user_id,
        is_active=True,
    ).first()

    if not memory:
        return jsonify(error="Memory not found"), 404

    memory.is_active = False
    memory.confidence = 0.0

    # Invalidate cache
    _invalidate_cache(user_id=user_id)

    db.session.commit()
    return jsonify(success=True)


@memories_bp.route('/purge', methods=['POST'])
@jwt_required()
def purge_memories():
    """Soft-delete ALL memories for the current user. Requires confirmation."""
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    if not data.get('confirm'):
        return jsonify(error="Pass {confirm: true} to purge all memories"), 400

    count = AgentMemory.purge_all_memories(user_id=user_id)
    return jsonify(purged=count)


@memories_bp.route('/export', methods=['GET'])
@jwt_required()
def export_memories():
    """Export all memories as JSON download. Your data, your right."""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    now = _user_now(user)

    memories = AgentMemory.query.filter_by(
        user_id=user_id,
        is_active=True,
    ).order_by(AgentMemory.created_at.asc()).all()

    export = {
        'exported_at': now.isoformat(),
        'user_email': user.email if user else None,
        'memory_count': len(memories),
        'memories': [{
            'type': m.memory_type,
            'content': m.content,
            'category': m.category,
            'confidence': round(m.confidence, 2),
            'times_reinforced': m.times_reinforced,
            'created_at': m.created_at.isoformat() if m.created_at else None,
            'last_reinforced': m.last_reinforced.isoformat() if m.last_reinforced else None,
        } for m in memories],
    }

    response = jsonify(export)
    response.headers['Content-Disposition'] = 'attachment; filename=my-memories.json'
    return response
