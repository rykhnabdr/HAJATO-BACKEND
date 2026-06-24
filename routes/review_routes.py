from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId
from datetime import datetime
from services.log_service import create_activity_log

from config.mongo import db

review_bp = Blueprint(
    "review",
    __name__,
    url_prefix="/api/reviews"
)

reviews = db.reviews
bookings = db.bookings


@review_bp.route("/create", methods=["POST"])
@jwt_required()
def create_review():

    current_user_id = get_jwt_identity()

    current_user = db.users.find_one({
        "_id": ObjectId(current_user_id)
    })

    if not current_user:
        return jsonify({
            "message": "User tidak ditemukan"
        }), 404

    data = request.get_json()

    if not data:
        return jsonify({
            "message": "Data ulasan tidak boleh kosong"
        }), 400

    booking_id = data.get("booking_id")
    rating = data.get("rating")
    comment = data.get("comment", "")

    if not booking_id or rating is None:
        return jsonify({
            "message": "Booking dan rating wajib diisi"
        }), 400

    if not ObjectId.is_valid(booking_id):
        return jsonify({
            "message": "ID booking tidak valid"
        }), 400

    try:
        rating = int(rating)
    except:
        return jsonify({
            "message": "Rating harus berupa angka"
        }), 400

    if rating < 1 or rating > 5:
        return jsonify({
            "message": "Rating harus antara 1 sampai 5"
        }), 400

    booking = bookings.find_one({
        "_id": ObjectId(booking_id),
        "user_id": current_user_id
    })

    if not booking:
        return jsonify({
            "message": "Booking tidak ditemukan"
        }), 404

    if booking.get("booking_status") != "completed":
        return jsonify({
            "message": "Ulasan hanya bisa diberikan setelah acara selesai"
        }), 400

    existing_review = reviews.find_one({
        "booking_id": booking_id,
        "user_id": current_user_id
    })

    if existing_review:
        return jsonify({
            "message": "Anda sudah memberi ulasan untuk booking ini"
        }), 400

    vendor_name = booking.get("vendor_name", "-")
    package_name = booking.get("package_name", "-")

    review_data = {
        "booking_id": booking_id,
        "user_id": current_user_id,
        "customer_name": booking.get("customer_name"),
        "vendor_id": booking.get("vendor_id"),
        "vendor_name": vendor_name,
        "package_name": package_name,
        "rating": rating,
        "comment": comment,
        "created_at": datetime.utcnow()
    }

    result = reviews.insert_one(review_data)

    # =========================
    # CATAT LOG: CREATE REVIEW
    # =========================
    create_activity_log(
        user_id=current_user_id,
        email=current_user.get("email", ""),
        name=current_user.get("name", ""),
        role=current_user.get("role", "user"),
        action="CREATE_REVIEW",
        title="Memberi ulasan",
        description=f"Anda memberikan ulasan untuk paket {package_name} di vendor {vendor_name} dengan rating {rating} bintang.",
        target_type="review",
        target_id=result.inserted_id,
        metadata={
            "review_id": str(result.inserted_id),
            "booking_id": booking_id,
            "vendor_id": booking.get("vendor_id"),
            "vendor_name": vendor_name,
            "package_name": package_name,
            "rating": rating,
            "comment": comment
        }
    )

    return jsonify({
        "message": "Ulasan berhasil dikirim",
        "review_id": str(result.inserted_id)
    }), 201


@review_bp.route("/vendor/<vendor_id>", methods=["GET"])
def get_vendor_reviews(vendor_id):

    review_data = list(
        reviews.find({
            "vendor_id": vendor_id
        }).sort("_id", -1)
    )

    result = []

    for review in review_data:
        result.append({
            "id": str(review["_id"]),
            "customer_name": review.get("customer_name", ""),
            "package_name": review.get("package_name", ""),
            "rating": review.get("rating", 0),
            "comment": review.get("comment", ""),
            "created_at": str(review.get("created_at", ""))
        })

    return jsonify({
        "data": result
    }), 200


@review_bp.route("/vendor-rating/<vendor_id>", methods=["GET"])
def get_vendor_rating(vendor_id):

    review_data = list(
        reviews.find({
            "vendor_id": vendor_id
        })
    )

    if len(review_data) == 0:
        return jsonify({
            "average_rating": 0,
            "total_reviews": 0
        }), 200

    total_rating = sum(
        review.get("rating", 0)
        for review in review_data
    )

    average_rating = round(
        total_rating / len(review_data),
        1
    )

    return jsonify({
        "average_rating": average_rating,
        "total_reviews": len(review_data)
    }), 200