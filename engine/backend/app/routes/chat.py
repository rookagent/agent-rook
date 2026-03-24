"""
Agent Rook — Chat API routes.

POST /api/chat — Send a message, get a response (with tool use).
"""
import logging

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import limiter
from app.models.user import User
from app.chat.engine import chat

logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('', methods=['POST'])
@jwt_required()
@limiter.limit("30 per minute")
def send_message():
    """
    Process a chat message through the Agent Rook engine.

    Request body:
        {
            "message": "Plan this week's meals",
            "history": [...]  // optional conversation history
        }

    Response:
        {
            "message": "Here's your meal plan...",
            "data": {...},  // tool response data if any
            "credits": 249,
            "remaining": 249,
            "access_type": "credits"
        }
    """
    data = request.get_json()
    if not data or not data.get('message', '').strip():
        return jsonify(error="Message is required"), 400

    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user:
        return jsonify(error="User not found"), 404

    message = data['message'].strip()
    history = data.get('history', [])

    # Truncate message length
    if len(message) > 2000:
        message = message[:2000]

    result = chat(user, message, conversation_history=history)

    status = 200
    if result.get('limit_reached'):
        status = 429

    return jsonify(result), status
