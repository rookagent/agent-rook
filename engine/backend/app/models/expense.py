"""
Expense model — track business expenses with category, amount, date.
"""
import json
from datetime import datetime
from app.extensions import db


class Expense(db.Model):
    __tablename__ = 'expenses'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50))  # gear, travel, software, marketing, education, meals, other
    date = db.Column(db.Date, nullable=False, index=True)
    vendor = db.Column(db.String(255))
    notes = db.Column(db.Text)
    tags = db.Column(db.Text)  # JSON list
    is_deductible = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('expenses', lazy='dynamic'))

    def to_dict(self):
        tags = []
        if self.tags:
            try:
                tags = json.loads(self.tags)
            except (json.JSONDecodeError, TypeError):
                pass
        return {
            'id': self.id,
            'description': self.description,
            'amount': self.amount,
            'category': self.category,
            'date': self.date.isoformat() if self.date else None,
            'vendor': self.vendor,
            'notes': self.notes,
            'tags': tags,
            'is_deductible': self.is_deductible,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
