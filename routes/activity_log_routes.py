from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from config.mongo import db
from datetime import timezone

from services.log_service import (
    get_default_title,
    get_default_description
)

activity_log_bp = Blueprint('activity_log', __name__)
def format_timestamp(timestamp):
    if not timestamp:
        return None

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    return timestamp.isoformat()


# =========================
# ACTION CATEGORY MAP
# =========================
CATEGORY_ACTIONS = {
    "akun": [
        "REGISTER",
        "VERIFY_REGISTER_OTP",
        "LOGIN",
        "LOGOUT",
        "RESET_PASSWORD",
        "CHANGE_PASSWORD",
        "UPDATE_PROFILE",
    ],

    "booking": [
        "CREATE_BOOKING",
        "CANCEL_BOOKING",
        "RECEIVE_BOOKING",
        "COMPLETE_BOOKING",
        "ACCEPT_BOOKING",
        "REJECT_BOOKING",
    ],

    "pembayaran": [
        "CREATE_PAYMENT",
        "PAYMENT_PENDING",
        "PAYMENT_SUCCESS",
        "PAYMENT_FAILED",
    ],

    "review": [
        "CREATE_REVIEW",
        "UPDATE_REVIEW",
        "DELETE_REVIEW",
        "ADD_REVIEW",
    ],

    "vendor": [
        "VENDOR_REGISTER",
        "VENDOR_APPROVED",
        "VENDOR_REJECTED",
        "UPDATE_VENDOR_PROFILE",
        "CREATE_PACKAGE",
        "UPDATE_PACKAGE",
        "DELETE_PACKAGE",
        "ADD_SERVICE",
        "EDIT_SERVICE",
        "DELETE_SERVICE",
        "PAYOUT_RELEASED",
    ],

    # =========================
    # KHUSUS TAMPILAN VENDOR
    # =========================
    "paket": [
        "CREATE_PACKAGE",
        "UPDATE_PACKAGE",
        "DELETE_PACKAGE",
        "ADD_SERVICE",
        "EDIT_SERVICE",
        "DELETE_SERVICE",
    ],

    "dana": [
        "PAYOUT_RELEASED",
    ],

    "status_vendor": [
        "VENDOR_REGISTER",
        "VENDOR_APPROVED",
        "VENDOR_REJECTED",
        "UPDATE_VENDOR_PROFILE",
    ],
}


# =========================
# GET MY ACTIVITY LOGS
# endpoint:
# /api/activity-logs/my?page=1&limit=20&category=semua
# =========================
@activity_log_bp.route('/my', methods=['GET'])
@jwt_required()
def get_my_activity_logs():

    current_user_id = get_jwt_identity()

    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    category = request.args.get("category", "semua").lower()

    if page < 1:
        page = 1

    if limit < 1:
        limit = 20

    if limit > 50:
        limit = 50

    skip = (page - 1) * limit

    query = {
        "user_id": str(current_user_id)
    }

    # =========================
    # FILTER CATEGORY
    # =========================
    if category != "semua":
        actions = CATEGORY_ACTIONS.get(category)

        if actions:
            query["action"] = {
                "$in": actions
            }

    total_logs = db.activity_logs.count_documents(query)

    logs_cursor = db.activity_logs.find(query) \
        .sort("timestamp", -1) \
        .skip(skip) \
        .limit(limit)

    logs = []

    for log in logs_cursor:
        action = log.get("action", "UNKNOWN")

        logs.append({
            "id": str(log["_id"]),
            "user_id": log.get("user_id"),
            "email": log.get("email"),
            "name": log.get("name"),
            "role": log.get("role"),
            "action": action,

            "title": log.get("title") or get_default_title(action),
            "description": log.get("description") or get_default_description(action),

            "target_type": log.get("target_type"),
            "target_id": log.get("target_id"),
            "metadata": log.get("metadata", {}),

            "timestamp": format_timestamp(log.get("timestamp")),
        })

    has_more = page * limit < total_logs

    return jsonify({
        "message": "Log aktivitas berhasil diambil",
        "data": logs,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total_logs,
            "has_more": has_more
        },
        "active_category": category
    }), 200