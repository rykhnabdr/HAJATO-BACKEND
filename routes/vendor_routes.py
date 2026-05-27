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
vendor_services = db.vendor_services
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
    print(f"[VENDOR REGISTER] {business_name} berhasil daftar vendor")

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

@vendor_bp.route('/services', methods=['POST'])
@jwt_required()
def add_service():

    current_user_id = get_jwt_identity()

    name = request.form.get("name")
    category = request.form.get("category")
    description = request.form.get("description")
    price = request.form.get("price")
    capacity = request.form.get("capacity")
    duration = request.form.get("duration")
    image = request.files.get("image")

    user = users.find_one({
        "_id": ObjectId(current_user_id)
    })

    if not user:
        return jsonify({
            "message": "User tidak ditemukan"
        }), 404

    if user.get("role") != "vendor" or user.get("vendor_status") != "approved":
        return jsonify({
            "message": "Akun vendor belum diverifikasi admin"
        }), 403

    vendor = vendor_registrations.find_one({
        "user_id": current_user_id,
        "status": "approved"
    })

    if not vendor:
        return jsonify({
            "message": "Data vendor tidak ditemukan"
        }), 404

    if not name or not description or not price:
        return jsonify({
            "message": "Nama, deskripsi, dan harga wajib diisi"
        }), 400

    image_filename = ""

    if image:
        image_filename = secure_filename(image.filename)
        image.save(
            os.path.join(
                UPLOAD_FOLDER,
                image_filename
            )
        )

    service_data = {
        "vendor_id": str(vendor["_id"]),
        "user_id": current_user_id,
        "name": name,
        "category": category,
        "description": description,
        "price": int(price),
        "capacity": capacity,
        "duration": duration,
        "image": image_filename,
        "features": []
    }

    result = vendor_services.insert_one(service_data)

    print(f"[SERVICE ADD] {vendor.get('business_name')} menambah layanan {name}")

    return jsonify({
        "message": "Layanan berhasil ditambahkan",
        "data": {
            "id": str(result.inserted_id),
            "name": name,
            "description": description,
            "price": int(price),
            "image": image_filename,
            "features": []
        }
    }), 201
# =========================
# EDIT SERVICE
# =========================
@vendor_bp.route('/services/<service_id>', methods=['PUT'])
@jwt_required()
def edit_service(service_id):

    current_user_id = get_jwt_identity()

    service = vendor_services.find_one({
        "_id": ObjectId(service_id),
        "user_id": current_user_id
    })

    if not service:
        return jsonify({
            "message": "Layanan tidak ditemukan"
        }), 404

    name = request.form.get("name")
    description = request.form.get("description")
    price = request.form.get("price")

    image = request.files.get("image")

    update_data = {
        "name": name,
        "description": description,
        "price": int(price)
    }

    if image:
        image_filename = secure_filename(
            image.filename
        )

        image.save(
            os.path.join(
                UPLOAD_FOLDER,
                image_filename
            )
        )

        update_data["image"] = image_filename

    vendor_services.update_one(
        {
            "_id": ObjectId(service_id)
        },
        {
            "$set": update_data
        }
    )

    print(f"[SERVICE EDIT] {name} berhasil diedit")

    return jsonify({
        "message": "Layanan berhasil diupdate"
    }), 200


# =========================
# DELETE SERVICE
# =========================
@vendor_bp.route('/services/<service_id>', methods=['DELETE'])
@jwt_required()
def delete_service(service_id):

    current_user_id = get_jwt_identity()

    service = vendor_services.find_one({
        "_id": ObjectId(service_id),
        "user_id": current_user_id
    })

    if not service:
        return jsonify({
            "message": "Layanan tidak ditemukan"
        }), 404

    vendor_services.delete_one({
        "_id": ObjectId(service_id)
    })

    print(f"[SERVICE DELETE] {service.get('name')} berhasil dihapus")

    return jsonify({
        "message": "Layanan berhasil dihapus"
    }), 200
# =========================
# GET MY SERVICES
# =========================
@vendor_bp.route('/my-services', methods=['GET'])
@jwt_required()
def get_my_services():

    current_user_id = get_jwt_identity()

    services = list(
        vendor_services.find({
            "user_id": current_user_id
        }).sort("_id", -1)
    )

    data = []

    for s in services:
       data.append({
    "id": str(s["_id"]),
    "name": s.get("name", ""),
    "description": s.get("description", ""),
    "price": s.get("price", 0),
    "image": s.get("image", ""),
    "features": s.get("features", [])
})

    return jsonify({
        "message": "Layanan berhasil diambil",
        "data": data
    }), 200


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
    print(f"[VENDOR APPROVED] {vendor['business_name']} disetujui admin")

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
@vendor_bp.route('/public-vendors', methods=['GET'])
def public_vendors():

    vendors = list(
        vendor_registrations.find({
            "status": "approved"
        }).sort("_id", -1)
    )

    data = []

    for vendor in vendors:
        services = list(
            vendor_services.find({
                "vendor_id": str(vendor["_id"])
            })
        )

        print("VENDOR:", vendor.get("business_name"))
        print("JUMLAH SERVICES:", len(services))
        print("NAMA SERVICES:", [s.get("name") for s in services])

        packages = []

        starting_price = 0
        image_url = ""

        for s in services:
            price = s.get("price", 0)

            if starting_price == 0 or price < starting_price:
                starting_price = price

            if not image_url and s.get("image"):
                image_url = s.get("image")

            packages.append({
                "id": str(s["_id"]),
                "name": s.get("name", ""),
                "category": s.get("category", ""),
                "description": s.get("description", ""),
                "price": price,
                "capacity": s.get("capacity", ""),
                "duration": s.get("duration", ""),
                "image": s.get("image", ""),
                "features": s.get("features", [])
            })

        data.append({
            "id": str(vendor["_id"]),
            "name": vendor.get("business_name", ""),
            "category": vendor.get("category", ""),
            "description": vendor.get("description", ""),
            "location": vendor.get("location", ""),
            "phone": vendor.get("phone", ""),
            "rating": 5.0,
            "review_count": 0,
            "image_url": image_url,
            "gallery": [
                p["image"] for p in packages if p["image"]
            ],
            "packages": packages,
            "starting_price": starting_price,
            "is_featured": True
        })

    return jsonify({
        "message": "Vendor berhasil diambil",
        "data": data
    }), 200