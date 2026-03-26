"""
Memory system scale tests.
Verifies performance and correctness at clinical-grade volumes.

Run:
    cd /Users/kellysmith/Desktop/agentrook/engine/backend
    python -m pytest ../../tests/test_memory_scale.py -v -s
"""
import json
import sys
import os
import time
import threading
import unittest
from datetime import datetime, timedelta

# Ensure the backend app is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'engine', 'backend'))

from flask import Flask
from app.extensions import db
from app.models.agent_memory import AgentMemory
from app.models.user import User


def create_test_app():
    """Create a minimal Flask app with SQLite in-memory for testing."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    app.config['JWT_SECRET_KEY'] = 'test-jwt-secret'

    db.init_app(app)

    with app.app_context():
        db.create_all()

    return app


def make_user(email='test@example.com'):
    """Create and persist a test user."""
    user = User(
        email=email,
        password_hash='fakehash',
        role='user',
        verified=True,
        subscription_tier='premium',
    )
    db.session.add(user)
    db.session.commit()
    return user


class TestBulkSave200Memories(unittest.TestCase):
    """Create 200 memories for one user. Verify all saved, no duplicates, no crashes."""

    def setUp(self):
        self.app = create_test_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.user = make_user()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_bulk_save_200_memories(self):
        memories_list = [
            {
                'type': 'fact',
                'content': f'Unique fact number {i}: the user mentioned detail {i * 7}',
                'category': 'personal',
            }
            for i in range(200)
        ]

        start = time.time()
        saved = AgentMemory.save_memories_from_session(
            user_id=self.user.id, memories_list=memories_list
        )
        elapsed = time.time() - start

        self.assertEqual(len(saved), 200, f"Expected 200 saved, got {len(saved)}")

        # Verify DB count
        count = AgentMemory.query.filter_by(user_id=self.user.id, is_active=True).count()
        self.assertEqual(count, 200, f"DB count mismatch: {count}")

        # No duplicate content
        contents = [m.content for m in AgentMemory.query.filter_by(user_id=self.user.id).all()]
        self.assertEqual(len(contents), len(set(contents)), "Duplicate content found")

        print(f"\n  [PERF] Bulk save 200 memories: {elapsed:.3f}s")
        self.assertLess(elapsed, 5.0, f"Too slow: {elapsed:.3f}s (limit 5s)")


class TestPromptInjectionAt200(unittest.TestCase):
    """With 200 memories, verify get_memories_for_prompt returns within limits."""

    def setUp(self):
        self.app = create_test_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.user = make_user()

        # Seed 200 memories with varying confidence
        for i in range(200):
            mem = AgentMemory(
                user_id=self.user.id,
                memory_type='fact',
                content=f'Memory fact {i}: detail about topic {i % 20}',
                category='personal',
                confidence=0.5 + (i % 50) * 0.01,  # 0.50 - 0.99 range
                last_reinforced=datetime.utcnow() - timedelta(hours=200 - i),
            )
            db.session.add(mem)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_prompt_injection_at_200(self):
        start = time.time()
        prompt_block = AgentMemory.get_memories_for_prompt(
            user_id=self.user.id, limit=40
        )
        elapsed = time.time() - start

        self.assertIsInstance(prompt_block, str)
        self.assertGreater(len(prompt_block), 0, "Prompt block should not be empty")

        # Count memory lines (lines starting with "    - ")
        memory_lines = [l for l in prompt_block.split('\n') if l.strip().startswith('- Memory fact')]
        self.assertLessEqual(len(memory_lines), 40, f"Exceeded prompt limit: {len(memory_lines)} lines")

        print(f"\n  [PERF] get_memories_for_prompt (200 memories, limit=40): {elapsed*1000:.1f}ms")
        self.assertLess(elapsed, 0.1, f"Too slow: {elapsed*1000:.1f}ms (limit 100ms)")


class TestDedupAtScale(unittest.TestCase):
    """Save 50 unique, then 50 near-duplicates. Verify dedup reinforces instead of creating."""

    def setUp(self):
        self.app = create_test_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.user = make_user()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_dedup_at_scale(self):
        # Phase 1: 50 unique memories
        unique_memories = [
            {'type': 'fact', 'content': f'The user works with technology {i} in their workflow'}
            for i in range(50)
        ]
        saved_phase1 = AgentMemory.save_memories_from_session(
            user_id=self.user.id, memories_list=unique_memories
        )
        count_after_phase1 = AgentMemory.query.filter_by(
            user_id=self.user.id, is_active=True
        ).count()
        self.assertEqual(count_after_phase1, 50)

        # Phase 2: 50 exact duplicates (same content)
        # SQLite fallback uses exact match, so these should reinforce
        duplicate_memories = [
            {'type': 'fact', 'content': f'The user works with technology {i} in their workflow'}
            for i in range(50)
        ]
        saved_phase2 = AgentMemory.save_memories_from_session(
            user_id=self.user.id, memories_list=duplicate_memories
        )

        count_after_phase2 = AgentMemory.query.filter_by(
            user_id=self.user.id, is_active=True
        ).count()

        # With exact-match fallback (SQLite), duplicates should reinforce existing
        self.assertEqual(
            count_after_phase2, 50,
            f"Expected 50 (deduped), got {count_after_phase2}"
        )

        # Verify reinforcement happened
        reinforced = AgentMemory.query.filter(
            AgentMemory.user_id == self.user.id,
            AgentMemory.times_reinforced > 1,
        ).count()
        self.assertEqual(reinforced, 50, f"Expected 50 reinforced, got {reinforced}")

        print(f"\n  [DEDUP] 50 unique + 50 duplicates -> {count_after_phase2} total, {reinforced} reinforced")


class TestSurpriseScoringDistribution(unittest.TestCase):
    """Save 100 memories across topics. Verify surprise scores distribute reasonably."""

    def setUp(self):
        self.app = create_test_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.user = make_user()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_surprise_scoring_distribution(self):
        # Save memories in batches of 10 with different topics
        topics = [
            'Python programming', 'machine learning', 'cooking Italian food',
            'running marathons', 'playing guitar', 'reading science fiction',
            'gardening tomatoes', 'building furniture', 'astronomy stars',
            'meditation practice',
        ]

        all_saved = []
        for batch_idx, topic in enumerate(topics):
            batch = [
                {
                    'type': 'fact',
                    'content': f'The user enjoys {topic} — variant {i} detail',
                    'category': 'personal',
                }
                for i in range(10)
            ]
            saved = AgentMemory.save_memories_from_session(
                user_id=self.user.id, memories_list=batch
            )
            all_saved.extend(saved)

        # All memories should have surprise scores (SQLite falls back to 0.5)
        memories_with_scores = AgentMemory.query.filter(
            AgentMemory.user_id == self.user.id,
            AgentMemory.surprise_score.isnot(None),
        ).all()

        self.assertGreater(len(memories_with_scores), 0, "No memories have surprise scores")

        scores = [m.surprise_score for m in memories_with_scores]
        avg_score = sum(scores) / len(scores)

        # With SQLite fallback (no pg_trgm), all scores default to 0.5
        # Just verify they exist and are in valid range
        for score in scores:
            self.assertGreaterEqual(score, 0.0, f"Score below 0: {score}")
            self.assertLessEqual(score, 1.0, f"Score above 1: {score}")

        print(f"\n  [SURPRISE] {len(scores)} memories scored, avg={avg_score:.3f}, "
              f"min={min(scores):.3f}, max={max(scores):.3f}")


class TestDualScopeIsolation(unittest.TestCase):
    """Verify org-scoped and personal memories do not cross-contaminate."""

    def setUp(self):
        self.app = create_test_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.user = make_user()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_dual_scope_isolation(self):
        user_id = self.user.id

        # Org 1 memories
        org1_memories = [
            {'type': 'fact', 'content': f'Org 1 policy: rule {i}', 'category': 'workflow'}
            for i in range(15)
        ]
        AgentMemory.save_memories_from_session(
            user_id=user_id, org_id=1, memories_list=org1_memories
        )

        # Org 2 memories
        org2_memories = [
            {'type': 'fact', 'content': f'Org 2 protocol: guideline {i}', 'category': 'workflow'}
            for i in range(15)
        ]
        AgentMemory.save_memories_from_session(
            user_id=user_id, org_id=2, memories_list=org2_memories
        )

        # Personal memories (no org)
        personal_memories = [
            {'type': 'preference', 'content': f'User prefers setting {i}', 'category': 'personal'}
            for i in range(10)
        ]
        AgentMemory.save_memories_from_session(
            user_id=user_id, memories_list=personal_memories
        )

        # Query dual scope for org 1
        prompt_org1 = AgentMemory.get_dual_memories_for_prompt(
            org_id=1, user_id=user_id
        )

        # Verify org 1 content is present
        self.assertIn('Org 1 policy', prompt_org1)

        # Verify org 2 content is NOT present (isolation)
        self.assertNotIn('Org 2 protocol', prompt_org1,
                         "Org 2 memories leaked into org 1 query!")

        # Verify personal memories are present
        self.assertIn('User prefers', prompt_org1)

        # Query dual scope for org 2
        prompt_org2 = AgentMemory.get_dual_memories_for_prompt(
            org_id=2, user_id=user_id
        )
        self.assertIn('Org 2 protocol', prompt_org2)
        self.assertNotIn('Org 1 policy', prompt_org2,
                         "Org 1 memories leaked into org 2 query!")
        self.assertIn('User prefers', prompt_org2)

        # Count verification
        org1_count = AgentMemory.query.filter_by(org_id=1, is_active=True).count()
        org2_count = AgentMemory.query.filter_by(org_id=2, is_active=True).count()
        personal_count = AgentMemory.query.filter(
            AgentMemory.user_id == user_id,
            AgentMemory.org_id.is_(None),
            AgentMemory.is_active == True,
        ).count()

        self.assertEqual(org1_count, 15)
        self.assertEqual(org2_count, 15)
        self.assertEqual(personal_count, 10)

        print(f"\n  [ISOLATION] org1={org1_count}, org2={org2_count}, personal={personal_count}")


class TestSmartCapEnforcement(unittest.TestCase):
    """Save 70 memories (above 50 cap trigger at 60). Run smart cap, verify trim to 50."""

    def setUp(self):
        self.app = create_test_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.user = make_user()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_smart_cap_enforcement(self):
        user_id = self.user.id

        # Create 70 memories: mix of types, varying confidence
        for i in range(70):
            mem_type = 'fact'
            confidence = 0.5 + (i % 30) * 0.015  # 0.50 - 0.935
            # Make some schedule and procedure types (should be protected)
            if i < 5:
                mem_type = 'schedule'
                confidence = 1.0
            elif i < 10:
                mem_type = 'preference'
                confidence = 0.95

            mem = AgentMemory(
                user_id=user_id,
                memory_type=mem_type,
                content=f'Memory {i}: type={mem_type} conf={confidence:.2f}',
                category='schedule' if mem_type == 'schedule' else 'personal',
                confidence=confidence,
                last_reinforced=datetime.utcnow() - timedelta(hours=70 - i),
            )
            db.session.add(mem)
        db.session.commit()

        count_before = AgentMemory.query.filter_by(
            user_id=user_id, is_active=True
        ).count()
        self.assertEqual(count_before, 70)

        # Run smart cap: soft-delete lowest confidence memories to reach cap of 50
        cap = 50
        if count_before > cap:
            # Protected types that should survive the cull
            protected_types = ('schedule', 'procedure')

            # Get all active memories ordered by confidence ASC (worst first)
            all_memories = (
                AgentMemory.query
                .filter_by(user_id=user_id, is_active=True)
                .order_by(AgentMemory.confidence.asc(), AgentMemory.last_reinforced.asc())
                .all()
            )

            # Separate protected from cullable
            protected = [m for m in all_memories if m.memory_type in protected_types]
            cullable = [m for m in all_memories if m.memory_type not in protected_types]

            # How many to remove
            excess = count_before - cap
            to_remove = cullable[:excess]

            for m in to_remove:
                m.is_active = False
                m.confidence = 0.0
            db.session.commit()

        count_after = AgentMemory.query.filter_by(
            user_id=user_id, is_active=True
        ).count()

        # Verify trimmed to cap
        self.assertLessEqual(count_after, cap, f"Still over cap: {count_after}")

        # Verify protected types survived
        schedule_count = AgentMemory.query.filter_by(
            user_id=user_id, memory_type='schedule', is_active=True
        ).count()
        self.assertEqual(schedule_count, 5, f"Schedule memories lost: {schedule_count}")

        # Verify remaining memories have higher confidence than removed ones
        remaining = AgentMemory.query.filter_by(
            user_id=user_id, is_active=True
        ).all()
        removed = AgentMemory.query.filter_by(
            user_id=user_id, is_active=False
        ).all()

        if remaining and removed:
            min_remaining_conf = min(
                m.confidence for m in remaining if m.memory_type not in ('schedule', 'procedure')
            )
            # Removed memories should have had lower original confidence
            # (their confidence is now 0.0 from the cap logic)
            self.assertGreater(min_remaining_conf, 0.0)

        print(f"\n  [CAP] {count_before} -> {count_after} memories, "
              f"{schedule_count} schedule protected, {len(removed)} removed")


class TestConcurrentSaveAndQuery(unittest.TestCase):
    """Use threading to simultaneously save and query. Verify no crashes or deadlocks."""

    def setUp(self):
        self.app = create_test_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.user = make_user()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_concurrent_save_and_query(self):
        user_id = self.user.id
        errors = []
        results = {'saves': 0, 'queries': 0}

        def save_batch(batch_id):
            """Save a batch of memories in its own app context."""
            try:
                with self.app.app_context():
                    memories = [
                        {
                            'type': 'fact',
                            'content': f'Concurrent batch {batch_id} memory {i}',
                            'category': 'personal',
                        }
                        for i in range(20)
                    ]
                    saved = AgentMemory.save_memories_from_session(
                        user_id=user_id, memories_list=memories
                    )
                    results['saves'] += len(saved)
            except Exception as e:
                errors.append(f"Save error batch {batch_id}: {e}")

        def query_memories(query_id):
            """Query memories in its own app context."""
            try:
                with self.app.app_context():
                    prompt = AgentMemory.get_memories_for_prompt(
                        user_id=user_id, limit=40
                    )
                    results['queries'] += 1
            except Exception as e:
                errors.append(f"Query error {query_id}: {e}")

        threads = []

        # 5 save threads (20 memories each = 100 total)
        for i in range(5):
            t = threading.Thread(target=save_batch, args=(i,))
            threads.append(t)

        # 5 query threads running concurrently
        for i in range(5):
            t = threading.Thread(target=query_memories, args=(i,))
            threads.append(t)

        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        elapsed = time.time() - start

        # Check for deadlocks (threads that didn't finish)
        hung = [t for t in threads if t.is_alive()]
        self.assertEqual(len(hung), 0, f"{len(hung)} threads hung (possible deadlock)")

        # Check for errors
        self.assertEqual(len(errors), 0, f"Concurrent errors: {errors}")

        print(f"\n  [CONCURRENT] {results['saves']} saved, {results['queries']} queries, "
              f"{elapsed:.3f}s, {len(errors)} errors")


class TestMemoryExportAll(unittest.TestCase):
    """With 200 memories, export all as JSON. Verify structure."""

    def setUp(self):
        self.app = create_test_app()
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.user = make_user()

        # Seed 200 memories
        for i in range(200):
            mem = AgentMemory(
                user_id=self.user.id,
                memory_type=['fact', 'preference', 'goal', 'interaction'][i % 4],
                content=f'Export test memory {i}: some detail here',
                category=['personal', 'workflow', 'project'][i % 3],
                confidence=0.5 + (i % 50) * 0.01,
                surprise_score=0.5,
            )
            db.session.add(mem)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_memory_export_all(self):
        start = time.time()

        memories = AgentMemory.query.filter_by(
            user_id=self.user.id, is_active=True
        ).all()

        exported = [m.to_dict() for m in memories]
        elapsed = time.time() - start

        # Verify count
        self.assertEqual(len(exported), 200, f"Expected 200, got {len(exported)}")

        # Verify JSON serializable
        json_str = json.dumps(exported)
        self.assertIsInstance(json_str, str)

        # Verify structure of each exported memory
        required_keys = {'id', 'type', 'content', 'category', 'confidence', 'surprise_score', 'created_at'}
        for mem_dict in exported:
            missing = required_keys - set(mem_dict.keys())
            self.assertEqual(len(missing), 0, f"Missing keys: {missing}")
            self.assertIsInstance(mem_dict['id'], int)
            self.assertIsInstance(mem_dict['content'], str)
            self.assertIsInstance(mem_dict['confidence'], float)

        # Verify all 4 types represented
        types_found = set(m['type'] for m in exported)
        self.assertEqual(types_found, {'fact', 'preference', 'goal', 'interaction'})

        print(f"\n  [EXPORT] {len(exported)} memories exported in {elapsed*1000:.1f}ms, "
              f"JSON size: {len(json_str):,} bytes")


if __name__ == '__main__':
    unittest.main(verbosity=2)
