"""
Schedule Event model — calendar entries. Label configurable via agent.yaml.
A photographer sees "Shoots", a chef sees "Bookings", etc.
"""
import json
from datetime import datetime
from app.extensions import db


class ScheduleEvent(db.Model):
    __tablename__ = 'schedule_events'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    all_day = db.Column(db.Boolean, default=False)
    tags = db.Column(db.Text)
    color = db.Column(db.String(7))  # hex color, e.g. "#E94560"

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('schedule_events', lazy='dynamic'))

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
            'description': self.description,
            'date': self.date.isoformat() if self.date else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'all_day': self.all_day,
            'tags': tags,
            'color': self.color,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
