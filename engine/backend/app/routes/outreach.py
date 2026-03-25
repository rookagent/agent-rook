"""
Agent Rook — Outreach routes (manual triggers for testing).

POST /api/outreach/briefing — Generate and send morning briefing for current user
POST /api/outreach/roundup — Generate and send weekly roundup for current user
GET  /api/outreach/preview/briefing — Preview briefing HTML without sending
GET  /api/outreach/preview/roundup — Preview roundup HTML without sending
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.user import User

outreach_bp = Blueprint('outreach', __name__)


@outreach_bp.route('/preview/briefing', methods=['GET'])
@jwt_required()
def preview_briefing():
    """Preview morning briefing without sending."""
    user = User.query.get(int(get_jwt_identity()))
    if not user:
        return jsonify(error="User not found"), 404

    from app.outreach.briefings import generate_morning_briefing
    result = generate_morning_briefing(user)

    if not result:
        return jsonify(message="Nothing to report today — no events or tasks due.")

    return jsonify(
        subject=result['subject'],
        html=result['html_body'],
    )


@outreach_bp.route('/preview/roundup', methods=['GET'])
@jwt_required()
def preview_roundup():
    """Preview weekly roundup without sending."""
    user = User.query.get(int(get_jwt_identity()))
    if not user:
        return jsonify(error="User not found"), 404

    from app.outreach.briefings import generate_weekly_roundup
    result = generate_weekly_roundup(user)

    if not result:
        return jsonify(message="Nothing to report this week.")

    return jsonify(
        subject=result['subject'],
        html=result['html_body'],
    )


@outreach_bp.route('/send/briefing', methods=['POST'])
@jwt_required()
def send_briefing():
    """Send morning briefing to current user."""
    user = User.query.get(int(get_jwt_identity()))
    if not user:
        return jsonify(error="User not found"), 404

    from app.outreach.briefings import generate_morning_briefing, send_email
    result = generate_morning_briefing(user)

    if not result:
        return jsonify(message="Nothing to report today.")

    sent = send_email(result['to_email'], result['subject'], result['html_body'])
    return jsonify(message="Briefing sent" if sent else "Briefing generated (email not configured)", subject=result['subject'])


@outreach_bp.route('/send/roundup', methods=['POST'])
@jwt_required()
def send_roundup():
    """Send weekly roundup to current user."""
    user = User.query.get(int(get_jwt_identity()))
    if not user:
        return jsonify(error="User not found"), 404

    from app.outreach.briefings import generate_weekly_roundup, send_email
    result = generate_weekly_roundup(user)

    if not result:
        return jsonify(message="Nothing to report this week.")

    sent = send_email(result['to_email'], result['subject'], result['html_body'])
    return jsonify(message="Roundup sent" if sent else "Roundup generated (email not configured)", subject=result['subject'])
