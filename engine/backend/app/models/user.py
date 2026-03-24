"""
User model for Agent Rook.
Supports admin and regular user roles with optional premium subscriptions and credits.
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(db.Model):
    """
    User accounts. Roles: admin, user.
    Premium access via subscription or pay-as-you-go credits.
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(20), nullable=False, default='user')  # user|admin
    verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100), unique=True)

    phone = db.Column(db.String(20), nullable=True)

    # Password reset
    password_reset_token = db.Column(db.String(100), unique=True, nullable=True)
    password_reset_expires = db.Column(db.DateTime, nullable=True)

    # Subscription
    subscription_tier = db.Column(db.String(20), default='free', index=True)  # free|premium
    subscription_expires_at = db.Column(db.DateTime, index=True)
    subscription_permanent = db.Column(db.Boolean, default=False)  # True = free for life (promo)
    stripe_customer_id = db.Column(db.String(100))

    # Credits (pay-as-you-go): 1 credit = 1 agent message
    credits = db.Column(db.Integer, default=0, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Timezone (IANA name, e.g. 'America/New_York')
    timezone = db.Column(db.String(50), default='UTC')

    last_login = db.Column(db.DateTime, nullable=True)
    signup_source = db.Column(db.String(50), nullable=True)

    # Relationships
    subscription = db.relationship('Subscription', back_populates='user', uselist=False)

    def set_password(self, password):
        """Hash and set password using pbkdf2."""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        """Verify password against stored hash."""
        return check_password_hash(self.password_hash, password)

    def is_premium(self):
        """Check if user has active premium subscription."""
        if self.subscription_tier != 'premium':
            return False
        if self.subscription_permanent:
            return True
        if not self.subscription_expires_at:
            return False
        return self.subscription_expires_at > datetime.utcnow()

    def has_pro_access(self):
        """Check if user can access pro features (admin OR credits > 0 OR active subscription)."""
        try:
            user_credits = getattr(self, 'credits', 0) or 0
            return self.role == 'admin' or self.is_premium() or user_credits > 0
        except Exception:
            return self.role == 'admin' or self.is_premium()

    def has_credits(self):
        """Check if user has any credits remaining."""
        try:
            return (getattr(self, 'credits', 0) or 0) > 0
        except Exception:
            return False

    def use_credit(self):
        """Atomically deduct 1 credit. Returns True if successful, False if no credits."""
        try:
            from app.extensions import db
            result = db.session.execute(
                db.text("UPDATE users SET credits = credits - 1 WHERE id = :uid AND credits > 0"),
                {'uid': self.id}
            )
            db.session.commit()
            if result.rowcount > 0:
                db.session.refresh(self)
                return True
            return False
        except Exception:
            return False

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'

    def to_dict(self, include_sensitive=False):
        """Convert to dictionary for API responses."""
        data = {
            'id': self.id,
            'email': self.email,
            'role': self.role,
            'verified': self.verified,
            'subscription_tier': self.subscription_tier,
            'subscription_permanent': self.subscription_permanent or False,
            'is_premium': self.is_premium(),
            'credits': self.credits,
            'timezone': self.timezone or 'UTC',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }

        if include_sensitive:
            data['phone'] = self.phone
            data['subscription_expires_at'] = (
                self.subscription_expires_at.isoformat() if self.subscription_expires_at else None
            )

        return data
