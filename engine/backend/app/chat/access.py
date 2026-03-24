"""
Agent Rook — Access control and credit management.

Three-tier system:
1. Admin → unlimited
2. Credits > 0 → deduct 1 per message, no daily cap
3. Free → N messages/day (configurable in agent.yaml)
"""
import logging
from datetime import datetime

import pytz

logger = logging.getLogger(__name__)


def _user_today(user):
    """Get today's date in the user's timezone (or US/Eastern as default)."""
    tz_name = getattr(user, 'timezone', None) or 'US/Eastern'
    try:
        tz = pytz.timezone(tz_name)
    except pytz.UnknownTimeZoneError:
        tz = pytz.timezone('US/Eastern')
    return datetime.now(tz).date()


def _get_redis():
    """Get Redis connection for daily limit counters."""
    try:
        import redis
        import os
        url = os.environ.get('CELERY_BROKER_URL') or os.environ.get('REDIS_URL')
        if url:
            return redis.from_url(url)
    except Exception:
        pass
    return None


def _check_free_daily_limit(user, daily_limit):
    """
    Check and increment the free user's daily message count.
    Returns (allowed, remaining, limit).
    Uses Redis counter with TTL until midnight in user's timezone.
    """
    try:
        r = _get_redis()
        if not r:
            return True, daily_limit, daily_limit

        today = _user_today(user)
        key = f"rook_daily:{user.id}:{today.isoformat()}"
        count = r.incr(key)

        if count == 1:
            # Expire at end of day
            r.expire(key, 86400)

        remaining = max(0, daily_limit - count)
        return count <= daily_limit, remaining, daily_limit
    except Exception as e:
        logger.debug(f"Daily limit check failed (allowing): {e}")
        return True, daily_limit, daily_limit


def check_and_deduct_access(user, daily_limit=3, upgrade_message=None):
    """
    Check if user can send a message and deduct credits if applicable.

    Args:
        user: User model instance.
        daily_limit: Free messages per day (from agent.yaml config).
        upgrade_message: Custom message shown when limit is reached.

    Returns dict: {allowed, remaining, limit, credits, access_type, message}
    """
    from config.settings import Config
    agent_name = Config.AGENT_NAME

    result = {
        'allowed': True,
        'remaining': 0,
        'limit': 0,
        'credits': 0,
        'access_type': 'free',
        'message': None,
    }

    if not user:
        return {**result, 'allowed': False, 'message': 'Authentication required.'}

    # Admin — unlimited
    if user.role == 'admin':
        return {**result, 'access_type': 'admin', 'remaining': 9999, 'limit': 9999}

    # Credit user — deduct 1 credit, no daily cap
    try:
        user_credits = getattr(user, 'credits', 0) or 0
        if user_credits > 0:
            if user.use_credit():
                return {
                    **result,
                    'access_type': 'credits',
                    'credits': user.credits,
                    'remaining': user.credits,
                    'limit': 0,
                }
    except Exception:
        pass

    # Free user — daily limit
    allowed, remaining, limit = _check_free_daily_limit(user, daily_limit)
    if not allowed:
        msg = upgrade_message or (
            f"You've used your {limit} free messages today. "
            f"Get more {agent_name} credits to keep chatting!"
        )
        return {**result, 'allowed': False, 'remaining': 0, 'limit': limit, 'message': msg}

    return {**result, 'remaining': remaining, 'limit': limit}
