from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId
from datetime import datetime
from services.notification_service import (
    send_push_notification,
    save_notification
)

from config.mongo import db
from config.midtrans_config import snap

payment_bp = Blueprint(
    "payment",
    __name__,
    url_prefix="/api/payment"
)

bookings = db.bookings


@payment_bp.route("/create/<booking_id>", methods=["POST"])
@jwt_required()
def create_midtrans_payment(booking_id):

    current_user_id = get_jwt_identity()

    booking = bookings.find_one({
        "_id": ObjectId(booking_id),
        "user_id": current_user_id
    })

    if not booking:
        return jsonify({
            "message": "Booking tidak ditemukan"
        }), 404

    order_id = f"HAJATO-{booking_id}-{int(datetime.utcnow().timestamp())}"

    param = {
        "transaction_details": {
            "order_id": order_id,
            "gross_amount": int(booking.get("total_price", 0))
        },
        "customer_details": {
            "first_name": booking.get("customer_name", "Customer")
        }
    }

    transaction = snap.create_transaction(param)

    bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {
            "$set": {
                "payment_method": "midtrans",
                "midtrans_order_id": order_id,
                "snap_token": transaction.get("token"),
                "snap_redirect_url": transaction.get("redirect_url"),
                "payment_status": "pending_payment"
            }
        }
    )

    return jsonify({
        "message": "Transaksi Midtrans berhasil dibuat",
        "snap_token": transaction.get("token"),
        "redirect_url": transaction.get("redirect_url")
    }), 200

@payment_bp.route("/notification", methods=["POST"])
def midtrans_notification():

    data = request.get_json()

    order_id = data.get("order_id")
    transaction_status = data.get("transaction_status")

    print("MIDTRANS CALLBACK:", data)

    if transaction_status in [
        "settlement",
        "capture"
    ]:

        bookings.update_one(
            {
                "midtrans_order_id": order_id
            },
            {
                "$set": {
                    "payment_status": "paid",
                    "booking_status": "confirmed",
                    "vendor_payout_status": "hold"
                }
            }
        )

        booking = bookings.find_one({
            "midtrans_order_id": order_id
        })

        if booking:

            user = db.users.find_one({
                "_id": ObjectId(booking.get("user_id"))
            })

            if user and user.get("fcm_token"):

                send_push_notification(
                    user.get("fcm_token"),
                    "Pembayaran Berhasil",
                    f"Pembayaran untuk {booking.get('package_name')} berhasil dan booking telah dikonfirmasi."
                )

                save_notification(
                    receiver_id=user["_id"],
                    role="user",
                    title="Pembayaran Berhasil",
                    message=f"Pembayaran untuk {booking.get('package_name')} berhasil dan booking telah dikonfirmasi."
                )

            vendor = db.vendor_registrations.find_one({
                "_id": ObjectId(booking.get("vendor_id"))
            })

            if vendor:

                vendor_user = db.users.find_one({
                    "_id": ObjectId(vendor.get("user_id"))
                })

                if vendor_user and vendor_user.get("fcm_token"):

                    send_push_notification(
                        vendor_user.get("fcm_token"),
                        "Pembayaran Diterima",
                        f"{booking.get('customer_name')} telah menyelesaikan pembayaran untuk {booking.get('package_name')}."
                    )

                    save_notification(
                        receiver_id=vendor_user["_id"],
                        role="vendor",
                        title="Pembayaran Diterima",
                        message=f"{booking.get('customer_name')} telah menyelesaikan pembayaran untuk {booking.get('package_name')}."
                    )

    return jsonify({
        "message": "OK"
    }), 200