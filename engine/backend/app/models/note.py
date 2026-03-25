"""
Note model — searchable, taggable markdown notes.
"""
import json
from datetime import datetime
from app.extensions import db


class Note(db.Model):
    __tablename__ = 'notes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text)  # markdown
    tags = db.Column(db.Text)
    is_pinned = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('notes', lazy='dynamic'))

    def to_dict(self):
        tags = []
        if self.tags:
            try:
                tags = json.loads(self.tags)
            except (json.JSONDecodeError, TypeError):
                pass
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'tags': tags,
            'is_pinned': self.is_pinned,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
