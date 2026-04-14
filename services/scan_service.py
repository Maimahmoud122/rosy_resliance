import os
import tempfile
from app import db
from models import User, UserRole, Patient
from models.scan import Scan, PredictionClass, ImageType
from services.ml_service import predict
from services.cloudinary_service import validate_scan_image, upload_scan_image, delete_scan_image
from flask_jwt_extended import get_jwt_identity

VALID_IMAGE_TYPES = [t.value for t in ImageType]


# ══════════════════════════════════════════════════════════
#  UPLOAD SCAN + GET DIAGNOSIS
# ══════════════════════════════════════════════════════════

def upload_scan(file, image_type):
    """
    Full pipeline for both ultrasound and mammogram images.

    Args:
        file       (FileStorage): image from request.files["image"]
        image_type (str):         "ultrasound" or "mammogram"

    Returns: (response_dict, http_status_code)
    """

    # 1. Validate role
    user_id = get_jwt_identity()
    user    = User.query.get(user_id)

    if user.role != UserRole.patient:
        return {"success": False, "message": "Access denied. Patients only."}, 403

    # 2. Validate image type
    if image_type not in VALID_IMAGE_TYPES:
        return {
            "success": False,
            "message": f"Invalid image_type. Must be one of: {', '.join(VALID_IMAGE_TYPES)}."
        }, 400

    # 3. Validate file
    is_valid, error_msg = validate_scan_image(file)
    if not is_valid:
        return {"success": False, "message": error_msg}, 400

    tmp_path = None

    try:
        # 4. Save to temp file for ML model
        suffix = "." + file.filename.rsplit(".", 1)[-1].lower()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            file.save(tmp)
            tmp_path = tmp.name

        # 5. Run prediction with the correct model
        prediction_result = predict(tmp_path, image_type)

        # 6. Upload to Cloudinary (organized by image type)
        file.seek(0)
        image_url, public_id = upload_scan_image(file, user_id, image_type)

        # 7. Save to database
        probabilities = prediction_result["probabilities"]

        scan = Scan(
            patient_id      = user_id,
            image_type      = ImageType(image_type),
            image_url       = image_url,
            image_public_id = public_id,
            prediction      = PredictionClass(prediction_result["predicted_class"]),
            confidence      = prediction_result["confidence"],
            prob_benign     = probabilities["benign"],
            prob_malignant  = probabilities["malignant"],
            prob_normal     = probabilities["normal"],
            model_version   = prediction_result["model_version"],
        )
        db.session.add(scan)
        db.session.commit()

        return {
            "success":   True,
            "message":   f"{image_type.capitalize()} scan analyzed successfully.",
            "diagnosis": scan.to_dict(),
        }, 201

    except FileNotFoundError as e:
        return {
            "success": False,
            "message": "Diagnosis service is currently unavailable. Please try again later.",
            "error":   str(e)
        }, 503

    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": "Something went wrong.", "error": str(e)}, 500

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


# ══════════════════════════════════════════════════════════
#  GET MY SCANS (with optional type filter)
# ══════════════════════════════════════════════════════════

def get_my_scans(image_type=None):
    """
    Returns patient's scan history.
    Optionally filter by image_type: ?type=ultrasound or ?type=mammogram
    """
    user_id = get_jwt_identity()
    user    = User.query.get(user_id)

    if user.role != UserRole.patient:
        return {"success": False, "message": "Access denied. Patients only."}, 403

    try:
        query = Scan.query.filter_by(patient_id=user_id)

        if image_type:
            if image_type not in VALID_IMAGE_TYPES:
                return {
                    "success": False,
                    "message": f"Invalid type filter. Must be: {', '.join(VALID_IMAGE_TYPES)}."
                }, 400
            query = query.filter_by(image_type=ImageType(image_type))

        scans = query.order_by(Scan.created_at.desc()).all()

        return {
            "success": True,
            "count":   len(scans),
            "scans":   [s.to_dict() for s in scans],
        }, 200

    except Exception as e:
        return {"success": False, "message": "Something went wrong.", "error": str(e)}, 500


# ══════════════════════════════════════════════════════════
#  GET SINGLE SCAN
# ══════════════════════════════════════════════════════════

def get_scan_by_id(scan_id):
    """Patient or their assigned doctor can view a single scan."""
    user_id = get_jwt_identity()
    user    = User.query.get(user_id)

    scan = Scan.query.get(scan_id)
    if not scan:
        return {"success": False, "message": "Scan not found."}, 404

    if user.role == UserRole.patient and str(scan.patient_id) != user_id:
        return {"success": False, "message": "Access denied."}, 403

    if user.role == UserRole.doctor:
        patient = Patient.query.get(str(scan.patient_id))
        if not patient or str(patient.current_assigned_doctor_id) != user_id:
            return {"success": False, "message": "Access denied."}, 403

    return {"success": True, "scan": scan.to_dict()}, 200


# ══════════════════════════════════════════════════════════
#  GET PATIENT SCANS — DOCTOR VIEW
# ══════════════════════════════════════════════════════════

def get_patient_scans(patient_id, image_type=None):
    """Doctor views scans of their assigned patient. Optional type filter."""
    user_id = get_jwt_identity()
    user    = User.query.get(user_id)

    if user.role != UserRole.doctor:
        return {"success": False, "message": "Access denied. Doctors only."}, 403

    patient = Patient.query.get(patient_id)
    if not patient or str(patient.current_assigned_doctor_id) != user_id:
        return {"success": False, "message": "This patient is not assigned to you."}, 403

    try:
        query = Scan.query.filter_by(patient_id=patient_id)

        if image_type:
            if image_type not in VALID_IMAGE_TYPES:
                return {
                    "success": False,
                    "message": f"Invalid type filter. Must be: {', '.join(VALID_IMAGE_TYPES)}."
                }, 400
            query = query.filter_by(image_type=ImageType(image_type))

        scans        = query.order_by(Scan.created_at.desc()).all()
        patient_user = User.query.get(patient_id)

        return {
            "success": True,
            "patient": {
                "patient_id": patient_id,
                "full_name":  patient_user.full_name,
            },
            "count": len(scans),
            "scans": [s.to_dict() for s in scans],
        }, 200

    except Exception as e:
        return {"success": False, "message": "Something went wrong.", "error": str(e)}, 500


# ══════════════════════════════════════════════════════════
#  DELETE SCAN
# ══════════════════════════════════════════════════════════

def delete_scan(scan_id):
    """Patient deletes their own scan + removes from Cloudinary."""
    user_id = get_jwt_identity()
    user    = User.query.get(user_id)

    if user.role != UserRole.patient:
        return {"success": False, "message": "Access denied. Patients only."}, 403

    scan = Scan.query.filter_by(scan_id=scan_id, patient_id=user_id).first()
    if not scan:
        return {"success": False, "message": "Scan not found."}, 404

    try:
        delete_scan_image(scan.image_public_id)
        db.session.delete(scan)
        db.session.commit()
        return {"success": True, "message": "Scan deleted successfully."}, 200

    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": "Something went wrong.", "error": str(e)}, 500