import uuid
from datetime import datetime
from app import db
import enum


class ImageType(enum.Enum):
    ultrasound = "ultrasound"
    mammogram  = "mammogram"


class PredictionClass(enum.Enum):
    benign    = "benign"
    malignant = "malignant"
    normal    = "normal"


class Scan(db.Model):
    __tablename__ = "scans"

    scan_id         = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id      = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    image_type      = db.Column(db.Enum(ImageType),       nullable=False)   # ultrasound | mammogram
    image_url       = db.Column(db.String(500),            nullable=False)   # Cloudinary URL
    image_public_id = db.Column(db.String(300),            nullable=False)   # Cloudinary public_id
    prediction      = db.Column(db.Enum(PredictionClass),  nullable=False)
    confidence      = db.Column(db.Float,                  nullable=False)
    prob_benign     = db.Column(db.Float,                  nullable=False)
    prob_malignant  = db.Column(db.Float,                  nullable=False)
    prob_normal     = db.Column(db.Float,                  nullable=False)
    model_version   = db.Column(db.String(50),             nullable=False)
    created_at      = db.Column(db.DateTime,               nullable=False, default=datetime.utcnow)

    patient = db.relationship("User", foreign_keys=[patient_id])

    def to_dict(self):
        return {
            "scan_id":       str(self.scan_id),
            "patient_id":    str(self.patient_id),
            "image_type":    self.image_type.value,
            "image_url":     self.image_url,
            "prediction":    self.prediction.value,
            "confidence":    self.confidence,
            "probabilities": {
                "benign":    self.prob_benign,
                "malignant": self.prob_malignant,
                "normal":    self.prob_normal,
            },
            "model_version": self.model_version,
            "created_at":    self.created_at.isoformat(),
        }
