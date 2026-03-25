"""
Session Plan model — structured timelines for photo sessions.
Blocks stored as JSON: [{"time": "3:00 PM", "duration": 30, "activity": "First look", "notes": "..."}, ...]
"""
import json
from datetime import datetime
from app.extensions import db


class SessionPlan(db.Model):
    __tablename__ = 'session_plans'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(255), nullable=False)
    session_type = db.Column(db.String(50))
    date = db.Column(db.Date)
    location = db.Column(db.String(255))
    client_name = db.Column(db.String(255))
    blocks = db.Column(db.Text, default='[]')  # JSON array of time blocks
    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('session_plans', lazy='dynamic'))

    def get_blocks(self):
        if not self.blocks:
            return []
        try:
            return json.loads(self.blocks)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_blocks(self, blocks_list):
        self.blocks = json.dumps(blocks_list) if blocks_list else '[]'

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'session_type': self.session_type,
            'date': self.date.isoformat() if self.date else None,
            'location': self.location,
            'client_name': self.client_name,
            'blocks': self.get_blocks(),
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
