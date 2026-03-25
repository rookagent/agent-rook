"""
MemoryTriple — Knowledge graph layer for Agent Rook memory.

Stores subject-predicate-object triples extracted from flat memories.
Enables entity-centric queries: "Tell me everything about Benny"
-> gets all triples where subject OR object matches.

Examples:
  ("Benny", "allergic_to", "peanuts")
  ("Benny", "enrolled_since", "January 2026")
  ("Kelly", "prefers", "hands-on activities")
  ("Centre", "opens_at", "7am")
  ("Patient_42", "takes", "oxycodone 10mg")
  ("Patient_42", "baseline_mmse", "28")
"""
import json
import logging
import pytz
from datetime import datetime
from app.extensions import db
from sqlalchemy import or_, text as sa_text

logger = logging.getLogger(__name__)

EASTERN = pytz.timezone('US/Eastern')


def _now_eastern():
    return datetime.now(EASTERN)


class MemoryTriple(db.Model):
    __tablename__ = 'memory_triples'

    id = db.Column(db.Integer, primary_key=True)

    # The triple itself
    subject = db.Column(db.String(200), nullable=False, index=True)
    predicate = db.Column(db.String(200), nullable=False)
    object = db.Column(db.String(500), nullable=False)

    # Link back to source flat memory (nullable — triples can outlive their source)
    memory_id = db.Column(
        db.Integer,
        db.ForeignKey('agent_memories.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )

    # Owner
    user_id = db.Column(db.Integer, nullable=False, index=True)

    # Organization scope (matches dual-scope pattern from AgentMemory)
    org_id = db.Column(db.Integer, nullable=True, index=True)

    # Confidence inherited from source memory or set by extractor
    confidence = db.Column(db.Float, default=0.85)

    # Soft delete
    is_active = db.Column(db.Boolean, default=True, index=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=_now_eastern)
    updated_at = db.Column(db.DateTime, default=_now_eastern, onupdate=_now_eastern)

    # Composite indexes for hot-path queries
    __table_args__ = (
        db.Index('ix_triple_subject_user', 'subject', 'user_id'),
        db.Index('ix_triple_predicate_user', 'predicate', 'user_id'),
        db.Index('ix_triple_subject_predicate_user', 'subject', 'predicate', 'user_id'),
    )

    # Relationship to source memory
    source_memory = db.relationship(
        'AgentMemory',
        backref=db.backref('triples', lazy='dynamic'),
        foreign_keys=[memory_id],
    )

    def __repr__(self):
        return (
            f"<MemoryTriple {self.id} "
            f"({self.subject}, {self.predicate}, {self.object}) "
            f"user={self.user_id}>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'subject': self.subject,
            'predicate': self.predicate,
            'object': self.object,
            'memory_id': self.memory_id,
            'user_id': self.user_id,
            'org_id': self.org_id,
            'confidence': self.confidence,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    # ------------------------------------------------------------------
    # Extraction — call Haiku to pull triples from a memory string
    # ------------------------------------------------------------------

    @classmethod
    def extract_triples(cls, content, ai_complete_func=None):
        """
        Extract subject-predicate-object triples from a memory content string.

        Uses Haiku (MODEL_FAST) to parse natural language into structured triples.
        If ai_complete_func is None, imports the default from ai_client.

        Args:
            content: The memory text to extract triples from.
            ai_complete_func: Optional callable(prompt) -> JSON string.
                              Defaults to ai_complete_json from ai_client.

        Returns:
            List of triple dicts: [{"subject": ..., "predicate": ..., "object": ...}]
        """
        if not content or not content.strip():
            return []

        if ai_complete_func is None:
            from app.utils.ai_client import ai_complete_json
            ai_complete_func = ai_complete_json

        prompt = (
            'Extract subject-predicate-object triples from this fact:\n'
            f'"{content}"\n\n'
            'Return JSON array: [{"subject": "...", "predicate": "...", "object": "..."}]\n'
            'Only extract clear, factual relationships. If none exist, return [].\n'
            'Keep subjects and objects short (1-3 words). Use snake_case for predicates.'
        )

        try:
            raw = ai_complete_func(prompt, max_tokens=300, temperature=0, context="triple_extraction")
            triples = json.loads(raw)

            if not isinstance(triples, list):
                logger.warning(f"Triple extraction returned non-list: {type(triples)}")
                return []

            # Validate each triple has the required keys and non-empty values
            validated = []
            for t in triples:
                if not isinstance(t, dict):
                    continue
                subj = str(t.get('subject', '')).strip()
                pred = str(t.get('predicate', '')).strip()
                obj = str(t.get('object', '')).strip()
                if subj and pred and obj:
                    validated.append({
                        'subject': subj[:200],
                        'predicate': pred[:200],
                        'object': obj[:500],
                    })

            return validated

        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Triple extraction JSON parse failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Triple extraction error: {e}", exc_info=True)
            return []

    # ------------------------------------------------------------------
    # Persistence — save/upsert triples to database
    # ------------------------------------------------------------------

    @classmethod
    def save_triples(cls, triples, user_id, memory_id=None, org_id=None, confidence=0.85):
        """
        Save a list of triple dicts to the database.

        Upsert logic: if an active triple with the same (subject, predicate, user_id)
        already exists, update its object value and bump updated_at. Facts change —
        "Benny is_age 3" becomes "Benny is_age 4".

        Args:
            triples: List of dicts from extract_triples.
            user_id: Owner user ID.
            memory_id: Optional FK to source AgentMemory.
            org_id: Optional organization scope.
            confidence: Default confidence for new triples.

        Returns:
            Count of triples saved or updated.
        """
        if not triples or not user_id:
            return 0

        count = 0
        for t in triples:
            subj = t.get('subject', '').strip()
            pred = t.get('predicate', '').strip()
            obj = t.get('object', '').strip()

            if not subj or not pred or not obj:
                continue

            # Check for existing active triple with same subject+predicate+user
            existing = cls.query.filter_by(
                subject=subj,
                predicate=pred,
                user_id=user_id,
                is_active=True,
            ).first()

            if existing:
                # Update: fact has changed (e.g. age, medication dose)
                existing.object = obj[:500]
                existing.confidence = max(existing.confidence, confidence)
                existing.updated_at = _now_eastern()
                if memory_id is not None:
                    existing.memory_id = memory_id
                if org_id is not None:
                    existing.org_id = org_id
                logger.debug(
                    f"Updated triple: ({subj}, {pred}) -> {obj} [user={user_id}]"
                )
            else:
                # New triple
                triple = cls(
                    subject=subj[:200],
                    predicate=pred[:200],
                    object=obj[:500],
                    memory_id=memory_id,
                    user_id=user_id,
                    org_id=org_id,
                    confidence=confidence,
                )
                db.session.add(triple)
                logger.debug(
                    f"New triple: ({subj}, {pred}, {obj}) [user={user_id}]"
                )

            count += 1

        db.session.commit()
        return count

    # ------------------------------------------------------------------
    # Querying — entity-centric lookups
    # ------------------------------------------------------------------

    @classmethod
    def query_entity(cls, entity_name, user_id, org_id=None):
        """
        Find all active triples where subject OR object matches entity_name.

        Uses case-insensitive LIKE matching so "benny", "Benny", "BENNY" all work.
        If org_id is provided, includes org-scoped triples in addition to
        user-scoped ones.

        Args:
            entity_name: The entity to search for.
            user_id: The user whose triples to search.
            org_id: Optional org scope to include.

        Returns:
            List of triple dicts, ordered by confidence DESC.
        """
        if not entity_name or not user_id:
            return []

        pattern = entity_name.strip()

        # Build scope filter: user's own triples + optionally org triples
        scope_filters = [cls.user_id == user_id]
        if org_id:
            scope_filters = [or_(cls.user_id == user_id, cls.org_id == org_id)]

        triples = (
            cls.query.filter(
                cls.is_active == True,
                *scope_filters,
                or_(
                    cls.subject.ilike(pattern),
                    cls.object.ilike(pattern),
                ),
            )
            .order_by(cls.confidence.desc(), cls.updated_at.desc())
            .all()
        )

        return [t.to_dict() for t in triples]

    @classmethod
    def get_entity_summary(cls, entity_name, user_id, org_id=None):
        """
        Build a human-readable summary of everything known about an entity.
        Suitable for injection into agent system prompts.

        Example output:
            About Benny:
            - allergic_to: peanuts
            - enrolled_since: January 2026
            - favourite_activity: painting

        Args:
            entity_name: The entity to summarize.
            user_id: Owner user ID.
            org_id: Optional org scope.

        Returns:
            Formatted string, or empty string if no triples found.
        """
        triples = cls.query_entity(entity_name, user_id, org_id)
        if not triples:
            return ""

        lines = [f"About {entity_name}:"]

        # Separate triples where entity is subject vs object
        as_subject = [t for t in triples if t['subject'].lower() == entity_name.lower()]
        as_object = [t for t in triples if t['object'].lower() == entity_name.lower()]

        # Subject triples: entity -> predicate -> value
        for t in as_subject:
            lines.append(f"  - {t['predicate']}: {t['object']}")

        # Object triples: something -> predicate -> entity (reverse perspective)
        for t in as_object:
            lines.append(f"  - (referenced by {t['subject']}: {t['predicate']})")

        return "\n".join(lines)

    @classmethod
    def get_all_entities(cls, user_id, org_id=None):
        """
        Get all distinct entity names (subjects) for a user/org.

        Useful for "what do I know about?" or entity autocomplete.

        Args:
            user_id: Owner user ID.
            org_id: Optional org scope.

        Returns:
            Sorted list of distinct entity name strings.
        """
        if not user_id:
            return []

        scope_filters = [cls.user_id == user_id]
        if org_id:
            scope_filters = [or_(cls.user_id == user_id, cls.org_id == org_id)]

        rows = (
            db.session.query(cls.subject)
            .filter(cls.is_active == True, *scope_filters)
            .distinct()
            .order_by(cls.subject)
            .all()
        )

        return [row[0] for row in rows]

    # ------------------------------------------------------------------
    # Lifecycle — soft delete
    # ------------------------------------------------------------------

    @classmethod
    def deactivate_entity(cls, entity_name, user_id):
        """
        Soft-delete ALL triples for an entity.

        Triggered when user says "forget everything about Benny".
        Sets is_active=False on all triples where entity appears as
        subject OR object.

        Args:
            entity_name: The entity to forget.
            user_id: Owner user ID.

        Returns:
            Count of triples deactivated.
        """
        if not entity_name or not user_id:
            return 0

        pattern = entity_name.strip()

        triples = cls.query.filter(
            cls.is_active == True,
            cls.user_id == user_id,
            or_(
                cls.subject.ilike(pattern),
                cls.object.ilike(pattern),
            ),
        ).all()

        count = len(triples)
        for t in triples:
            t.is_active = False

        if triples:
            db.session.commit()

        logger.info(
            f"Deactivated {count} triples for entity '{entity_name}' [user={user_id}]"
        )
        return count
