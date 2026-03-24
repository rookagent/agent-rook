"""
Stripe subscription tracking.
Complements user.subscription_tier with detailed Stripe data.
"""
from datetime import datetime
from app.extensions import db


class Subscription(db.Model):
    """
    Stripe subscription details for premium users.
    Synced via Stripe webhooks.
    """
    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    stripe_subscription_id = db.Column(db.String(100), unique=True)
    plan = db.Column(db.String(30))  # premium_monthly|premium_annual
    status = db.Column(db.String(30))  # active|canceled|past_due|trialing

    current_period_end = db.Column(db.DateTime)
    cancel_at_period_end = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = db.relationship('User', back_populates='subscription')

    def __repr__(self):
        return f'<Subscription {self.stripe_subscription_id} - {self.status}>'

    def to_dict(self):
        return {
            'id': self.id,
            'plan': self.plan,
            'status': self.status,
            'current_period_end': self.current_period_end.isoformat() if self.current_period_end else None,
            'cancel_at_period_end': self.cancel_at_period_end,
        }
