from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId

from config.mongo import db

notification_bp = Blueprint(
    "notification",
    __name__,
    url_prefix="/api/notifications"
)


@notification_bp.route("/", methods=["GET"])
@jwt_required()
def get_notifications():

    current_user_id = get_jwt_identity()

    notification_data = list(
        db.notifications.find({
            "receiver_id": current_user_id
        }).sort("_id", -1)
    )

    result = []

    for notif in notification_data:
        result.append({
            "id": str(notif["_id"]),
            "title": notif.get("title", ""),
            "message": notif.get("message", ""),
            "is_read": notif.get("is_read", False),
            "created_at": str(notif.get("created_at", ""))
        })

    return jsonify(result), 200


@notification_bp.route("/read/<notification_id>", methods=["PUT"])
@jwt_required()
def mark_as_read(notification_id):

    current_user_id = get_jwt_identity()

    db.notifications.update_one(
        {
            "_id": ObjectId(notification_id),
            "receiver_id": current_user_id
        },
        {
            "$set": {
                "is_read": True
            }
        }
    )

    return jsonify({
        "message": "Notifikasi dibaca"
    }), 200