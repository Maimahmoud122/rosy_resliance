from flask import Blueprint, request, jsonify, make_response
from app import limiter
from middleware.auth_middleware import jwt_required_middleware
from services.account_service import (
    delete_account,
    forgot_password,
    verify_reset_code,
    resend_reset_code,
)

account_bp = Blueprint("account", __name__, url_prefix="/api/account")

RESET_COOKIE_NAME    = "reset_session"
RESET_COOKIE_MAX_AGE = 60 * 20


@account_bp.route("/delete", methods=["DELETE"])
@jwt_required_middleware
@limiter.limit("3 per hour")
def delete_account_route():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided."}), 400

    # Service returns 2 values — route handles cookie clearing based on status
    response, status = delete_account(data)
    res = make_response(jsonify(response), status)

    if status == 200:
        res.delete_cookie("access_token")
        res.delete_cookie("refresh_token")

    return res


@account_bp.route("/forgot-password", methods=["POST"])
@limiter.limit("3 per minute; 5 per hour")
def forgot_password_route():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided."}), 400

    response, status, user_id = forgot_password(data)
    res = make_response(jsonify(response), status)

    if user_id:
        res.set_cookie(RESET_COOKIE_NAME, value=user_id, max_age=RESET_COOKIE_MAX_AGE, httponly=True, samesite="Lax", secure=False)

    return res


@account_bp.route("/reset-password", methods=["POST"])
@limiter.limit("5 per minute; 10 per hour")
def reset_password_route():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided."}), 400

    user_id = request.cookies.get(RESET_COOKIE_NAME)
    response, status, should_clear_cookie = verify_reset_code(data, user_id)
    res = make_response(jsonify(response), status)

    if should_clear_cookie:
        res.delete_cookie(RESET_COOKIE_NAME)

    return res


@account_bp.route("/resend-reset-code", methods=["POST"])
@limiter.limit("3 per minute; 5 per hour")
def resend_reset_code_route():
    user_id  = request.cookies.get(RESET_COOKIE_NAME)
    response, status = resend_reset_code(user_id)
    return jsonify(response), status