from datetime import datetime
from app import db
from models import User, Doctor, UserRole, VerificationStatus
from services.email_service import send_doctor_approved_email, send_doctor_rejected_email
from flask_jwt_extended import get_jwt_identity


# ══════════════════════════════════════════════════════════
#  GET ALL PENDING DOCTORS
#  → Admin sees all doctors waiting for approval
# ══════════════════════════════════════════════════════════

def get_pending_doctors():
    """
    Returns all doctors with verification_status = pending
    who have already verified their email.
    """
    try:
        # Join Doctor + User to get full info
        pending_doctors = (
            db.session.query(Doctor, User)
            .join(User, Doctor.doctor_id == User.user_id)
            .filter(
                Doctor.verification_status == VerificationStatus.pending,
                User.email_verified        == True   # only show email-verified doctors
            )
            .order_by(User.created_at.asc())         # oldest first
            .all()
        )

        doctors_list = []
        for doctor, user in pending_doctors:
            doctors_list.append({
                **user.to_dict(),       # full_name, email, phone, gender etc.
                **doctor.to_dict(),     # specialization, hospital, bio etc.
            })

        return {
            "success": True,
            "count":   len(doctors_list),
            "doctors": doctors_list,
        }, 200

    except Exception as e:
        return {"success": False, "message": "Something went wrong.", "error": str(e)}, 500


# ══════════════════════════════════════════════════════════
#  GET ALL DOCTORS (with filter)
#  → Admin can view all doctors filtered by status
# ══════════════════════════════════════════════════════════

def get_all_doctors(status_filter=None):
    """
    Returns all doctors optionally filtered by verification_status.
    status_filter: 'pending' | 'verified' | 'rejected' | None (all)
    """
    try:
        query = (
            db.session.query(Doctor, User)
            .join(User, Doctor.doctor_id == User.user_id)
        )

        if status_filter:
            try:
                status_enum = VerificationStatus(status_filter)
                query = query.filter(Doctor.verification_status == status_enum)
            except ValueError:
                return {
                    "success": False,
                    "message": f"Invalid status. Must be: pending, verified, or rejected."
                }, 400

        doctors = query.order_by(User.created_at.desc()).all()

        doctors_list = [{**user.to_dict(), **doctor.to_dict()} for doctor, user in doctors]

        return {
            "success": True,
            "count":   len(doctors_list),
            "doctors": doctors_list,
        }, 200

    except Exception as e:
        return {"success": False, "message": "Something went wrong.", "error": str(e)}, 500


# ══════════════════════════════════════════════════════════
#  APPROVE DOCTOR
#  → Sets verification_status = verified
#  → Sets is_active = True (doctor can now log in)
#  → Sends approval email
# ══════════════════════════════════════════════════════════

def approve_doctor(doctor_id):
    """
    Args:
        doctor_id (str): the doctor's user_id / doctor_id

    Returns: (response_dict, http_status_code)
    """

    # Get the admin performing the action
    admin_id = get_jwt_identity()

    # Find doctor profile
    doctor = Doctor.query.get(doctor_id)
    if not doctor:
        return {"success": False, "message": "Doctor not found."}, 404

    # Find associated user
    user = User.query.get(doctor_id)
    if not user or user.role != UserRole.doctor:
        return {"success": False, "message": "Doctor account not found."}, 404

    # Check email is verified first
    if not user.email_verified:
        return {
            "success": False,
            "message": "Doctor has not verified their email yet. Cannot approve."
        }, 400

    # Check not already verified
    if doctor.verification_status == VerificationStatus.verified:
        return {"success": False, "message": "Doctor is already verified."}, 400

    try:
        # Approve the doctor
        doctor.verification_status = VerificationStatus.verified
        doctor.verified_by         = admin_id
        doctor.verification_date   = datetime.utcnow()

        # Activate the account so they can log in
        user.is_active = True

        db.session.commit()

        # Notify doctor by email
        send_doctor_approved_email(user.email, user.full_name)

        return {
            "success": True,
            "message": f"Dr. {user.full_name} has been approved and notified by email.",
            "doctor":  {**user.to_dict(), **doctor.to_dict()},
        }, 200

    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": "Something went wrong.", "error": str(e)}, 500


# ══════════════════════════════════════════════════════════
#  REJECT DOCTOR
#  → Sets verification_status = rejected
#  → is_active stays False
#  → Sends rejection email with reason
# ══════════════════════════════════════════════════════════

def reject_doctor(doctor_id, reason=None):
    """
    Args:
        doctor_id (str): the doctor's user_id / doctor_id
        reason    (str): optional rejection reason sent in email

    Returns: (response_dict, http_status_code)
    """

    admin_id = get_jwt_identity()

    doctor = Doctor.query.get(doctor_id)
    if not doctor:
        return {"success": False, "message": "Doctor not found."}, 404

    user = User.query.get(doctor_id)
    if not user or user.role != UserRole.doctor:
        return {"success": False, "message": "Doctor account not found."}, 404

    # Check not already rejected
    if doctor.verification_status == VerificationStatus.rejected:
        return {"success": False, "message": "Doctor account is already rejected."}, 400

    try:
        # Reject the doctor
        doctor.verification_status = VerificationStatus.rejected
        doctor.verified_by         = admin_id
        doctor.verification_date   = datetime.utcnow()

        # Keep is_active = False
        user.is_active = False

        db.session.commit()

        # Notify doctor by email with reason
        send_doctor_rejected_email(user.email, user.full_name, reason)

        return {
            "success": True,
            "message": f"Dr. {user.full_name} has been rejected and notified by email.",
            "doctor":  {**user.to_dict(), **doctor.to_dict()},
        }, 200

    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": "Something went wrong.", "error": str(e)}, 500