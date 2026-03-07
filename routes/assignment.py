from flask import Blueprint, request, jsonify
from app import limiter
from middleware.auth_middleware import jwt_required_middleware
from services.assignment_service import (
    get_all_doctors,
    request_doctor_assignment,
    get_my_requests,
    cancel_assignment_request,
    get_doctor_pending_requests,
    accept_assignment,
    reject_assignment,
    remove_assigned_doctor,
)

assignment_bp = Blueprint("assignment", __name__, url_prefix="/api")


# ══════════════════════════════════════════════════════════
#  PATIENT ROUTES
# ══════════════════════════════════════════════════════════

@assignment_bp.route("/doctors", methods=["GET"])
@jwt_required_middleware
def browse_doctors():
    response, status = get_all_doctors()
    return jsonify(response), status


@assignment_bp.route("/doctors/<string:doctor_id>/request", methods=["POST"])
@jwt_required_middleware
@limiter.limit("5 per hour")
def request_assignment(doctor_id):
    response, status = request_doctor_assignment(doctor_id)
    return jsonify(response), status


@assignment_bp.route("/patient/requests", methods=["GET"])
@jwt_required_middleware
def my_requests():
    response, status = get_my_requests()
    return jsonify(response), status


@assignment_bp.route("/patient/requests/<string:assignment_id>", methods=["DELETE"])
@jwt_required_middleware
def cancel_request(assignment_id):
    response, status = cancel_assignment_request(assignment_id)
    return jsonify(response), status


@assignment_bp.route("/patient/doctor", methods=["DELETE"])
@jwt_required_middleware
def remove_doctor():
    response, status = remove_assigned_doctor()
    return jsonify(response), status


# ══════════════════════════════════════════════════════════
#  DOCTOR ROUTES
# ══════════════════════════════════════════════════════════

@assignment_bp.route("/doctor/requests", methods=["GET"])
@jwt_required_middleware
def doctor_requests():
    response, status = get_doctor_pending_requests()
    return jsonify(response), status


@assignment_bp.route("/doctor/requests/<string:assignment_id>/accept", methods=["PUT"])
@jwt_required_middleware
def accept_request(assignment_id):
    response, status = accept_assignment(assignment_id)
    return jsonify(response), status


@assignment_bp.route("/doctor/requests/<string:assignment_id>/reject", methods=["PUT"])
@jwt_required_middleware
def reject_request(assignment_id):
    response, status = reject_assignment(assignment_id)
    return jsonify(response), status