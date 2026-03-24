"""
Agent Memory — persistent memory for agent conversations.

At the end of each chat session, the agent extracts key facts learned about
the user and stores them. On the next session, these memories are loaded into
the system prompt so the agent remembers preferences, context, and details.

Memory types:
- preference: "Prefers concise answers", "Likes detailed code examples"
- fact: "Works at Acme Corp", "Uses Python 3.12"
- goal: "Learning Rust", "Building a SaaS product"
- interaction: "Asked about deployment last week", "We debugged auth together"
- schedule: Structured schedule data stored as JSON in structured_data column

Memories have confidence scores and decay over time if not reinforced.
Each conversation can add, update, or reinforce existing memories.
Schedule memories use a single merged JSON record per user (not fragments).
"""
import json
import logging
from datetime import datetime
from app.extensions import db

logger = logging.getLogger(__name__)


class AgentMemory(db.Model):
    __tablename__ = 'agent_memories'

    id = db.Column(db.Integer, primary_key=True)

    # Owner — always a user
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )

    # Memory content
    memory_type = db.Column(
        db.String(20),
        nullable=False,
        default='fact',
    )  # preference, fact, goal, interaction, schedule
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))  # e.g. workflow, tools, personal, schedule, project

    # Structured data for schedule memories (JSON-encoded dict)
    structured_data = db.Column(db.Text, nullable=True)

    # Confidence and reinforcement
    confidence = db.Column(db.Float, default=0.8)  # 0.0-1.0, decays over time
    times_reinforced = db.Column(db.Integer, default=1)
    last_reinforced = db.Column(db.DateTime, default=datetime.utcnow)

    # Source tracking
    source_session = db.Column(db.String(100))

    # Active/archived
    is_active = db.Column(db.Boolean, default=True, index=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('agent_memories', lazy='dynamic'))

    def __repr__(self):
        return f"<AgentMemory {self.id} [{self.memory_type}] user={self.user_id}: {self.content[:50]}>"

    def to_dict(self):
        result = {
            'id': self.id,
            'type': self.memory_type,
            'content': self.content,
            'category': self.category,
            'confidence': self.confidence,
            'times_reinforced': self.times_reinforced,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if self.structured_data:
            try:
                result['structured_data'] = json.loads(self.structured_data)
            except (json.JSONDecodeError, TypeError):
                pass
        return result

    def get_structured_data(self):
        """Parse and return structured_data as a dict, or empty dict if not set."""
        if not self.structured_data:
            return {}
        try:
            return json.loads(self.structured_data)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_structured_data(self, data):
        """Set structured_data from a dict."""
        self.structured_data = json.dumps(data) if data else None

    def reinforce(self):
        """Called when a memory is confirmed/mentioned again in a new session."""
        self.times_reinforced += 1
        self.last_reinforced = datetime.utcnow()
        self.confidence = min(1.0, self.confidence + 0.1)

    @classmethod
    def get_or_create_schedule(cls, user_id=None):
        """
        Return the single structured schedule memory for a user,
        creating it if it doesn't exist. Schedule data is ONE memory record
        per user with merged JSON — not scattered fragments.
        """
        if not user_id:
            return None

        schedule_mem = cls.query.filter_by(
            user_id=user_id, memory_type='schedule', is_active=True
        ).first()

        if not schedule_mem:
            schedule_mem = cls(
                user_id=user_id,
                memory_type='schedule',
                content='User schedule',
                category='schedule',
                confidence=1.0,
                structured_data=json.dumps({}),
            )
            db.session.add(schedule_mem)
            db.session.commit()

        return schedule_mem

    @classmethod
    def merge_schedule_data(cls, user_id=None, new_data=None):
        """
        Merge new schedule data into the single structured schedule memory.
        Deep merge: new keys added, existing keys updated,
        nested dicts merged key-by-key.

        Supports versioned schedule entries:
        - Permanent: "hours", "days", "daily_routine" — the regular schedule
        - Temporary: stored in "temporary_changes" list with expiry dates
          e.g. {"change": "Out of office Monday", "expires": "2026-03-11"}

        Temporary changes auto-expire and are cleaned up on every merge.
        """
        if not new_data:
            return None

        clean_data = {k: v for k, v in new_data.items() if v is not None}
        if not clean_data:
            return None

        schedule_mem = cls.get_or_create_schedule(user_id=user_id)
        if not schedule_mem:
            return None

        existing = schedule_mem.get_structured_data()

        # Clean up expired temporary changes
        if existing.get('temporary_changes'):
            from datetime import date as date_type
            today_str = date_type.today().isoformat()
            existing['temporary_changes'] = [
                tc for tc in existing['temporary_changes']
                if tc.get('expires', '9999-12-31') >= today_str
            ]
            if not existing['temporary_changes']:
                del existing['temporary_changes']

        # Handle temporary changes separately
        if 'temporary_changes' in clean_data:
            new_temps = clean_data.pop('temporary_changes')
            if isinstance(new_temps, list):
                if 'temporary_changes' not in existing:
                    existing['temporary_changes'] = []
                existing['temporary_changes'].extend(new_temps)
                existing['temporary_changes'] = existing['temporary_changes'][-10:]

        # Deep merge permanent schedule data
        for key, value in clean_data.items():
            if isinstance(value, dict) and isinstance(existing.get(key), dict):
                existing[key].update(value)
            else:
                existing[key] = value

        schedule_mem.set_structured_data(existing)

        # Build a human-readable content summary
        summary_parts = []
        if existing.get('hours_start') or existing.get('hours_end'):
            h_start = existing.get('hours_start', '?')
            h_end = existing.get('hours_end', '?')
            summary_parts.append(f"Hours: {h_start} - {h_end}")
        if existing.get('days'):
            summary_parts.append(f"Days: {existing['days']}")
        if existing.get('daily_routine'):
            routine_count = len(existing['daily_routine'])
            summary_parts.append(f"Daily routine: {routine_count} activities")
        if existing.get('exceptions'):
            summary_parts.append(f"Exceptions: {existing['exceptions']}")
        if existing.get('temporary_changes'):
            temp_count = len(existing['temporary_changes'])
            summary_parts.append(f"Temporary changes: {temp_count}")

        schedule_mem.content = '; '.join(summary_parts) if summary_parts else 'User schedule'
        schedule_mem.reinforce()
        schedule_mem.confidence = 1.0  # Schedule data is authoritative

        db.session.commit()

        # Invalidate memory cache after schedule update
        _invalidate_cache(user_id=user_id)

        return schedule_mem

    @staticmethod
    def get_memories_for_prompt(user_id=None, limit=40):
        """
        Get active memories formatted for injection into the agent's system prompt.
        Returns a string block ready to paste into the prompt.

        Category-aware retrieval:
        - Always include ALL schedule memories (up to 5)
        - Fill remaining slots with other types by confidence + recency
        - Total cap: 40 memories
        """
        if not user_id:
            return ""

        # Check Redis cache first
        cached = _get_cached_block(user_id=user_id)
        if cached is not None:
            return cached

        base_filters = {'is_active': True, 'user_id': user_id}

        # 1. Always get schedule memories (up to 5)
        schedule_memories = (
            AgentMemory.query.filter_by(**base_filters, memory_type='schedule')
            .order_by(AgentMemory.last_reinforced.desc())
            .limit(5)
            .all()
        )

        # 2. Fill remaining slots with other types
        priority_ids = [m.id for m in schedule_memories]
        remaining_slots = limit - len(priority_ids)

        if remaining_slots > 0:
            other_query = (
                AgentMemory.query.filter_by(**base_filters)
                .filter(AgentMemory.memory_type != 'schedule')
            )
            if priority_ids:
                other_query = other_query.filter(AgentMemory.id.notin_(priority_ids))
            other_memories = (
                other_query
                .order_by(AgentMemory.confidence.desc(), AgentMemory.last_reinforced.desc())
                .limit(remaining_slots)
                .all()
            )
        else:
            other_memories = []

        all_memories = schedule_memories + other_memories

        if not all_memories:
            return ""

        lines = []

        # Render schedule memories with structured data
        if schedule_memories:
            for m in schedule_memories:
                sdata = m.get_structured_data()
                if sdata:
                    lines.append("USER SCHEDULE (from previous conversations):")
                    if sdata.get('hours_start') or sdata.get('hours_end'):
                        h_start = sdata.get('hours_start', '?')
                        h_end = sdata.get('hours_end', '?')
                        lines.append(f"  Hours: {h_start} - {h_end}")
                    if sdata.get('days'):
                        lines.append(f"  Days: {sdata['days']}")
                    if sdata.get('daily_routine') and isinstance(sdata['daily_routine'], dict):
                        lines.append("  Daily Routine:")
                        routine = sdata['daily_routine']
                        for time_str, activity in sorted(routine.items()):
                            lines.append(f"    {time_str} - {activity}")
                    if sdata.get('exceptions'):
                        lines.append(f"  Exceptions: {sdata['exceptions']}")
                    if sdata.get('temporary_changes') and isinstance(sdata['temporary_changes'], list):
                        lines.append("  Temporary Changes (auto-expire):")
                        for tc in sdata['temporary_changes']:
                            change = tc.get('change', '?')
                            expires = tc.get('expires', '')
                            lines.append(f"    - {change}{f' (until {expires})' if expires else ''}")
                else:
                    lines.append(f"USER SCHEDULE: {m.content}")

        # Group remaining memories by type
        if other_memories:
            grouped = {}
            for m in other_memories:
                grouped.setdefault(m.memory_type, []).append(m)

            if lines:
                lines.append("")
            lines.append("THINGS YOU REMEMBER ABOUT THIS USER (from previous conversations):")

            type_labels = {
                'preference': 'Preferences',
                'fact': 'Key Facts',
                'goal': 'Goals',
                'interaction': 'Previous Interactions',
            }

            for mtype, label in type_labels.items():
                if mtype in grouped:
                    lines.append(f"\n  {label}:")
                    for m in grouped[mtype]:
                        lines.append(f"    - {m.content}")

        lines.append(
            "\nUse these memories naturally in conversation — reference them when relevant "
            "but don't list them all at once. It should feel like you genuinely remember."
        )

        result = "\n".join(lines)
        _set_cached_block(result, user_id=user_id)
        return result

    @classmethod
    def purge_all_memories(cls, user_id=None):
        """
        Soft-delete ALL memories for a user.
        Sets is_active=False (not hard delete) for audit trail.
        Invalidates memory cache after purge.

        Returns count of memories deactivated.
        """
        if not user_id:
            return 0

        memories = cls.query.filter_by(user_id=user_id, is_active=True).all()
        count = len(memories)

        for m in memories:
            m.is_active = False
            m.confidence = 0.0

        if memories:
            db.session.commit()

        _invalidate_cache(user_id=user_id)

        logger.info(f"Memory purge complete: {count} memories deactivated (user={user_id})")
        return count

    @staticmethod
    def save_memories_from_session(user_id=None, memories_list=None):
        """
        Save new memories extracted from a chat session.

        memories_list: [{"type": "preference", "content": "Prefers concise answers", "category": "workflow"}, ...]

        Uses pg_trgm fuzzy dedup (similarity > 0.6) with exact-match fallback.
        """
        if not memories_list or not user_id:
            return []

        saved = []
        for mem_data in memories_list:
            content = mem_data.get('content', '').strip()
            if not content:
                continue

            # Fuzzy dedup: check for similar existing memories (pg_trgm similarity > 0.6)
            from sqlalchemy import text as sa_text
            existing = None
            try:
                existing = (
                    AgentMemory.query
                    .filter(
                        AgentMemory.user_id == user_id,
                        AgentMemory.is_active == True,
                    )
                    .filter(sa_text("similarity(content, :new_content) > 0.6"))
                    .params(new_content=content)
                    .order_by(sa_text("similarity(content, :new_content) DESC"))
                    .params(new_content=content)
                    .first()
                )
            except Exception:
                # Fallback: exact match if pg_trgm not installed
                db.session.rollback()
                existing = AgentMemory.query.filter_by(
                    user_id=user_id,
                    content=content,
                    is_active=True,
                ).first()

            if existing:
                existing.reinforce()
                saved.append(existing)
            else:
                memory = AgentMemory(
                    user_id=user_id,
                    memory_type=mem_data.get('type', 'fact'),
                    content=content,
                    category=mem_data.get('category'),
                    confidence=mem_data.get('confidence', 0.8),
                )
                db.session.add(memory)
                saved.append(memory)

        db.session.commit()

        _invalidate_cache(user_id=user_id)

        return saved


# ---------------------------------------------------------------------------
# Redis memory cache helpers
# ---------------------------------------------------------------------------
# Cache keys use 'rook:' prefix. TTL: 1 hour (3600s).
# Invalidated on write (save_memories_from_session, merge_schedule_data, purge).

_redis_client = None
_CACHE_TTL = 3600


def _get_redis():
    """Get or create Redis connection. Returns None if Redis unavailable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis
        from config.settings import Config
        broker_url = getattr(Config, 'CELERY_BROKER_URL', None) or getattr(Config, 'REDIS_URL', None)
        if not broker_url:
            return None
        _redis_client = redis.from_url(broker_url, decode_responses=True, socket_timeout=2)
        _redis_client.ping()
        return _redis_client
    except Exception:
        _redis_client = None
        return None


def _cache_key(user_id):
    return f"rook:mem:user:{user_id}"


def _get_cached_block(user_id=None):
    """Return cached memory block string, or None if not cached."""
    if not user_id:
        return None
    r = _get_redis()
    if not r:
        return None
    try:
        return r.get(_cache_key(user_id))
    except Exception:
        return None


def _set_cached_block(block, user_id=None):
    """Cache a formatted memory block string."""
    if not user_id or not block:
        return
    r = _get_redis()
    if not r:
        return
    try:
        r.setex(_cache_key(user_id), _CACHE_TTL, block)
    except Exception:
        pass


def _invalidate_cache(user_id=None):
    """Delete cached memory block for a user."""
    if not user_id:
        return
    r = _get_redis()
    if not r:
        return
    try:
        r.delete(_cache_key(user_id))
    except Exception:
        pass
