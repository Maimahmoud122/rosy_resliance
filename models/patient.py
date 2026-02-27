import uuid
from datetime import datetime
from app import db
import enum



# ─── Patient Model ────────────────────────────────────────

class Patient(db.Model):
    __tablename__ = "patients"

    # PK is also FK to users.user_id (one-to-one)
    patient_id                  = db.Column(db.UUID(as_uuid=True), db.ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    current_assigned_doctor_id  = db.Column(db.UUID(as_uuid=True), db.ForeignKey("doctors.doctor_id", ondelete="SET NULL"), nullable=True)
    mental_health_mode  = db.Column(db.Boolean, nullable=False, default=False)
    whatsapp_number     = db.Column(db.String(30), nullable=True)   # for doctor contact

    # ─── Relationships ────────────────────────────────────
    user             = db.relationship("User",   back_populates="patient", foreign_keys=[patient_id])
    assigned_doctor  = db.relationship("Doctor", foreign_keys=[current_assigned_doctor_id])

    def to_dict(self):
        return {
            "patient_id":                 str(self.patient_id),
            "current_assigned_doctor_id": str(self.current_assigned_doctor_id) if self.current_assigned_doctor_id else None,
            "insurance_info":             self.insurance_info,
            "mental_health_mode":         self.mental_health_mode,
            "whatsapp_number":            self.whatsapp_number,
        }