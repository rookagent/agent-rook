"""
Checklist model — reusable checklists with checkable items.
Used for gear checklists, packing lists, prep lists, etc.
Items stored as JSON array: [{"name": "Camera body", "checked": false}, ...]
"""
import json
from datetime import datetime
from app.extensions import db


class Checklist(db.Model):
    __tablename__ = 'checklists'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(255), nullable=False)
    shoot_type = db.Column(db.String(50))  # wedding, portrait, mini, etc.
    items = db.Column(db.Text, default='[]')  # JSON array
    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('checklists', lazy='dynamic'))

    def get_items(self):
        if not self.items:
            return []
        try:
            return json.loads(self.items)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_items(self, items_list):
        self.items = json.dumps(items_list) if items_list else '[]'

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'shoot_type': self.shoot_type,
            'items': self.get_items(),
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
