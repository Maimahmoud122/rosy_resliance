import random
from datetime import datetime
from app import db, bcrypt
from models import User
from models.password_reset_token import PasswordResetToken
from services.email_service import send_password_reset_email, send_password_changed_email
from flask_jwt_extended import get_jwt_identity

SALT_ROUNDS = 12


# ══════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════

def generate_reset_code():
    """Returns a random 6-digit string."""
    return str(random.randint(100000, 999999))


# ══════════════════════════════════════════════════════════
#  DELETE ACCOUNT
#  → Logged-in user deletes their own account
#  → Requires password confirmation for security
# ══════════════════════════════════════════════════════════

def delete_account(data):
    """
    Permanently deletes the account of the currently logged-in user.
    Requires password confirmation to prevent accidental deletion.

    Args:
        data (dict): must contain 'password' for confirmation

    Returns: (response_dict, http_status_code, should_clear_cookies)
    """

    # 1. Get current user from JWT
    user_id = get_jwt_identity()
    user    = User.query.get(user_id)

    if not user:
        return {"success": False, "message": "User not found."}, 404

    # 2. Password confirmation is required
    password = data.get("password", "").strip()
    if not password:
        return {"success": False, "message": "Password is required to delete your account."}, 400

    # 3. Verify the password
    if not bcrypt.check_password_hash(user.password_hash, password):
        return {"success": False, "message": "Incorrect password."}, 401

    try:
        full_name = user.full_name

        # 4. Hard delete — cascades to doctor/patient/admin profile automatically
        # (because of ON DELETE CASCADE on the foreign keys)
        db.session.delete(user)
        db.session.commit()

        return {
            "success": True,
            "message": f"Account for {full_name} has been permanently deleted.",
        }, 200  # True = clear JWT cookies

    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": "Something went wrong.", "error": str(e)}, 500


# ══════════════════════════════════════════════════════════
#  FORGOT PASSWORD — STEP 1
#  → User submits email
#  → Generate reset code and send it
# ══════════════════════════════════════════════════════════

def forgot_password(data):
    """
    Sends a 6-digit password reset code to the user's email.

    Security note: Always returns success even if email doesn't exist
    to prevent email enumeration attacks.

    Args:
        data (dict): must contain 'email'

    Returns: (response_dict, http_status_code, user_id_for_cookie)
    """

    email = data.get("email", "").strip().lower()

    if not email:
        return {"success": False, "message": "Email is required."}, 400, None

    # Always return success even if email not found (security)
    user = User.query.filter_by(email=email).first()
    if not user:
        return {"success": False, "message": "No account found with this email address."}, 404, None

    if not user.is_active:
        return {"success": False, "message": "This account has been deactivated. Please contact support."}, 403, None

    user = User.query.filter_by(email=email).first()
    if not user:
        return *generic_response, None   # don't reveal email doesn't exist

    # Check account is active
    if not user.is_active:
        return *generic_response, None

    try:
        # Invalidate all previous unused reset codes for this user
        PasswordResetToken.query.filter_by(
            user_id=str(user.user_id), is_used=False
        ).update({"is_used": True})

        # Generate and save new reset code
        code = generate_reset_code()
        reset_token = PasswordResetToken(
            user_id    = user.user_id,
            code       = code,
            expires_at = PasswordResetToken.generate_expiry(),
        )
        db.session.add(reset_token)
        db.session.commit()

        # Send reset email
        send_password_reset_email(user.email, user.full_name, code)

        # Return user_id as 3rd value → route stores it in cookie
        return {
            "success": True,
            "message": "A 6-digit reset code has been sent to your email.",
        }, 200, str(user.user_id)

    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": "Something went wrong.", "error": str(e)}, 500, None


# ══════════════════════════════════════════════════════════
#  FORGOT PASSWORD — STEP 2
#  → User submits code (read from cookie) + new password
# ══════════════════════════════════════════════════════════

def verify_reset_code(data, user_id):
    """
    Verifies the reset code and sets a new password.

    Args:
        data    (dict): must contain 'code' and 'new_password' and 'confirm_password'
        user_id (str):  from the reset_session cookie

    Returns: (response_dict, http_status_code, should_clear_cookie)
    """

    if not user_id:
        return {
            "success": False,
            "message": "Session expired. Please request a new reset code."
        }, 401, False

    code             = data.get("code", "").strip()
    new_password     = data.get("new_password", "")
    confirm_password = data.get("confirm_password", "")

    # Validate fields
    if not code:
        return {"success": False, "message": "Reset code is required."}, 400, False

    if not new_password or not confirm_password:
        return {"success": False, "message": "new_password and confirm_password are required."}, 400, False

    if len(new_password) < 8:
        return {"success": False, "message": "Password must be at least 8 characters."}, 422, False

    if new_password != confirm_password:
        return {"success": False, "message": "Passwords do not match."}, 422, False

    # Get the latest unused reset token
    reset_token = (
        PasswordResetToken.query
        .filter_by(user_id=user_id, is_used=False)
        .order_by(PasswordResetToken.created_at.desc())
        .first()
    )

    if not reset_token:
        return {
            "success": False,
            "message": "No active reset code found. Please request a new one."
        }, 404, False

    if reset_token.is_expired():
        return {
            "success": False,
            "message": "This code has expired. Please request a new one."
        }, 410, False

    if reset_token.code != code:
        return {"success": False, "message": "Invalid reset code."}, 400, False

    try:
        user = User.query.get(user_id)

        # Check new password is not the same as old password
        if bcrypt.check_password_hash(user.password_hash, new_password):
            return {
                "success": False,
                "message": "New password must be different from your current password."
            }, 422, False

        # Mark token as used
        reset_token.is_used = True

        # Hash and save new password
        user.password_hash = bcrypt.generate_password_hash(
            new_password, rounds=SALT_ROUNDS
        ).decode("utf-8")

        db.session.commit()

        # Send confirmation email
        send_password_changed_email(user.email, user.full_name)

        return {
            "success": True,
            "message": "Password reset successfully! You can now log in with your new password.",
        }, 200, True   # True = clear the reset_session cookie

    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": "Something went wrong.", "error": str(e)}, 500, False


# ══════════════════════════════════════════════════════════
#  RESEND RESET CODE
# ══════════════════════════════════════════════════════════

def resend_reset_code(user_id):
    """
    Args:
        user_id (str): from the reset_session cookie

    Returns: (response_dict, http_status_code)
    """

    if not user_id:
        return {
            "success": False,
            "message": "Session expired. Please start the reset process again."
        }, 401

    user = User.query.get(user_id)
    if not user:
        return {"success": False, "message": "User not found."}, 404

    try:
        # Invalidate old codes
        PasswordResetToken.query.filter_by(
            user_id=user_id, is_used=False
        ).update({"is_used": True})

        code = generate_reset_code()
        reset_token = PasswordResetToken(
            user_id    = user_id,
            code       = code,
            expires_at = PasswordResetToken.generate_expiry(),
        )
        db.session.add(reset_token)
        db.session.commit()

        send_password_reset_email(user.email, user.full_name, code)

        return {
            "success": True,
            "message": "A new reset code has been sent to your email.",
        }, 200

    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": "Something went wrong.", "error": str(e)}, 500