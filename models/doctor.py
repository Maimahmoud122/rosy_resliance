import uuid
from datetime import datetime
from app import db
import enum


# ─── Enums ────────────────────────────────────────────────

class VerificationStatus(enum.Enum):
    pending  = "pending"
    verified = "verified"
    rejected = "rejected"


# ─── Doctor Model ─────────────────────────────────────────

class Doctor(db.Model):
    __tablename__ = "doctors"

    # PK is also FK to users.user_id (one-to-one)
    doctor_id           = db.Column(db.UUID(as_uuid=True), db.ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)

    specialization      = db.Column(db.String(100), nullable=True)   # e.g. Oncologist, Radiologist
    hospital            = db.Column(db.String(150), nullable=True)
    verification_status = db.Column(db.Enum(VerificationStatus), nullable=False, default=VerificationStatus.pending)
    verified_by         = db.Column(db.UUID(as_uuid=True), db.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)  # admin who verified
    verification_date   = db.Column(db.DateTime, nullable=True)
    whatsapp_number     = db.Column(db.String(30), nullable=True)
    bio                 = db.Column(db.Text, nullable=True)
    profile_image_url   = db.Column(db.String(500), nullable=True)

    # ─── Relationships ────────────────────────────────────
    user         = db.relationship("User",  back_populates="doctor", foreign_keys=[doctor_id])
    verified_by_admin = db.relationship("User", foreign_keys=[verified_by])

    def to_dict(self):
        return {
            "doctor_id":           str(self.doctor_id),
            "specialization":      self.specialization,
            "hospital":            self.hospital,
            "verification_status": self.verification_status.value,
            "verification_date":   self.verification_date.isoformat() if self.verification_date else None,
            "whatsapp_number":     self.whatsapp_number,
            "bio":                 self.bio,
            "profile_image_url":   self.profile_image_url,
        }