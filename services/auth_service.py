import random
from datetime import datetime
from app import db, bcrypt
from models import User, Patient, UserRole, GenderEnum
from models.email_verification import EmailVerification
from services.email_service import send_verification_email
from flask_jwt_extended import create_access_token, create_refresh_token

# ── Bcrypt salt rounds ────────────────────────────────────
SALT_ROUNDS = 12


# ══════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════

def generate_verification_code():
    """Returns a random 6-digit string."""
    return str(random.randint(100000, 999999))


def validate_patient_signup(data):
    """Returns list of error messages. Empty list = valid."""
    errors = []

    required = ["full_name", "email", "password", "confirm_password"]
    for field in required:
        if not data.get(field, "").strip():
            errors.append(f"{field} is required.")

    if errors:
        return errors

    if "@" not in data["email"] or "." not in data["email"]:
        errors.append("Invalid email address.")

    if len(data["password"]) < 8:
        errors.append("Password must be at least 8 characters.")

    if data["password"] != data["confirm_password"]:
        errors.append("Passwords do not match.")

    if data.get("gender"):
        valid_genders = [g.value for g in GenderEnum]
        if data["gender"] not in valid_genders:
            errors.append(f"gender must be one of: {', '.join(valid_genders)}.")

    if data.get("date_of_birth"):
        try:
            datetime.strptime(data["date_of_birth"], "%Y-%m-%d")
        except ValueError:
            errors.append("date_of_birth must be in YYYY-MM-DD format.")

    return errors


# ══════════════════════════════════════════════════════════
#  SIGNUP
#  → Creates User + Patient
#  → Sends 6-digit code
#  → Returns user_id as 3rd value so route stores in cookie
# ══════════════════════════════════════════════════════════

def signup_patient(data):
    """
    Returns: (response_dict, http_status_code, user_id_for_cookie)
    user_id_for_cookie is None on failure
    """
    errors = validate_patient_signup(data)
    if errors:
        return {"success": False, "errors": errors}, 422, None

    # if User.query.filter_by(email=data["email"].lower().strip()).first():
    #     return {"success": False, "message": "An account with this email already exists."}, 409, None

    try:
        dob = None
        if data.get("date_of_birth"):
            dob = datetime.strptime(data["date_of_birth"], "%Y-%m-%d").date()

        gender = None
        if data.get("gender"):
            gender = GenderEnum(data["gender"])

        password_hash = bcrypt.generate_password_hash(
            data["password"], rounds=SALT_ROUNDS
        ).decode("utf-8")

        user = User(
            email          = data["email"].lower().strip(),
            password_hash  = password_hash,
            role           = UserRole.patient,
            full_name      = data["full_name"].strip(),
            gender         = gender,
            date_of_birth  = dob,
            phone_number   = data.get("phone_number", "").strip() or None,
            is_active      = True,
            email_verified = False,
        )
        db.session.add(user)
        db.session.flush()

        patient = Patient(
            patient_id         = user.user_id,
            mental_health_mode = bool(data.get("mental_health_mode", False)),
            whatsapp_number    = data.get("whatsapp_number", "").strip() or None,
        )
        db.session.add(patient)

        code = generate_verification_code()
        verification = EmailVerification(
            user_id    = user.user_id,
            code       = code,
            expires_at = EmailVerification.generate_expiry(),
        )
        db.session.add(verification)
        db.session.commit()

        send_verification_email(user.email, user.full_name, code)

        # Return user_id as 3rd value — route will set it as a cookie
        return {
            "success": True,
            "message": "Account created! A 6-digit verification code has been sent to your email.",
        }, 201, str(user.user_id)

    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": "Something went wrong.", "error": str(e)}, 500, None


# ══════════════════════════════════════════════════════════
#  VERIFY EMAIL
#  → Reads user_id from cookie (not from request body)
#  → On success: returns JWT tokens + signals route to clear cookie
# ══════════════════════════════════════════════════════════

def verify_email(code, user_id):
    """
    Args:
        code    (str): 6-digit code submitted by the user
        user_id (str): extracted from the signup_session cookie

    Returns: (response_dict, http_status_code, should_clear_cookie)
    """

    if not user_id:
        return {
            "success": False,
            "message": "Session expired. Please sign up again."
        }, 401, False

    if not code or not code.strip():
        return {"success": False, "message": "Verification code is required."}, 400, False

    verification = (
        EmailVerification.query
        .filter_by(user_id=user_id, is_used=False)
        .order_by(EmailVerification.created_at.desc())
        .first()
    )

    if not verification:
        return {
            "success": False,
            "message": "No active verification code found. Please request a new one."
        }, 404, False

    if verification.is_expired():
        return {
            "success": False,
            "message": "This code has expired. Please request a new one."
        }, 410, False

    if verification.code != code.strip():
        return {"success": False, "message": "Invalid verification code."}, 400, False

    try:
        verification.is_used = True

        user = User.query.get(user_id)
        user.email_verified = True
        user.last_login = datetime.utcnow()

        db.session.commit()

        # Generate JWT tokens — user is now fully authenticated
        access_token  = create_access_token(identity=str(user.user_id))
        refresh_token = create_refresh_token(identity=str(user.user_id))

        return {
            "success":       True,
            "message":       f"Email verified! Welcome, {user.full_name}!",
            "access_token":  access_token,
            "refresh_token": refresh_token,
            "user":          user.to_dict(),
        }, 200, True   # True = clear the signup_session cookie

    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": "Something went wrong.", "error": str(e)}, 500, False


# ══════════════════════════════════════════════════════════
#  RESEND CODE
#  → Also reads user_id from cookie
# ══════════════════════════════════════════════════════════

def resend_verification_code(user_id):
    """
    Args:
        user_id (str): extracted from the signup_session cookie

    Returns: (response_dict, http_status_code)
    """

    if not user_id:
        return {
            "success": False,
            "message": "Session expired. Please sign up again."
        }, 401

    user = User.query.get(user_id)
    if not user:
        return {"success": False, "message": "User not found."}, 404

    if user.email_verified:
        return {"success": False, "message": "This email is already verified."}, 400

    try:
        # Invalidate all previous unused codes
        EmailVerification.query.filter_by(
            user_id=user_id, is_used=False
        ).update({"is_used": True})

        code = generate_verification_code()
        verification = EmailVerification(
            user_id    = user_id,
            code       = code,
            expires_at = EmailVerification.generate_expiry(),
        )
        db.session.add(verification)
        db.session.commit()

        send_verification_email(user.email, user.full_name, code)

        return {
            "success": True,
            "message": "A new verification code has been sent to your email.",
        }, 200

    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": "Something went wrong.", "error": str(e)}, 500