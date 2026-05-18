import os
from werkzeug.utils import secure_filename
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId

from flask import Blueprint, request, jsonify
from config.mongo import db

from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity
)

from bson.objectid import ObjectId
from middleware.role_middleware import role_required

import bcrypt


auth_bp = Blueprint('auth', __name__)

users = db.users
vendor_registrations = db.vendor_registrations


# =========================
# UPLOAD FOLDER
# =========================
UPLOAD_FOLDER = "uploads"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@auth_bp.route('/register', methods=['POST'])
def register():

    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    password = data.get("password")

    if not name or not email or not phone or not password:
        return jsonify({
            "message": "Semua field wajib diisi"
        }), 400

    existing_user = users.find_one({
        "email": email
    })

    if existing_user:
        return jsonify({
            "message": "Email sudah digunakan"
        }), 400

    hashed_password = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    )

    user_data = {
        "name": name,
        "email": email,
        "phone": phone,
        "password": hashed_password,
        "role": "user",
        "vendor_status": None,
        "bio": ""
    }

    users.insert_one(user_data)

    return jsonify({
        "message": "Register berhasil"
    }), 201


# =========================
# LOGIN
# =========================
@auth_bp.route('/login', methods=['POST'])
def login():

    data = request.get_json()

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({
            "message": "Email dan password wajib diisi"
        }), 400

    user = users.find_one({
        "email": email
    })

    if not user:
        return jsonify({
            "message": "Email tidak ditemukan"
        }), 404

    valid_password = bcrypt.checkpw(
        password.encode("utf-8"),
        user["password"]
    )

    if not valid_password:
        return jsonify({
            "message": "Password salah"
        }), 401

    token = create_access_token(
        identity=str(user["_id"])
    )
    return jsonify({
        "message": "Login berhasil",
        "token": token,
        "role": user["role"],
        "vendor_status": user.get("vendor_status"),
        "name": user["name"],
        "email": user["email"],
        "phone": user.get("phone", "")
    }), 200


# =========================
# PROFILE
# =========================
@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def profile():

    current_user_id = get_jwt_identity()

    user = users.find_one({
        "_id": ObjectId(current_user_id)
    })

    if not user:
        return jsonify({
            "message": "User tidak ditemukan"
        }), 404

    return jsonify({
    "message": "Profile berhasil diambil",
    "data": {
        "id": str(user["_id"]),
        "name": user.get("name"),
        "email": user.get("email"),
        "phone": user.get("phone", ""),
        "bio": user.get("bio", ""),
        "role": user.get("role"),
        "vendor_status": user.get("vendor_status")
    }
}), 200

@auth_bp.route('/update-profile', methods=['PUT'])
@jwt_required()
def update_profile():

    current_user_id = get_jwt_identity()

    data = request.get_json()

    name = data.get("name")
    phone = data.get("phone")
    bio = data.get("bio")

    if not name:
        return jsonify({
            "message": "Nama wajib diisi"
        }), 400

    result = users.update_one(
        {
            "_id": ObjectId(current_user_id)
        },
        {
            "$set": {
                "name": name,
                "phone": phone,
                "bio": bio
            }
        }
    )

    print("UPDATE PROFILE HIT")
    print("USER ID:", current_user_id)
    print("MATCHED:", result.matched_count)
    print("MODIFIED:", result.modified_count)

    updated_user = users.find_one({
        "_id": ObjectId(current_user_id)
    })

    return jsonify({
        "message": "Profil berhasil diperbarui",
        "data": {
            "name": updated_user.get("name", ""),
            "email": updated_user.get("email", ""),
            "phone": updated_user.get("phone", ""),
            "bio": updated_user.get("bio", "")
        }
    }), 200


# =========================
# ADMIN ONLY
# =========================
@auth_bp.route('/admin-only', methods=['GET'])
@role_required("admin")
def admin_only():

    return jsonify({
        "message": "Selamat datang admin"
    }), 200


# =========================
# REGISTER VENDOR DIRECT
# untuk user baru daftar vendor dari onboarding
# endpoint: /api/auth/register-vendor
# =========================
@auth_bp.route('/register-vendor', methods=['POST'])
def register_vendor_direct():

    # =========================
    # FORM DATA
    # =========================
    name = request.form.get("name")
    email = request.form.get("email")
    password = request.form.get("password")

    business_name = request.form.get("business_name")
    category = request.form.get("category")
    description = request.form.get("description")
    location = request.form.get("location")
    phone = request.form.get("phone")

    owner_name = request.form.get("owner_name")
    nik = request.form.get("nik")
    npwp = request.form.get("npwp")

    # =========================
    # FILE DATA
    # =========================
    ktp_image = request.files.get("ktp_image")
    selfie_image = request.files.get("selfie_image")
    business_license = request.files.get("business_license")

    print("========== DIRECT REGISTER VENDOR ==========")
    print("NAME :", name)
    print("EMAIL :", email)
    print("BUSINESS NAME :", business_name)
    print("CATEGORY :", category)
    print("KTP :", ktp_image)
    print("SELFIE :", selfie_image)
    print("LICENSE :", business_license)

    # =========================
    # VALIDASI
    # =========================
    if not name or not email or not password:
        return jsonify({
            "message": "Nama, email, dan password wajib diisi"
        }), 400

    if not business_name or not category:
        return jsonify({
            "message": "Data bisnis wajib diisi"
        }), 400

    existing_user = users.find_one({
        "email": email
    })

    if existing_user:
        return jsonify({
            "message": "Email sudah digunakan"
        }), 400

    # =========================
    # HASH PASSWORD
    # =========================
    hashed_password = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    )

    # =========================
    # SIMPAN USER
    # =========================
    user_data = {
        "name": name,
        "email": email,
        "password": hashed_password,
        "role": "vendor_pending",
        "vendor_status": "pending"
    }

    result = users.insert_one(user_data)
    user_id = str(result.inserted_id)

    # =========================
    # SIMPAN FILE
    # =========================
    ktp_filename = None
    selfie_filename = None
    license_filename = None

    if ktp_image:
        ktp_filename = secure_filename(ktp_image.filename)
        ktp_image.save(
            os.path.join(UPLOAD_FOLDER, ktp_filename)
        )

    if selfie_image:
        selfie_filename = secure_filename(selfie_image.filename)
        selfie_image.save(
            os.path.join(UPLOAD_FOLDER, selfie_filename)
        )

    if business_license:
        license_filename = secure_filename(business_license.filename)
        business_license.save(
            os.path.join(UPLOAD_FOLDER, license_filename)
        )

    # =========================
    # SIMPAN VENDOR REGISTRATION
    # =========================
    vendor_data = {
        "user_id": user_id,

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

    vendor_registrations.insert_one(vendor_data)

    # =========================
    # TOKEN
    # =========================
    token = create_access_token(
        identity=user_id
    )

    return jsonify({
        "message": "Pendaftaran vendor berhasil",
        "token": token,
        "role": "vendor_pending",
        "vendor_status": "pending",
        "name": name,
        "email": email
    }), 201