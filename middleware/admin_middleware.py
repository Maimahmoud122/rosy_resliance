from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from models import User, UserRole


def admin_required(f):
    """
    Middleware that:
    1. Checks JWT token is valid
    2. Checks the user exists and is active
    3. Checks the user role is admin
    """
    @wraps(f)
    def decorated(*args, **kwargs):

        # 1. Verify JWT token
        try:
            verify_jwt_in_request()
        except Exception:
            return jsonify({
                "success": False,
                "message": "Unauthorized. Please log in."
            }), 401

        # 2. Get user from token
        user_id = get_jwt_identity()
        user    = User.query.get(user_id)

        if not user:
            return jsonify({"success": False, "message": "User not found."}), 404

        # 3. Check account is active
        if not user.is_active:
            return jsonify({"success": False, "message": "Your account has been deactivated."}), 403

        # 4. Check role is admin
        if user.role != UserRole.admin:
            return jsonify({
                "success": False,
                "message": "Access denied. Admin only."
            }), 403

        return f(*args, **kwargs)
    return decorated