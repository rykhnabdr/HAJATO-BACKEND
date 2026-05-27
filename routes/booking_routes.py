from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from config.mongo import db
import os
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId

booking_bp = Blueprint(
    "booking",
    __name__,
    url_prefix="/api/booking"
)

bookings = db.bookings


@booking_bp.route("/create", methods=["POST"])
@jwt_required()
def create_booking():
    current_user_id = get_jwt_identity()

    current_user = db.users.find_one({
    "_id": ObjectId(current_user_id)
})

    data = request.get_json()

    booking_data = {
        "user_id": current_user_id,
        "customer_name": current_user.get("name"),
        "vendor_id": data.get("vendor_id"),
        "vendor_name": data.get("vendor_name"),
        "package_id": data.get("package_id"),
        "package_name": data.get("package_name"),
        "event_date": data.get("event_date"),
        "event_time": data.get("event_time"),
        "location": data.get("location"),
        "notes": data.get("notes"),
        "payment_method": data.get("payment_method"),
        "payment_detail": data.get("payment_detail"),
        "payment_proof": "",
        "total_price": data.get("total_price"),

        "booking_status": "waiting_confirmation",
        "payment_status": "pending_verification",
        "vendor_payout_status": "hold",

        "created_at": datetime.utcnow()
    }

    result = bookings.insert_one(booking_data)

    return jsonify({
        "message": "Booking berhasil dibuat",
        "booking_id": str(result.inserted_id)
    }), 201

@booking_bp.route("/my-bookings", methods=["GET"])
@jwt_required()
def my_bookings():

    current_user_id = get_jwt_identity()

    booking_data = list(
        bookings.find({
            "user_id": current_user_id
        }).sort("_id", -1)
    )

    result = []

    for booking in booking_data:

        result.append({
            "id": str(booking["_id"]),
            "vendor_name": booking.get("vendor_name", ""),
            "package_name": booking.get("package_name", ""),
            "event_date": booking.get("event_date", ""),
            "event_time": booking.get("event_time", ""),
            "location": booking.get("location", ""),
            "payment_method": booking.get("payment_method", ""),
            "total_price": booking.get("total_price", 0),
            "booking_status": booking.get("booking_status", ""),
            "payment_status": booking.get("payment_status", ""),
            "vendor_payout_status": booking.get("vendor_payout_status", ""),
            "payment_proof": booking.get("payment_proof", ""),
        })

    return jsonify(result), 200


@booking_bp.route("/upload-proof/<booking_id>", methods=["POST"])
@jwt_required()
def upload_payment_proof(booking_id):

    if "file" not in request.files:
        return jsonify({
            "message": "File tidak ditemukan"
        }), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({
            "message": "File kosong"
        }), 400

    filename = secure_filename(file.filename)

    upload_folder = "uploads/payment_proofs"

    os.makedirs(upload_folder, exist_ok=True)

    filepath = os.path.join(upload_folder, filename)

    file.save(filepath)

    bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {
            "$set": {
                "payment_proof": filename,
                "payment_status": "waiting_admin_verification"
            }
        }
    )

    return jsonify({
        "message": "Bukti pembayaran berhasil diupload",
        "filename": filename
    }), 200


@booking_bp.route("/vendor-bookings", methods=["GET"])
@jwt_required()
def vendor_bookings():

    current_user_id = get_jwt_identity()

    vendor = db.vendor_registrations.find_one({
        "user_id": current_user_id,
        "status": "approved"
    })

    if not vendor:
        return jsonify({
            "message": "Vendor tidak ditemukan"
        }), 404

    booking_data = list(
        bookings.find({
            "vendor_id": str(vendor["_id"])
        }).sort("_id", -1)
    )

    result = []

    for booking in booking_data:
        result.append({
            "id": str(booking["_id"]),
            "customer_name": booking.get("customer_name", ""),
            "vendor_name": booking.get("vendor_name", ""),
            "package_name": booking.get("package_name", ""),
            "event_date": booking.get("event_date", ""),
            "event_time": booking.get("event_time", ""),
            "location": booking.get("location", ""),
            "payment_method": booking.get("payment_method", ""),
            "total_price": booking.get("total_price", 0),
            "booking_status": booking.get("booking_status", ""),
            "payment_status": booking.get("payment_status", ""),
            "vendor_payout_status": booking.get("vendor_payout_status", ""),
            "payment_proof": booking.get("payment_proof", ""),
        })

    return jsonify(result), 200

@booking_bp.route("/complete/<booking_id>", methods=["PUT"])
@jwt_required()
def complete_booking(booking_id):

    current_user_id = get_jwt_identity()

    vendor = db.vendor_registrations.find_one({
        "user_id": current_user_id,
        "status": "approved"
    })

    if not vendor:
        return jsonify({
            "message": "Vendor tidak ditemukan"
        }), 404

    booking = bookings.find_one({
        "_id": ObjectId(booking_id)
    })

    if not booking:
        return jsonify({
            "message": "Booking tidak ditemukan"
        }), 404

    if booking.get("vendor_id") != str(vendor["_id"]):
        return jsonify({
            "message": "Akses ditolak"
        }), 403

    bookings.update_one(
        {
            "_id": ObjectId(booking_id)
        },
        {
            "$set": {
                "booking_status": "completed"
            }
        }
    )

    return jsonify({
        "message": "Acara berhasil diselesaikan"
    }), 200