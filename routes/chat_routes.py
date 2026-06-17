from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
import os
from datetime import datetime
from werkzeug.utils import secure_filename

from config.mongo import db
from services.notification_service import send_push_notification, save_notification

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")


@chat_bp.route("/notify", methods=["POST"])
@jwt_required()
def notify_chat():
    current_user_id = get_jwt_identity()
    data = request.get_json()

    receiver_id = data.get("receiver_id")
    title = data.get("title", "Pesan Baru")
    message = data.get("message", "")
    chat_id = data.get("chat_id", "")
    receiver_name = data.get("receiver_name", "")
    sender_role = data.get("sender_role", "")

    print("=================================")
    print("CURRENT USER:", current_user_id)
    print("RECEIVER ID:", receiver_id)
    print("TITLE:", title)
    print("MESSAGE:", message)
    print("=================================")

    if not receiver_id or not message:
        return jsonify({
            "message": "receiver_id dan message wajib diisi"
        }), 400

    receiver = db.users.find_one({
        "_id": ObjectId(receiver_id)
    })

    if not receiver:
        return jsonify({
            "message": "Penerima tidak ditemukan"
        }), 404

    fcm_token = receiver.get("fcm_token")

    if not fcm_token:
        return jsonify({
            "message": "Penerima belum memiliki FCM token"
        }), 400

    send_push_notification(
        fcm_token,
        title,
        message,
        data={
            "type": "chat",
            "chat_id": chat_id,
            "receiver_id": str(current_user_id),
            "receiver_name": receiver_name,
            "sender_role": sender_role
        }
    )

    save_notification(
        receiver_id=receiver_id,
        title=title,
        message=message,
        role=receiver.get("role")
    )

    return jsonify({
        "message": "Notifikasi chat berhasil dikirim"
    }), 200

@chat_bp.route("/upload-image", methods=["POST"])
@jwt_required()
def upload_chat_image():
    if "image" not in request.files:
        return jsonify({
            "message": "File gambar wajib diisi"
        }), 400

    image = request.files["image"]

    if image.filename == "":
        return jsonify({
            "message": "Nama file kosong"
        }), 400

    filename = secure_filename(image.filename)
    unique_filename = f"chat_{datetime.utcnow().timestamp()}_{filename}"

    upload_folder = "uploads"

    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    image_path = os.path.join(upload_folder, unique_filename)

    image.save(image_path)

    return jsonify({
        "message": "Gambar chat berhasil diupload",
        "image_url": f"{request.host_url}uploads/{unique_filename}"
    }), 200