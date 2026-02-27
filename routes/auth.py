from flask import Blueprint, request, jsonify, make_response
from app import limiter
from services.auth_service import (
    signup_patient,
    verify_email,
    resend_verification_code,
)
from services.doctor_auth_service import (
    signup_doctor,
    verify_doctor_email,
    resend_doctor_verification_code,
)
from services.login_service import login_user, logout_user

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# ── Cookie settings ───────────────────────────────────────
SIGNUP_COOKIE_NAME     = "signup_session"
SIGNUP_COOKIE_MAX_AGE  = 60 * 30    # 30 minutes
ACCESS_COOKIE_MAX_AGE  = 3600       # 1 hour
REFRESH_COOKIE_MAX_AGE = 2592000    # 30 days


def _set_jwt_cookies(res, access_token, refresh_token):
    """Helper to set both JWT cookies on a response."""
    res.set_cookie("access_token",  access_token,  max_age=ACCESS_COOKIE_MAX_AGE,  httponly=True, samesite="Lax", secure=False)
    res.set_cookie("refresh_token", refresh_token, max_age=REFRESH_COOKIE_MAX_AGE, httponly=True, samesite="Lax", secure=False)
    return res


# ══════════════════════════════════════════════════════════
#  PATIENT SIGNUP
# ══════════════════════════════════════════════════════════

@auth_bp.route("/patient/signup", methods=["POST"])
@limiter.limit("5 per minute; 20 per hour")
def patient_signup():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided."}), 400

    response, status, user_id = signup_patient(data)
    res = make_response(jsonify(response), status)

    if user_id:
        res.set_cookie(SIGNUP_COOKIE_NAME, value=user_id, max_age=SIGNUP_COOKIE_MAX_AGE, httponly=True, samesite="Lax", secure=False)

    return res


@auth_bp.route("/patient/verify-email", methods=["POST"])
@limiter.limit("5 per minute; 10 per hour")
def patient_verify_email():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided."}), 400

    user_id = request.cookies.get(SIGNUP_COOKIE_NAME)
    code    = data.get("code", "").strip()

    response, status, should_clear_cookie = verify_email(code, user_id)
    res = make_response(jsonify(response), status)

    if should_clear_cookie:
        res.delete_cookie(SIGNUP_COOKIE_NAME)
        _set_jwt_cookies(res, response["access_token"], response["refresh_token"])

    return res


@auth_bp.route("/patient/resend-code", methods=["POST"])
@limiter.limit("3 per minute; 5 per hour")
def patient_resend_code():
    user_id  = request.cookies.get(SIGNUP_COOKIE_NAME)
    response, status = resend_verification_code(user_id)
    return jsonify(response), status


# ══════════════════════════════════════════════════════════
#  DOCTOR SIGNUP
# ══════════════════════════════════════════════════════════

@auth_bp.route("/doctor/signup", methods=["POST"])
@limiter.limit("3 per minute; 10 per hour")
def doctor_signup():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided."}), 400

    response, status, user_id = signup_doctor(data)
    res = make_response(jsonify(response), status)

    if user_id:
        res.set_cookie(SIGNUP_COOKIE_NAME, value=user_id, max_age=SIGNUP_COOKIE_MAX_AGE, httponly=True, samesite="Lax", secure=False)

    return res


@auth_bp.route("/doctor/verify-email", methods=["POST"])
@limiter.limit("5 per minute; 10 per hour")
def doctor_verify_email():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided."}), 400

    user_id = request.cookies.get(SIGNUP_COOKIE_NAME)
    code    = data.get("code", "").strip()

    response, status, should_clear_cookie = verify_doctor_email(code, user_id)
    res = make_response(jsonify(response), status)

    if should_clear_cookie:
        res.delete_cookie(SIGNUP_COOKIE_NAME)

    return res


@auth_bp.route("/doctor/resend-code", methods=["POST"])
@limiter.limit("3 per minute; 5 per hour")
def doctor_resend_code():
    user_id  = request.cookies.get(SIGNUP_COOKIE_NAME)
    response, status = resend_doctor_verification_code(user_id)
    return jsonify(response), status


# ══════════════════════════════════════════════════════════
#  UNIFIED LOGIN — one route for all roles
# ══════════════════════════════════════════════════════════

@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute; 50 per hour")
def login():
    """
    Single login for patient, doctor, and admin.
    Role is detected automatically from the database.

    Required: email, password
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided."}), 400

    response, status, tokens = login_user(data)
    res = make_response(jsonify(response), status)

    if tokens:
        _set_jwt_cookies(res, *tokens)

    return res


# ══════════════════════════════════════════════════════════
#  LOGOUT — works for all roles
# ══════════════════════════════════════════════════════════

@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Clears JWT cookies. Works for patient, doctor, and admin."""
    response, status = logout_user()
    res = make_response(jsonify(response), status)
    res.delete_cookie("access_token")
    res.delete_cookie("refresh_token")
    return res