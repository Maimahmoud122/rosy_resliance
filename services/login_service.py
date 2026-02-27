from datetime import datetime
from app import db, bcrypt
from models import User, Doctor, UserRole, VerificationStatus
from flask_jwt_extended import create_access_token, create_refresh_token


# ══════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════

def _generate_tokens(user_id):
    access_token  = create_access_token(identity=str(user_id))
    refresh_token = create_refresh_token(identity=str(user_id))
    return access_token, refresh_token


def _update_last_login(user):
    user.last_login = datetime.utcnow()
    db.session.commit()


# ══════════════════════════════════════════════════════════
#  UNIFIED LOGIN — handles patient, doctor, and admin
# ══════════════════════════════════════════════════════════

def login_user(data):
    """
    Single login endpoint for all roles.
    Role is detected automatically from the database.

    Returns: (response_dict, http_status_code, tokens_or_None)
    tokens = (access_token, refresh_token) on success, None on failure
    """

    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    # 1. Validate required fields
    if not email or not password:
        return {"success": False, "message": "Email and password are required."}, 400, None

    # 2. Find user — same error for wrong email or wrong password
    #    (prevents attackers from knowing which emails are registered)
    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return {"success": False, "message": "Invalid email or password."}, 401, None

    # 3. Email must be verified for all roles
    if not user.email_verified:
        return {
            "success":    False,
            "message":    "Please verify your email before logging in.",
            "user_id":    str(user.user_id),
            "unverified": True,
        }, 403, None

    # 4. Run role-specific checks
    if user.role == UserRole.patient:
        return _patient_checks(user)

    elif user.role == UserRole.doctor:
        return _doctor_checks(user)

    elif user.role == UserRole.admin:
        return _admin_checks(user)

    return {"success": False, "message": "Unknown role."}, 400, None


# ══════════════════════════════════════════════════════════
#  ROLE-SPECIFIC CHECKS
# ══════════════════════════════════════════════════════════

def _patient_checks(user):
    if not user.is_active:
        return {
            "success": False,
            "message": "Your account has been deactivated. Please contact support."
        }, 403, None

    _update_last_login(user)
    access_token, refresh_token = _generate_tokens(user.user_id)

    return {
        "success": True,
        "message": f"Welcome back, {user.full_name}!",
        "role":    "patient",
        "user":    user.to_dict(),
    }, 200, (access_token, refresh_token)


def _doctor_checks(user):
    doctor = Doctor.query.get(user.user_id)

    if doctor.verification_status == VerificationStatus.pending:
        return {
            "success": False,
            "message": "Your account is pending admin approval. We will notify you by email once reviewed.",
            "status":  "pending_approval",
        }, 403, None

    if doctor.verification_status == VerificationStatus.rejected:
        return {
            "success": False,
            "message": "Your account was not approved. Please contact support.",
            "status":  "rejected",
        }, 403, None

    if not user.is_active:
        return {
            "success": False,
            "message": "Your account has been deactivated. Please contact support."
        }, 403, None

    _update_last_login(user)
    access_token, refresh_token = _generate_tokens(user.user_id)

    return {
        "success": True,
        "message": f"Welcome back, Dr. {user.full_name}!",
        "role":    "doctor",
        "user":    {**user.to_dict(), **doctor.to_dict()},
    }, 200, (access_token, refresh_token)


def _admin_checks(user):
    if not user.is_active:
        return {
            "success": False,
            "message": "Your account has been deactivated."
        }, 403, None

    _update_last_login(user)
    access_token, refresh_token = _generate_tokens(user.user_id)

    return {
        "success": True,
        "message": f"Welcome back, {user.full_name}!",
        "role":    "admin",
        "user":    user.to_dict(),
    }, 200, (access_token, refresh_token)


# ══════════════════════════════════════════════════════════
#  LOGOUT
# ══════════════════════════════════════════════════════════

def logout_user():
    return {"success": True, "message": "Logged out successfully."}, 200