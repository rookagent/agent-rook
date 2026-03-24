"""
Promo Code models — promotional codes that grant free credits or premium days.

Tables:
  promo_codes: id, code, description, premium_days, bonus_credits, max_uses, current_uses, expires_at, is_active, created_at
  promo_redemptions: id, promo_code_id, user_id, premium_days_granted, credits_granted, premium_expires_at, redeemed_at
"""
from datetime import datetime
from app.extensions import db


class PromoCode(db.Model):
    __tablename__ = 'promo_codes'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    premium_days = db.Column(db.Integer, nullable=True, default=0)  # Grant subscription days
    bonus_credits = db.Column(db.Integer, nullable=True, default=0)  # Grant credits
    max_uses = db.Column(db.Integer, nullable=True)
    current_uses = db.Column(db.Integer, default=0)
    expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    redemptions = db.relationship('PromoRedemption', backref='promo_code', lazy='dynamic')

    def is_valid(self):
        if not self.is_active:
            return False, "This promo code is no longer active"
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False, "This promo code has expired"
        if self.max_uses and (self.current_uses or 0) >= self.max_uses:
            return False, "This promo code has reached its usage limit"
        return True, "Valid"

    def to_dict(self, include_stats=False):
        data = {
            'id': self.id,
            'code': self.code,
            'description': self.description,
            'premium_days': self.premium_days or 0,
            'bonus_credits': self.bonus_credits or 0,
            'max_uses': self.max_uses,
            'current_uses': self.current_uses or 0,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active,
            'is_valid': self.is_valid()[0],
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if include_stats:
            data['redemptions'] = [
                r.to_dict() for r in self.redemptions.order_by(
                    PromoRedemption.redeemed_at.desc()
                ).limit(10)
            ]
        return data


class PromoRedemption(db.Model):
    """
    Tracks each promo code use.

    Design note: In multi-account-type systems (e.g. separate provider and parent
    tables), a common pattern is to use the sign of user_id to distinguish account
    types (positive = primary, negative = secondary) without needing an extra column.
    Agent Rook uses a single User model, so user_id is always a direct FK to users.id.
    """
    __tablename__ = 'promo_redemptions'

    id = db.Column(db.Integer, primary_key=True)
    promo_code_id = db.Column(db.Integer, db.ForeignKey('promo_codes.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    premium_days_granted = db.Column(db.Integer, nullable=True)
    credits_granted = db.Column(db.Integer, nullable=True)
    premium_expires_at = db.Column(db.DateTime, nullable=True)
    redeemed_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('promo_redemptions', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_email': self.user.email if self.user else None,
            'premium_days_granted': self.premium_days_granted,
            'credits_granted': self.credits_granted,
            'premium_expires_at': self.premium_expires_at.isoformat() if self.premium_expires_at else None,
            'redeemed_at': self.redeemed_at.isoformat() if self.redeemed_at else None,
        }
