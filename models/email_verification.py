import uuid
from datetime import datetime, timedelta
from app import db


class EmailVerification(db.Model):
    __tablename__ = "email_verifications"

    id         = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    code       = db.Column(db.String(6),  nullable=False)   # 6-digit code
    expires_at = db.Column(db.DateTime,   nullable=False)   # valid for 10 minutes
    is_used    = db.Column(db.Boolean,    nullable=False, default=False)
    created_at = db.Column(db.DateTime,   nullable=False, default=datetime.utcnow)

    user = db.relationship("User", foreign_keys=[user_id])

    @staticmethod
    def generate_expiry():
        """Returns a timestamp 10 minutes from now."""
        return datetime.utcnow() + timedelta(minutes=10)

    def is_expired(self):
        """Returns True if the code has passed its expiry time."""
        return datetime.utcnow() > self.expires_at