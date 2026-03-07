import uuid
from datetime import datetime
from app import db
import enum


# ─── Enums ────────────────────────────────────────────────

class UserRole(enum.Enum):
    patient = "patient"
    doctor  = "doctor"
    admin   = "admin"

class GenderEnum(enum.Enum):
    male   = "male"
    female = "female"
    other  = "other"


# ─── User Model ───────────────────────────────────────────

class User(db.Model):
    __tablename__ = "users"

    user_id        = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email          = db.Column(db.String(255), nullable=False, unique=False)
    password_hash  = db.Column(db.Text, nullable=False)
    role           = db.Column(db.Enum(UserRole), nullable=False)
    full_name      = db.Column(db.String(150), nullable=False)
    gender         = db.Column(db.Enum(GenderEnum), nullable=True)
    date_of_birth  = db.Column(db.Date, nullable=True)
    phone_number   = db.Column(db.String(30), nullable=True)
    created_at     = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_active      = db.Column(db.Boolean, nullable=False, default=True)
    email_verified = db.Column(db.Boolean, nullable=False, default=False)
    last_login     = db.Column(db.DateTime, nullable=True)

    # ─── Relationships ────────────────────────────────────
    doctor  = db.relationship("Doctor",  back_populates="user", uselist=False, cascade="all, delete-orphan", foreign_keys="Doctor.doctor_id")
    patient = db.relationship("Patient", back_populates="user", uselist=False, cascade="all, delete-orphan", foreign_keys="Patient.patient_id")
    admin   = db.relationship("Admin",   back_populates="user", uselist=False, cascade="all, delete-orphan", foreign_keys="Admin.admin_id")

    def to_dict(self):
        return {
            "user_id":        str(self.user_id),
            "email":          self.email,
            "role":           self.role.value,
            "full_name":      self.full_name,
            "gender":         self.gender.value if self.gender else None,
            "date_of_birth":  self.date_of_birth.isoformat() if self.date_of_birth else None,
            "phone_number":   self.phone_number,
            "is_active":      self.is_active,
            "email_verified": self.email_verified,
            "created_at":     self.created_at.isoformat()
        }