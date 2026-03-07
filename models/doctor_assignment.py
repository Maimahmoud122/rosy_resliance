import uuid
from datetime import datetime
from app import db
import enum


class AssignmentStatus(enum.Enum):
    pending  = "pending"
    accepted = "accepted"
    rejected = "rejected"


class DoctorAssignment(db.Model):
    __tablename__ = "doctor_assignments"

    id         = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    doctor_id  = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    status     = db.Column(
        db.Enum(AssignmentStatus),
        nullable=False,
        default=AssignmentStatus.pending
    )
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=True)

    # ─── Relationships ────────────────────────────────────
    patient = db.relationship("User", foreign_keys=[patient_id])
    doctor  = db.relationship("User", foreign_keys=[doctor_id])

    def to_dict(self):
        return {
            "id":         str(self.id),
            "patient_id": str(self.patient_id),
            "doctor_id":  str(self.doctor_id),
            "status":     self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }