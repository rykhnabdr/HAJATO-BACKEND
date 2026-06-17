from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId
from datetime import datetime

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
    data = request.get_json()

    booking_id = data.get("booking_id")
    rating = data.get("rating")
    comment = data.get("comment", "")

    if not booking_id or not rating:
        return jsonify({
            "message": "Booking dan rating wajib diisi"
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

    review_data = {
        "booking_id": booking_id,
        "user_id": current_user_id,
        "customer_name": booking.get("customer_name"),
        "vendor_id": booking.get("vendor_id"),
        "vendor_name": booking.get("vendor_name"),
        "package_name": booking.get("package_name"),
        "rating": int(rating),
        "comment": comment,
        "created_at": datetime.utcnow()
    }

    reviews.insert_one(review_data)

    return jsonify({
        "message": "Ulasan berhasil dikirim"
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