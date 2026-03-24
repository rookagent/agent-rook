"""
Agent Rook — Authentication routes.

Simple email + password auth. No provider claiming, no license lookup.
JWT tokens for session management.
"""
import logging
import secrets
from datetime import datetime, timedelta

import pytz
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, get_jwt_identity, jwt_required,
)
from app.extensions import db, limiter
from app.models.user import User

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

# Use UTC explicitly via pytz (not bare datetime.utcnow)
_UTC = pytz.UTC


def _now_utc():
    """Get current UTC time (timezone-aware)."""
    return datetime.now(_UTC)


@auth_bp.route('/register', methods=['POST'])
@limiter.limit("5 per hour")
def register():
    """Register a new user account."""
    data = request.get_json()
    if not data:
        return jsonify(error="Request body required"), 400

    email = (data.get('email') or '').strip().lower()
    password = data.get('password', '')
    name = data.get('name', '').strip()
    timezone = data.get('timezone', 'US/Eastern')
    signup_source = data.get('source', 'direct')

    if not email or not password:
        return jsonify(error="Email and password are required"), 400

    if len(password) < 6:
        return jsonify(error="Password must be at least 6 characters"), 400

    if User.query.filter_by(email=email).first():
        return jsonify(error="An account with this email already exists"), 409

    user = User(
        email=email,
        role='user',
        verified=True,  # No email verification in v1
        timezone=timezone,
        signup_source=signup_source,
    )
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    token = create_access_token(
        identity=str(user.id),
        additional_claims={'role': user.role, 'email': user.email},
    )

    logger.info(f"New user registered: {email}")

    return jsonify(
        message="Account created successfully",
        token=token,
        user=user.to_dict(),
    ), 201


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    """Log in with email + password."""
    data = request.get_json()
    if not data:
        return jsonify(error="Request body required"), 400

    email = (data.get('email') or '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify(error="Email and password are required"), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify(error="Invalid email or password"), 401

    # Update last login in user's timezone
    tz_name = user.timezone or 'US/Eastern'
    try:
        tz = pytz.timezone(tz_name)
    except pytz.UnknownTimeZoneError:
        tz = pytz.timezone('US/Eastern')
    user.last_login = datetime.now(tz)
    db.session.commit()

    token = create_access_token(
        identity=str(user.id),
        additional_claims={'role': user.role, 'email': user.email},
    )

    return jsonify(token=token, user=user.to_dict())


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current authenticated user's profile."""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user:
        return jsonify(error="User not found"), 404

    return jsonify(user=user.to_dict())


@auth_bp.route('/password-reset/request', methods=['POST'])
@limiter.limit("3 per hour")
def request_password_reset():
    """Request a password reset email."""
    data = request.get_json()
    email = (data.get('email') or '').strip().lower()

    if not email:
        return jsonify(error="Email is required"), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify(message="If that email exists, a reset link has been sent")

    token = secrets.token_urlsafe(32)
    user.password_reset_token = token
    user.password_reset_expires = _now_utc() + timedelta(hours=1)
    db.session.commit()

    # TODO: Send email with reset link via SendGrid
    logger.info(f"Password reset requested for {email}")

    return jsonify(message="If that email exists, a reset link has been sent")


@auth_bp.route('/password-reset/confirm', methods=['POST'])
def confirm_password_reset():
    """Confirm password reset with token."""
    data = request.get_json()
    token = data.get('token', '')
    new_password = data.get('password', '')

    if not token or not new_password:
        return jsonify(error="Token and new password are required"), 400

    if len(new_password) < 6:
        return jsonify(error="Password must be at least 6 characters"), 400

    user = User.query.filter_by(password_reset_token=token).first()
    if not user:
        return jsonify(error="Invalid or expired reset token"), 400

    if user.password_reset_expires and user.password_reset_expires < _now_utc():
        return jsonify(error="Reset token has expired"), 400

    user.set_password(new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    db.session.commit()

    return jsonify(message="Password has been reset successfully")
