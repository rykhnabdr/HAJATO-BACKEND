from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId
from datetime import datetime
from services.log_service import create_activity_log
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

    current_user = db.users.find_one({
        "_id": ObjectId(current_user_id)
    })

    if not current_user:
        return jsonify({
            "message": "User tidak ditemukan"
        }), 404

    booking = bookings.find_one({
        "_id": ObjectId(booking_id),
        "user_id": current_user_id
    })

    if not booking:
        return jsonify({
            "message": "Booking tidak ditemukan"
        }), 404

    package_name = booking.get("package_name", "-")
    vendor_name = booking.get("vendor_name", "-")
    total_price = int(booking.get("total_price", 0))

    order_id = f"HAJATO-{booking_id}-{int(datetime.utcnow().timestamp())}"

    param = {
        "transaction_details": {
            "order_id": order_id,
            "gross_amount": total_price
        },
        "customer_details": {
            "first_name": booking.get("customer_name", "Customer"),
            "email": current_user.get("email", "")
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

    # =========================
    # CATAT LOG: CREATE PAYMENT
    # =========================
    create_activity_log(
        user_id=current_user_id,
        email=current_user.get("email", ""),
        name=current_user.get("name", ""),
        role=current_user.get("role", "user"),
        action="CREATE_PAYMENT",
        title="Membuat pembayaran",
        description=f"Anda membuat transaksi pembayaran Midtrans untuk paket {package_name} di vendor {vendor_name}.",
        target_type="booking",
        target_id=booking_id,
        metadata={
            "booking_id": booking_id,
            "midtrans_order_id": order_id,
            "vendor_id": booking.get("vendor_id"),
            "vendor_name": vendor_name,
            "package_name": package_name,
            "payment_method": "midtrans",
            "payment_status": "pending_payment",
            "total_price": total_price
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

    if not data:
        return jsonify({
            "message": "Data callback kosong"
        }), 400

    order_id = data.get("order_id")
    transaction_status = data.get("transaction_status")

    print("MIDTRANS CALLBACK:", data)

    if not order_id:
        return jsonify({
            "message": "Order ID tidak ditemukan"
        }), 400

    booking = bookings.find_one({
        "midtrans_order_id": order_id
    })

    if not booking:
        return jsonify({
            "message": "Booking tidak ditemukan"
        }), 404

    user = db.users.find_one({
        "_id": ObjectId(booking.get("user_id"))
    })

    package_name = booking.get("package_name", "-")
    vendor_name = booking.get("vendor_name", "-")
    total_price = booking.get("total_price", 0)
    old_payment_status = booking.get("payment_status")

    # =========================
    # PAYMENT SUCCESS
    # =========================
    if transaction_status in ["settlement", "capture"]:

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

        # Biar log dan notifikasi tidak dobel kalau callback Midtrans masuk lebih dari sekali
        if user and old_payment_status != "paid":

            create_activity_log(
                user_id=user["_id"],
                email=user.get("email", ""),
                name=user.get("name", ""),
                role=user.get("role", "user"),
                action="PAYMENT_SUCCESS",
                title="Pembayaran berhasil",
                description=f"Pembayaran untuk paket {package_name} di vendor {vendor_name} berhasil dan booking telah dikonfirmasi.",
                target_type="booking",
                target_id=booking.get("_id"),
                metadata={
                    "booking_id": str(booking.get("_id")),
                    "midtrans_order_id": order_id,
                    "vendor_id": booking.get("vendor_id"),
                    "vendor_name": vendor_name,
                    "package_name": package_name,
                    "payment_method": "midtrans",
                    "payment_status": "paid",
                    "booking_status": "confirmed",
                    "total_price": total_price
                }
            )

            if user.get("fcm_token"):

                send_push_notification(
                    user.get("fcm_token"),
                    "Pembayaran Berhasil",
                    f"Pembayaran untuk {package_name} di vendor {vendor_name} berhasil dan booking telah dikonfirmasi."
                )

                save_notification(
                    receiver_id=user["_id"],
                    role="user",
                    title="Pembayaran Berhasil",
                    message=f"Pembayaran untuk {package_name} di vendor {vendor_name} berhasil dan booking telah dikonfirmasi."
                )

        vendor = db.vendor_registrations.find_one({
            "_id": ObjectId(booking.get("vendor_id"))
        })

        if vendor and old_payment_status != "paid":

            vendor_user = db.users.find_one({
                "_id": ObjectId(vendor.get("user_id"))
            })

            if vendor_user:
                create_activity_log(
                    user_id=vendor.get("user_id"),
                    email=vendor_user.get("email", ""),
                    name=vendor_user.get("name", ""),
                    role="vendor",
                    action="RECEIVE_BOOKING",
                    title="Menerima booking baru",
                    description=f"Anda menerima booking baru untuk paket {package_name} dari pelanggan {booking.get('customer_name')}.",
                    target_type="booking",
                    target_id=booking.get("_id"),
                    metadata={
                        "booking_id": str(booking.get("_id")),
                        "midtrans_order_id": order_id,
                        "vendor_id": booking.get("vendor_id"),
                        "vendor_name": vendor_name,
                        "customer_name": booking.get("customer_name"),
                        "package_name": package_name,
                        "event_date": booking.get("event_date"),
                        "event_time": booking.get("event_time"),
                        "total_price": total_price,
                        "payment_status": "paid",
                        "booking_status": "confirmed"
                    }
                )

            if vendor_user and vendor_user.get("fcm_token"):

                send_push_notification(
                    vendor_user.get("fcm_token"),
                    "Pembayaran Diterima",
                    f"{booking.get('customer_name')} telah menyelesaikan pembayaran untuk {package_name}."
                )

                save_notification(
                    receiver_id=vendor_user["_id"],
                    role="vendor",
                    title="Pembayaran Diterima",
                    message=f"{booking.get('customer_name')} telah menyelesaikan pembayaran untuk {package_name}."
                )

    # =========================
    # PAYMENT FAILED / EXPIRED / CANCEL
    # =========================
    elif transaction_status in ["deny", "cancel", "expire", "failure"]:

        bookings.update_one(
            {
                "midtrans_order_id": order_id
            },
            {
                "$set": {
                    "payment_status": "failed"
                }
            }
        )

        # Biar log gagal tidak dobel
        if user and old_payment_status != "failed":

            create_activity_log(
                user_id=user["_id"],
                email=user.get("email", ""),
                name=user.get("name", ""),
                role=user.get("role", "user"),
                action="PAYMENT_FAILED",
                title="Pembayaran gagal",
                description=f"Pembayaran untuk paket {package_name} di vendor {vendor_name} gagal atau dibatalkan.",
                target_type="booking",
                target_id=booking.get("_id"),
                metadata={
                    "booking_id": str(booking.get("_id")),
                    "midtrans_order_id": order_id,
                    "vendor_id": booking.get("vendor_id"),
                    "vendor_name": vendor_name,
                    "package_name": package_name,
                    "payment_method": "midtrans",
                    "payment_status": "failed",
                    "transaction_status": transaction_status,
                    "total_price": total_price
                }
            )

            if user.get("fcm_token"):

                send_push_notification(
                    user.get("fcm_token"),
                    "Pembayaran Gagal",
                    f"Pembayaran untuk {package_name} di vendor {vendor_name} gagal atau dibatalkan."
                )

                save_notification(
                    receiver_id=user["_id"],
                    role="user",
                    title="Pembayaran Gagal",
                    message=f"Pembayaran untuk {package_name} di vendor {vendor_name} gagal atau dibatalkan."
                )

    return jsonify({
        "message": "OK"
    }), 200