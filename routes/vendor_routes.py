import os
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId

from config.mongo import db

vendor_bp = Blueprint(
    'vendor',
    __name__,
    url_prefix='/api/vendor'
)

vendor_registrations = db.vendor_registrations
users = db.users

# =========================
# UPLOAD FOLDER
# =========================
UPLOAD_FOLDER = "uploads"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# =========================
# REGISTER VENDOR
# =========================
@vendor_bp.route('/register-vendor', methods=['POST'])
@jwt_required()
def register_vendor():

    current_user_id = get_jwt_identity()

    # =========================
    # FORM DATA
    # =========================
    business_name = request.form.get("business_name")
    category = request.form.get("category")
    description = request.form.get("description")
    location = request.form.get("location")
    phone = request.form.get("phone")

    owner_name = request.form.get("owner_name")
    nik = request.form.get("nik")

    npwp = request.form.get("npwp")

    # =========================
    # FILES
    # =========================
    ktp_image = request.files.get("ktp_image")
    selfie_image = request.files.get("selfie_image")
    business_license = request.files.get("business_license")

    print("KTP :", ktp_image)
    print("SELFIE :", selfie_image)

    # =========================
    # VALIDASI
    # =========================
    if not business_name or not category:
        return jsonify({
            "message": "Data bisnis wajib diisi"
        }), 400

    # cek apakah sudah daftar
    existing_vendor = vendor_registrations.find_one({
        "user_id": current_user_id
    })

    if existing_vendor:
        return jsonify({
            "message": "Anda sudah pernah mendaftar vendor"
        }), 400

    # =========================
    # SIMPAN FILE
    # =========================
    ktp_filename = None
    selfie_filename = None
    license_filename = None

    if ktp_image:
        ktp_filename = secure_filename(
            ktp_image.filename
        )

        ktp_image.save(
            os.path.join(
                UPLOAD_FOLDER,
                ktp_filename
            )
        )

    if selfie_image:
        selfie_filename = secure_filename(
            selfie_image.filename
        )

        selfie_image.save(
            os.path.join(
                UPLOAD_FOLDER,
                selfie_filename
            )
        )

    if business_license:
        license_filename = secure_filename(
            business_license.filename
        )

        business_license.save(
            os.path.join(
                UPLOAD_FOLDER,
                license_filename
            )
        )

    # =========================
    # DATA VENDOR
    # =========================
    vendor_data = {
        "user_id": current_user_id,

        "business_name": business_name,
        "category": category,
        "description": description,
        "location": location,
        "phone": phone,

        "owner_name": owner_name,
        "nik": nik,

        "npwp": npwp,

        "ktp_image": ktp_filename,
        "selfie_image": selfie_filename,
        "business_license": license_filename,

        "status": "pending"
    }

    # simpan vendor
    vendor_registrations.insert_one(vendor_data)

    # update user
    users.update_one(
        {
            "_id": ObjectId(current_user_id)
        },
        {
            "$set": {
                "vendor_status": "pending",
                "role": "vendor_pending"
            }
        }
    )

    return jsonify({
        "message": "Pendaftaran vendor berhasil dikirim"
    }), 201


# =========================
# APPROVE VENDOR (ADMIN)
# =========================
@vendor_bp.route('/approve-vendor/<vendor_id>', methods=['PUT'])
@jwt_required()
def approve_vendor(vendor_id):

    vendor = vendor_registrations.find_one({
        "_id": ObjectId(vendor_id)
    })

    if not vendor:
        return jsonify({
            "message": "Vendor tidak ditemukan"
        }), 404

    # update status vendor
    vendor_registrations.update_one(
        {
            "_id": ObjectId(vendor_id)
        },
        {
            "$set": {
                "status": "approved"
            }
        }
    )

    # update role user
    users.update_one(
        {
            "_id": ObjectId(vendor["user_id"])
        },
        {
            "$set": {
                "role": "vendor",
                "vendor_status": "approved"
            }
        }
    )

    return jsonify({
        "message": "Vendor berhasil diapprove"
    }), 200


# =========================
# REJECT VENDOR
# =========================
@vendor_bp.route('/reject-vendor/<vendor_id>', methods=['PUT'])
@jwt_required()
def reject_vendor(vendor_id):

    vendor = vendor_registrations.find_one({
        "_id": ObjectId(vendor_id)
    })

    if not vendor:
        return jsonify({
            "message": "Vendor tidak ditemukan"
        }), 404

    # update status vendor
    vendor_registrations.update_one(
        {
            "_id": ObjectId(vendor_id)
        },
        {
            "$set": {
                "status": "rejected"
            }
        }
    )

    # update role user
    users.update_one(
        {
            "_id": ObjectId(vendor["user_id"])
        },
        {
            "$set": {
                "role": "user",
                "vendor_status": "rejected"
            }
        }
    )

    return jsonify({
        "message": "Vendor ditolak"
    }), 200