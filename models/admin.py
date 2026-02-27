from app import db


# ─── Admin Model ──────────────────────────────────────────

class Admin(db.Model):
    __tablename__ = "admins"

    # PK is also FK to users.user_id (one-to-one)
    admin_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)

    # ─── Relationships ────────────────────────────────────
    user = db.relationship("User", back_populates="admin", foreign_keys=[admin_id])

    def to_dict(self):
        return {
            "admin_id": str(self.admin_id),
        }