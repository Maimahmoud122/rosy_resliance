from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from models import User


def jwt_required_middleware(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        # Debug: print what headers are received
        auth_header = request.headers.get("Authorization", "NOT FOUND")
        print(f"DEBUG Authorization header: {auth_header}")

        try:
            verify_jwt_in_request()   # ← no locations param, uses Flask-JWT default
        except Exception as e:
            print(f"DEBUG JWT error: {str(e)}")
            return jsonify({
                "success": False,
                "message": "Unauthorized. Please log in.",
                "debug":   str(e)    # ← shows exact error during development
            }), 401

        user_id = get_jwt_identity()
        user    = User.query.get(user_id)

        if not user:
            return jsonify({"success": False, "message": "User not found."}), 404

        if not user.is_active:
            return jsonify({
                "success": False,
                "message": "Your account has been deactivated."
            }), 403

        return f(*args, **kwargs)
    return decorated