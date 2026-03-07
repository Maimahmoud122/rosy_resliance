import random
from datetime import datetime
from app import db, bcrypt
from models import User, Doctor, UserRole, GenderEnum, VerificationStatus
from models.email_verification import EmailVerification
from services.email_service import send_verification_email, send_doctor_pending_email
from flask_jwt_extended import create_access_token, create_refresh_token

SALT_ROUNDS = 12


# ══════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════

def generate_verification_code():
    return str(random.randint(100000, 999999))


def validate_doctor_signup(data):
    """Returns list of error messages. Empty list = valid."""
    errors = []

    # Required fields
    required = ["full_name", "email", "password", "confirm_password",
                "phone_number", "specialization", "hospital"]
    for field in required:
        if not data.get(field, "").strip():
            errors.append(f"{field} is required.")

    if errors:
        return errors

    # Email format
    if "@" not in data["email"] or "." not in data["email"]:
        errors.append("Invalid email address.")

    # Password rules
    if len(data["password"]) < 8:
        errors.append("Password must be at least 8 characters.")

    if data["password"] != data["confirm_password"]:
        errors.append("Passwords do not match.")

    # Gender — optional but must be valid if provided
    if data.get("gender"):
        valid_genders = [g.value for g in GenderEnum]
        if data["gender"] not in valid_genders:
            errors.append(f"gender must be one of: {', '.join(valid_genders)}.")

    return errors


# ══════════════════════════════════════════════════════════
#  DOCTOR SIGNUP
#  → Creates User (role=doctor) + Doctor profile
#  → verification_status = pending (admin must approve)
#  → Sends email verification code first
#  → After email verified, doctor waits for admin approval
# ══════════════════════════════════════════════════════════

def signup_doctor(data):
    """
    Returns: (response_dict, http_status_code, user_id_for_cookie)
    """

    # 1. Validate
    errors = validate_doctor_signup(data)
    if errors:
        return {"success": False, "errors": errors}, 422, None

    # 2. Check duplicate email
    # if User.query.filter_by(email=data["email"].lower().strip()).first():
    #     return {"success": False, "message": "An account with this email already exists."}, 409, None

    try:
        # 3. Parse optional fields
        gender = None
        if data.get("gender"):
            gender = GenderEnum(data["gender"])

        # 4. Hash password
        password_hash = bcrypt.generate_password_hash(
            data["password"], rounds=SALT_ROUNDS
        ).decode("utf-8")

        # 5. Create User
        # is_active = False → doctor cannot log in until:
        #   a) email is verified AND
        #   b) admin approves the account
        user = User(
            email          = data["email"].lower().strip(),
            password_hash  = password_hash,
            role           = UserRole.doctor,
            full_name      = data["full_name"].strip(),
            gender         = gender,
            phone_number   = data["phone_number"].strip(),
            is_active      = False,       # blocked until admin approves
            email_verified = False,       # blocked until email verified
        )
        db.session.add(user)
        db.session.flush()

        # 6. Create Doctor profile
        doctor = Doctor(
            doctor_id           = user.user_id,
            specialization      = data["specialization"].strip(),
            hospital            = data["hospital"].strip(),
            verification_status = VerificationStatus.pending,  # awaiting admin
            whatsapp_number     = data.get("whatsapp_number", "").strip() or None,
            bio                 = data.get("bio", "").strip() or None,
        )
        db.session.add(doctor)

        # 7. Generate and save email verification code
        code = generate_verification_code()
        verification = EmailVerification(
            user_id    = user.user_id,
            code       = code,
            expires_at = EmailVerification.generate_expiry(),
        )
        db.session.add(verification)
        db.session.commit()

        # 8. Send email verification code
        send_verification_email(user.email, user.full_name, code)

        return {
            "success": True,
            "message": "Account created! Please verify your email with the 6-digit code we sent you.",
        }, 201, str(user.user_id)

    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": "Something went wrong.", "error": str(e)}, 500, None


# ══════════════════════════════════════════════════════════
#  VERIFY DOCTOR EMAIL
#  → Same as patient but after verification:
#     doctor is NOT logged in yet — must wait for admin
# ══════════════════════════════════════════════════════════

def verify_doctor_email(code, user_id):
    """
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
        # Note: is_active stays False — admin must still approve

        db.session.commit()

        # Send "pending approval" email to doctor
        send_doctor_pending_email(user.email, user.full_name)

        # No JWT tokens here — doctor must wait for admin approval
        return {
            "success": True,
            "message": "Email verified! Your account is now pending admin approval. We will notify you once your account is reviewed.",
            "status":  "pending_approval"
        }, 200, True   # True = clear the signup_session cookie

    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": "Something went wrong.", "error": str(e)}, 500, False


# ══════════════════════════════════════════════════════════
#  RESEND CODE — same as patient flow
# ══════════════════════════════════════════════════════════

def resend_doctor_verification_code(user_id):
    """
    Returns: (response_dict, http_status_code)
    """
    if not user_id:
        return {"success": False, "message": "Session expired. Please sign up again."}, 401

    user = User.query.get(user_id)
    if not user:
        return {"success": False, "message": "User not found."}, 404

    if user.email_verified:
        return {"success": False, "message": "Email is already verified."}, 400

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

        return {"success": True, "message": "A new verification code has been sent to your email."}, 200

    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": "Something went wrong.", "error": str(e)}, 500