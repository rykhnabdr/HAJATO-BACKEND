from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from config.mongo import db
import os
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
from services.notification_service import (
    send_push_notification,
    save_notification
)

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

        "booking_status": "pending_payment",
        "payment_status": "pending_payment",
        "vendor_payout_status": "hold",

        "created_at": datetime.utcnow()
    }

    result = bookings.insert_one(booking_data)

    # ==========================
    # NOTIF BOOKING BARU VENDOR
    # ==========================

    vendor = db.vendor_registrations.find_one({
        "_id": ObjectId(data.get("vendor_id"))
    })

    if vendor:

        vendor_user_id = vendor.get("user_id")

        vendor_user = db.users.find_one({
            "_id": ObjectId(vendor_user_id)
        })

        if vendor_user and vendor_user.get("fcm_token"):

            send_push_notification(
                vendor_user.get("fcm_token"),
                "Booking Baru",
                f"Ada pesanan baru dari {current_user.get('name')} untuk {data.get('package_name')}"
            )

            save_notification(
                receiver_id=vendor_user["_id"],
                role="vendor",
                title="Booking Baru",
                message=f"Ada pesanan baru dari {current_user.get('name')} untuk {data.get('package_name')}"
            )

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
            # "payment_status": "paid"
        }).sort("_id", -1)
    )

    result = []

    for booking in booking_data:

        existing_review = db.reviews.find_one({
            "booking_id": str(booking["_id"]),
            "user_id": current_user_id
        })

        has_reviewed = existing_review is not None

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
            "has_reviewed": has_reviewed,
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
            "vendor_id": str(vendor["_id"]),
            "payment_status": "paid"
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

    user = db.users.find_one({
        "_id": ObjectId(booking.get("user_id"))
    })

    if user and user.get("fcm_token"):

        send_push_notification(
            user.get("fcm_token"),
            "Acara Selesai",
            f"Vendor telah menyelesaikan layanan untuk {booking.get('package_name')}."
        )

        save_notification(
            receiver_id=user["_id"],
            role="user",
            title="Acara Selesai",
            message=f"Vendor telah menyelesaikan layanan untuk {booking.get('package_name')}."
        )

    return jsonify({
        "message": "Acara berhasil diselesaikan"
    }), 200

@booking_bp.route("/check-availability", methods=["GET"])
@jwt_required()
def check_availability():

    vendor_id = request.args.get("vendor_id")
    event_date = request.args.get("event_date")

    if not vendor_id or not event_date:
        return jsonify({
            "available": False,
            "message": "Vendor dan tanggal wajib diisi"
        }), 400

    existing_booking = bookings.find_one({
        "vendor_id": vendor_id,
        "event_date": event_date,
        "payment_status": "paid",
        "booking_status": {
            "$in": ["confirmed", "completed"]
        }
    })

    if existing_booking:
        return jsonify({
            "available": False,
            "message": "Tanggal ini sudah dibooking"
        }), 200

    return jsonify({
        "available": True,
        "message": "Tanggal tersedia"
    }), 200

@booking_bp.route("/vendor-schedule", methods=["GET"])
@jwt_required()
def vendor_schedule():

    current_user_id = get_jwt_identity()

    vendor = db.vendor_registrations.find_one({
        "user_id": current_user_id,
        "status": "approved"
    })

    if not vendor:
        return jsonify({
            "message": "Vendor tidak ditemukan"
        }), 404

    schedule_data = list(
        bookings.find({
            "vendor_id": str(vendor["_id"]),
            "payment_status": "paid"
        }).sort("event_date", 1)
    )

    result = []

    for booking in schedule_data:
        result.append({
            "id": str(booking["_id"]),
            "customer_name": booking.get("customer_name", ""),
            "package_name": booking.get("package_name", ""),
            "event_date": booking.get("event_date", ""),
            "event_time": booking.get("event_time", ""),
            "location": booking.get("location", ""),
            "booking_status": booking.get("booking_status", ""),
            "payment_status": booking.get("payment_status", ""),
            "total_price": booking.get("total_price", 0),
        })

    return jsonify({
        "data": result
    }), 200