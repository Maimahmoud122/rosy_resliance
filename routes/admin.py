from flask import Blueprint, request, jsonify
from app import limiter
from middleware.admin_middleware import admin_required
from services.admin_service import (
    get_pending_doctors,
    get_all_doctors,
    approve_doctor,
    reject_doctor,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


# ══════════════════════════════════════════════════════════
#  GET /api/admin/doctors/pending
#  → Returns all doctors waiting for approval
# ══════════════════════════════════════════════════════════

@admin_bp.route("/doctors/pending", methods=["GET"])
@admin_required
def pending_doctors():
    response, status = get_pending_doctors()
    return jsonify(response), status


# ══════════════════════════════════════════════════════════
#  GET /api/admin/doctors?status=pending|verified|rejected
#  → Returns all doctors with optional status filter
# ══════════════════════════════════════════════════════════

@admin_bp.route("/doctors", methods=["GET"])
@admin_required
def all_doctors():
    status_filter = request.args.get("status")   # ?status=pending
    response, status = get_all_doctors(status_filter)
    return jsonify(response), status


# ══════════════════════════════════════════════════════════
#  PUT /api/admin/doctors/<doctor_id>/approve
#  → Approves a doctor, activates account, sends email
# ══════════════════════════════════════════════════════════

@admin_bp.route("/doctors/<string:doctor_id>/approve", methods=["PUT"])
@admin_required
def approve_doctor_route(doctor_id):
    response, status = approve_doctor(doctor_id)
    return jsonify(response), status


# ══════════════════════════════════════════════════════════
#  PUT /api/admin/doctors/<doctor_id>/reject
#  → Rejects a doctor, sends email with optional reason
# ══════════════════════════════════════════════════════════

@admin_bp.route("/doctors/<string:doctor_id>/reject", methods=["PUT"])
@admin_required
def reject_doctor_route(doctor_id):
    data   = request.get_json() or {}
    reason = data.get("reason", "").strip() or None

    response, status = reject_doctor(doctor_id, reason)
    return jsonify(response), status