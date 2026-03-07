from datetime import datetime
from app import db
from models import User, Doctor, Patient, UserRole, VerificationStatus
from models.doctor_assignment import DoctorAssignment, AssignmentStatus
from flask_jwt_extended import get_jwt_identity


# ── Role check helpers ────────────────────────────────────

def _get_patient_or_error():
    """Returns (user, None) if patient, or (None, error_response) if not."""
    user_id = get_jwt_identity()
    user    = User.query.get(user_id)
    if user.role != UserRole.patient:
        return None, ({"success": False, "message": "Access denied. Patients only."}, 403)
    return user, None


def _get_doctor_or_error():
    """Returns (user, None) if doctor, or (None, error_response) if not."""
    user_id = get_jwt_identity()
    user    = User.query.get(user_id)
    if user.role != UserRole.doctor:
        return None, ({"success": False, "message": "Access denied. Doctors only."}, 403)
    return user, None


# ══════════════════════════════════════════════════════════
#  GET ALL VERIFIED DOCTORS
# ══════════════════════════════════════════════════════════

def get_all_doctors():
    user, error = _get_patient_or_error()
    if error:
        return error

    try:
        doctors = (
            db.session.query(Doctor, User)
            .join(User, Doctor.doctor_id == User.user_id)
            .filter(
                Doctor.verification_status == VerificationStatus.verified,
                User.is_active             == True,
            )
            .order_by(User.full_name.asc())
            .all()
        )

        doctors_list = [{
            "doctor_id":         str(doctor.doctor_id),
            "full_name":         user.full_name,
            "specialization":    doctor.specialization,
            "hospital":          doctor.hospital,
            "bio":               doctor.bio,
            "profile_image_url": doctor.profile_image_url,
        } for doctor, user in doctors]

        return {"success": True, "count": len(doctors_list), "doctors": doctors_list}, 200

    except Exception as e:
        return {"success": False, "message": "Something went wrong.", "error": str(e)}, 500


# ══════════════════════════════════════════════════════════
#  REQUEST DOCTOR ASSIGNMENT
# ══════════════════════════════════════════════════════════

def request_doctor_assignment(doctor_id):
    user, error = _get_patient_or_error()
    if error:
        return error

    patient_id = str(user.user_id)

    doctor = Doctor.query.get(doctor_id)
    if not doctor or doctor.verification_status != VerificationStatus.verified:
        return {"success": False, "message": "Doctor not found or not available."}, 404

    doctor_user = User.query.get(doctor_id)
    if not doctor_user or not doctor_user.is_active:
        return {"success": False, "message": "Doctor not found or not available."}, 404

    patient = Patient.query.get(patient_id)
    if patient.current_assigned_doctor_id:
        return {
            "success": False,
            "message": "You already have an assigned doctor. Remove them before requesting a new one.",
        }, 400

    existing = DoctorAssignment.query.filter_by(
        patient_id = patient_id,
        doctor_id  = doctor_id,
        status     = AssignmentStatus.pending,
    ).first()
    if existing:
        return {"success": False, "message": "You already have a pending request with this doctor."}, 400

    pending_count = DoctorAssignment.query.filter_by(
        patient_id = patient_id,
        status     = AssignmentStatus.pending,
    ).count()
    if pending_count >= 3:
        return {
            "success": False,
            "message": "You can only have 3 pending requests at a time.",
        }, 400

    try:
        assignment = DoctorAssignment(
            patient_id = patient_id,
            doctor_id  = doctor_id,
            status     = AssignmentStatus.pending,
        )
        db.session.add(assignment)
        db.session.commit()

        return {
            "success":    True,
            "message":    f"Request sent to Dr. {doctor_user.full_name}. Waiting for their approval.",
            "assignment": assignment.to_dict(),
        }, 201

    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": "Something went wrong.", "error": str(e)}, 500


# ══════════════════════════════════════════════════════════
#  GET PATIENT'S REQUESTS
# ══════════════════════════════════════════════════════════

def get_my_requests():
    user, error = _get_patient_or_error()
    if error:
        return error

    try:
        assignments = (
            DoctorAssignment.query
            .filter_by(patient_id=str(user.user_id))
            .order_by(DoctorAssignment.created_at.desc())
            .all()
        )

        result = []
        for a in assignments:
            doctor_user = User.query.get(a.doctor_id)
            doctor      = Doctor.query.get(a.doctor_id)
            result.append({
                "assignment_id": str(a.id),
                "status":        a.status.value,
                "created_at":    a.created_at.isoformat(),
                "doctor": {
                    "doctor_id":      str(a.doctor_id),
                    "full_name":      doctor_user.full_name,
                    "specialization": doctor.specialization,
                    "hospital":       doctor.hospital,
                }
            })

        return {"success": True, "requests": result}, 200

    except Exception as e:
        return {"success": False, "message": "Something went wrong.", "error": str(e)}, 500


# ══════════════════════════════════════════════════════════
#  CANCEL ASSIGNMENT REQUEST
# ══════════════════════════════════════════════════════════

def cancel_assignment_request(assignment_id):
    user, error = _get_patient_or_error()
    if error:
        return error

    assignment = DoctorAssignment.query.filter_by(
        id         = assignment_id,
        patient_id = str(user.user_id),
    ).first()

    if not assignment:
        return {"success": False, "message": "Request not found."}, 404

    if assignment.status != AssignmentStatus.pending:
        return {"success": False, "message": f"Cannot cancel a request that is already {assignment.status.value}."}, 400

    try:
        db.session.delete(assignment)
        db.session.commit()
        return {"success": True, "message": "Assignment request cancelled."}, 200

    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": "Something went wrong.", "error": str(e)}, 500


# ══════════════════════════════════════════════════════════
#  REMOVE ASSIGNED DOCTOR
# ══════════════════════════════════════════════════════════

def remove_assigned_doctor():
    user, error = _get_patient_or_error()
    if error:
        return error

    patient = Patient.query.get(str(user.user_id))
    if not patient.current_assigned_doctor_id:
        return {"success": False, "message": "You don't have an assigned doctor."}, 400

    try:
        patient.current_assigned_doctor_id = None
        db.session.commit()
        return {"success": True, "message": "Doctor removed successfully."}, 200

    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": "Something went wrong.", "error": str(e)}, 500


# ══════════════════════════════════════════════════════════
#  GET DOCTOR'S PENDING REQUESTS
# ══════════════════════════════════════════════════════════

def get_doctor_pending_requests():
    user, error = _get_doctor_or_error()
    if error:
        return error

    try:
        assignments = (
            DoctorAssignment.query
            .filter_by(doctor_id=str(user.user_id), status=AssignmentStatus.pending)
            .order_by(DoctorAssignment.created_at.asc())
            .all()
        )

        result = []
        for a in assignments:
            patient_user = User.query.get(a.patient_id)
            patient      = Patient.query.get(a.patient_id)
            result.append({
                "assignment_id": str(a.id),
                "created_at":    a.created_at.isoformat(),
                "patient": {
                    "patient_id":      str(a.patient_id),
                    "full_name":       patient_user.full_name,
                    "email":           patient_user.email,
                    "phone_number":    patient_user.phone_number,
                    "gender":          patient_user.gender.value if patient_user.gender else None,
                    "whatsapp_number": patient.whatsapp_number,
                }
            })

        return {"success": True, "count": len(result), "requests": result}, 200

    except Exception as e:
        return {"success": False, "message": "Something went wrong.", "error": str(e)}, 500


# ══════════════════════════════════════════════════════════
#  ACCEPT ASSIGNMENT
# ══════════════════════════════════════════════════════════

def accept_assignment(assignment_id):
    user, error = _get_doctor_or_error()
    if error:
        return error

    assignment = DoctorAssignment.query.filter_by(
        id        = assignment_id,
        doctor_id = str(user.user_id),
        status    = AssignmentStatus.pending,
    ).first()

    if not assignment:
        return {"success": False, "message": "Request not found or already responded to."}, 404

    try:
        assignment.status     = AssignmentStatus.accepted
        assignment.updated_at = datetime.utcnow()

        patient = Patient.query.get(assignment.patient_id)
        patient.current_assigned_doctor_id = str(user.user_id)

        # Reject all other pending requests from this patient
        DoctorAssignment.query.filter(
            DoctorAssignment.patient_id == assignment.patient_id,
            DoctorAssignment.id         != assignment_id,
            DoctorAssignment.status     == AssignmentStatus.pending,
        ).update({"status": AssignmentStatus.rejected, "updated_at": datetime.utcnow()})

        db.session.commit()

        patient_user = User.query.get(assignment.patient_id)
        return {
            "success":    True,
            "message":    f"You have accepted {patient_user.full_name} as your patient.",
            "assignment": assignment.to_dict(),
        }, 200

    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": "Something went wrong.", "error": str(e)}, 500


# ══════════════════════════════════════════════════════════
#  REJECT ASSIGNMENT
# ══════════════════════════════════════════════════════════

def reject_assignment(assignment_id):
    user, error = _get_doctor_or_error()
    if error:
        return error

    assignment = DoctorAssignment.query.filter_by(
        id        = assignment_id,
        doctor_id = str(user.user_id),
        status    = AssignmentStatus.pending,
    ).first()

    if not assignment:
        return {"success": False, "message": "Request not found or already responded to."}, 404

    try:
        assignment.status     = AssignmentStatus.rejected
        assignment.updated_at = datetime.utcnow()
        db.session.commit()

        patient_user = User.query.get(assignment.patient_id)
        return {
            "success":    True,
            "message":    f"You have rejected the request from {patient_user.full_name}.",
            "assignment": assignment.to_dict(),
        }, 200

    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": "Something went wrong.", "error": str(e)}, 500