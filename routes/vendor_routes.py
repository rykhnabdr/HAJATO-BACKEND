import os
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId
from datetime import datetime
from services.log_service import create_activity_log

from config.mongo import db

vendor_bp = Blueprint(
    'vendor',
    __name__,
    url_prefix='/api/vendor'
)

# ── 🟢 CONFIG GLOBAL DIRECTORY FOR UPLOADS ───────
UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

vendor_registrations = db.vendor_registrations
users = db.users
vendor_services = db.vendor_services
reviews = db.reviews

# ==============================================================================
# GET MY VENDOR DATA
# ==============================================================================
@vendor_bp.route('/my-data', methods=['GET'])
@jwt_required()
def get_my_vendor_data():
    current_user_id = get_jwt_identity()

    vendor = vendor_registrations.find_one({
        "user_id": current_user_id
    })

    if not vendor:
        return jsonify({
            "message": "Data vendor tidak ditemukan"
        }), 404

    return jsonify({
        "message": "Data vendor berhasil diambil",
        "data": {
            "id": str(vendor["_id"]),
            "user_id": vendor.get("user_id", ""),
            "business_name": vendor.get("business_name", ""),
            "category": vendor.get("category", ""),
            "description": vendor.get("description", ""),
            "location": vendor.get("location", ""),
            "phone": vendor.get("phone", ""),
            "owner_name": vendor.get("owner_name", ""),
            "nik": vendor.get("nik", ""),
            "npwp": vendor.get("npwp", ""),
            "ktp_image": vendor.get("ktp_image", ""),
            "selfie_image": vendor.get("selfie_image", ""),
            "business_license": vendor.get("business_license", ""),
            "status": vendor.get("status", "pending"),
            "created_at": str(vendor.get("created_at", ""))
        }
    }), 200

# ==============================================================================
# UPDATE MY VENDOR DATA
# ==============================================================================
@vendor_bp.route('/my-data', methods=['PUT'])
@jwt_required()
def update_my_vendor_data():
    current_user_id = get_jwt_identity()

    current_user = users.find_one({
        "_id": ObjectId(current_user_id)
    })

    if not current_user:
        return jsonify({
            "message": "User tidak ditemukan"
        }), 404

    vendor = vendor_registrations.find_one({
        "user_id": current_user_id
    })

    if not vendor:
        return jsonify({
            "message": "Data vendor tidak ditemukan"
        }), 404

    business_name = request.form.get("business_name")
    category = request.form.get("category")
    description = request.form.get("description")
    location = request.form.get("location")
    phone = request.form.get("phone")
    owner_name = request.form.get("owner_name")
    nik = request.form.get("nik")
    npwp = request.form.get("npwp")

    ktp_image = request.files.get("ktp_image")
    selfie_image = request.files.get("selfie_image")
    business_license = request.files.get("business_license")

    update_data = {}

    if business_name:
        update_data["business_name"] = business_name
    if category:
        update_data["category"] = category
    if description:
        update_data["description"] = description
    if location:
        update_data["location"] = location
    if phone:
        update_data["phone"] = phone
    if owner_name:
        update_data["owner_name"] = owner_name
    if nik:
        update_data["nik"] = nik
    if npwp:
        update_data["npwp"] = npwp

    if ktp_image:
        ktp_filename = secure_filename(ktp_image.filename)
        ktp_image.save(os.path.join(UPLOAD_FOLDER, ktp_filename))
        update_data["ktp_image"] = ktp_filename

    if selfie_image:
        selfie_filename = secure_filename(selfie_image.filename)
        selfie_image.save(os.path.join(UPLOAD_FOLDER, selfie_filename))
        update_data["selfie_image"] = selfie_filename

    if business_license:
        license_filename = secure_filename(business_license.filename)
        business_license.save(os.path.join(UPLOAD_FOLDER, license_filename))
        update_data["business_license"] = license_filename

    if not update_data:
        return jsonify({
            "message": "Tidak ada data yang diubah"
        }), 400

    update_data["updated_at"] = datetime.utcnow()

    vendor_registrations.update_one(
        {"_id": vendor["_id"]},
        {"$set": update_data}
    )

    if owner_name and owner_name.strip():
        users.update_one(
            {"_id": ObjectId(current_user_id)},
            {
                "$set": {
                    "name": owner_name.strip(),
                    "updated_at": datetime.utcnow()
                }
            }
        )

    updated_vendor = vendor_registrations.find_one({
        "_id": vendor["_id"]
    })

    create_activity_log(
        user_id=current_user_id,
        email=current_user.get("email", ""),
        name=current_user.get("name", ""),
        role=current_user.get("role", "vendor"),
        action="UPDATE_VENDOR_PROFILE",
        title="Update data vendor",
        description=f"Anda memperbarui data vendor {updated_vendor.get('business_name', '-')}.",
        target_type="vendor",
        target_id=vendor["_id"],
        metadata={
            "vendor_id": str(vendor["_id"]),
            "business_name": updated_vendor.get("business_name", ""),
            "category": updated_vendor.get("category", ""),
            "location": updated_vendor.get("location", ""),
            "phone": updated_vendor.get("phone", ""),
            "updated_fields": list(update_data.keys())
        }
    )

    return jsonify({
        "message": "Data vendor berhasil diperbarui",
        "data": {
            "id": str(updated_vendor["_id"]),
            "business_name": updated_vendor.get("business_name", ""),
            "category": updated_vendor.get("category", ""),
            "description": updated_vendor.get("description", ""),
            "location": updated_vendor.get("location", ""),
            "phone": updated_vendor.get("phone", ""),
            "owner_name": updated_vendor.get("owner_name", ""),
            "nik": updated_vendor.get("nik", ""),
            "npwp": updated_vendor.get("npwp", ""),
            "ktp_image": updated_vendor.get("ktp_image", ""),
            "selfie_image": updated_vendor.get("selfie_image", ""),
            "business_license": updated_vendor.get("business_license", ""),
            "status": updated_vendor.get("status", "pending")
        }
    }), 200

# ==============================================================================
# REGISTER VENDOR
# ==============================================================================
@vendor_bp.route('/register-vendor', methods=['POST'])
@jwt_required()
def register_vendor():
    current_user_id = get_jwt_identity()

    current_user = users.find_one({
        "_id": ObjectId(current_user_id)
    })

    if not current_user:
        return jsonify({
            "message": "User tidak ditemukan"
        }), 404

    business_name = request.form.get("business_name")
    category = request.form.get("category")
    description = request.form.get("description")
    location = request.form.get("location")
    phone = request.form.get("phone")
    owner_name = request.form.get("owner_name")
    nik = request.form.get("nik")
    npwp = request.form.get("npwp")

    ktp_image = request.files.get("ktp_image")
    selfie_image = request.files.get("selfie_image")
    business_license = request.files.get("business_license")

    if not business_name or not category:
        return jsonify({
            "message": "Data bisnis wajib diisi"
        }), 400

    existing_vendor = vendor_registrations.find_one({
        "user_id": current_user_id
    })

    if existing_vendor:
        return jsonify({
            "message": "Anda sudah pernah mendaftar vendor"
        }), 400

    ktp_filename = None
    selfie_filename = None
    license_filename = None

    if ktp_image:
        ktp_filename = secure_filename(ktp_image.filename)
        ktp_image.save(os.path.join(UPLOAD_FOLDER, ktp_filename))
    if selfie_image:
        selfie_filename = secure_filename(selfie_image.filename)
        selfie_image.save(os.path.join(UPLOAD_FOLDER, selfie_filename))
    if business_license:
        license_filename = secure_filename(business_license.filename)
        business_license.save(os.path.join(UPLOAD_FOLDER, license_filename))

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
        "status": "pending",
        "created_at": datetime.utcnow()
    }

    result = vendor_registrations.insert_one(vendor_data)

    users.update_one(
        {"_id": ObjectId(current_user_id)},
        {
            "$set": {
                "vendor_status": "pending",
                "role": "vendor_pending"
            }
        }
    )

    create_activity_log(
        user_id=current_user_id,
        email=current_user.get("email", ""),
        name=current_user.get("name", ""),
        role="vendor_pending",
        action="VENDOR_REGISTER",
        title="Pendaftaran vendor",
        description=f"Anda melakukan pendaftaran sebagai vendor dengan nama usaha {business_name}.",
        target_type="vendor",
        target_id=result.inserted_id,
        metadata={
            "vendor_id": str(result.inserted_id),
            "business_name": business_name,
            "category": category,
            "location": location,
            "phone": phone,
            "status": "pending"
        }
    )

    print(f"[VENDOR REGISTER] {business_name} berhasil daftar vendor")

    return jsonify({
        "message": "Pendaftaran vendor berhasil dikirim"
    }), 201

# ==============================================================================
# ADD SERVICE / PACKAGE
# ==============================================================================
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

    try:
        price = int(price)
    except Exception:
        return jsonify({
            "message": "Harga harus berupa angka"
        }), 400

    image_filename = ""
    if image:
        image_filename = secure_filename(image.filename)
        image.save(os.path.join(UPLOAD_FOLDER, image_filename))

    service_data = {
        "vendor_id": str(vendor["_id"]),
        "user_id": current_user_id,
        "name": name,
        "category": category,
        "description": description,
        "price": price,
        "capacity": capacity,
        "duration": duration,
        "image": image_filename,
        "features": [],
        "created_at": datetime.utcnow()
    }

    result = vendor_services.insert_one(service_data)

    create_activity_log(
        user_id=current_user_id,
        email=user.get("email", ""),
        name=user.get("name", ""),
        role="vendor",
        action="CREATE_PACKAGE",
        title="Menambahkan paket layanan",
        description=f"Anda menambahkan paket layanan {name} untuk vendor {vendor.get('business_name')}.",
        target_type="service",
        target_id=result.inserted_id,
        metadata={
            "service_id": str(result.inserted_id),
            "vendor_id": str(vendor["_id"]),
            "vendor_name": vendor.get("business_name"),
            "service_name": name,
            "category": category,
            "price": price,
            "capacity": capacity,
            "duration": duration
        }
    )

    print(f"[SERVICE ADD] {vendor.get('business_name')} menambah layanan {name}")

    return jsonify({
        "message": "Layanan berhasil ditambahkan",
        "data": {
            "id": str(result.inserted_id),
            "name": name,
            "description": description,
            "price": price,
            "image": image_filename,
            "features": []
        }
    }), 201

# ==============================================================================
# EDIT SERVICE / PACKAGE
# ==============================================================================
@vendor_bp.route('/services/<service_id>', methods=['PUT'])
@jwt_required()
def edit_service(service_id):
    current_user_id = get_jwt_identity()

    if not ObjectId.is_valid(service_id):
        return jsonify({
            "message": "ID layanan tidak valid"
        }), 400

    user = users.find_one({
        "_id": ObjectId(current_user_id)
    })

    if not user:
        return jsonify({
            "message": "User tidak ditemukan"
        }), 404

    service = vendor_services.find_one({
        "_id": ObjectId(service_id),
        "user_id": current_user_id
    })

    if not service:
        return jsonify({
            "message": "Layanan tidak ditemukan"
        }), 404

    vendor = vendor_registrations.find_one({
        "_id": ObjectId(service.get("vendor_id"))
    })

    name = request.form.get("name") or service.get("name")
    description = request.form.get("description") or service.get("description")
    price = request.form.get("price") or service.get("price")
    image = request.files.get("image")

    try:
        price = int(price)
    except Exception:
        return jsonify({
            "message": "Harga harus berupa angka"
        }), 400

    update_data = {
        "name": name,
        "description": description,
        "price": price,
        "updated_at": datetime.utcnow()
    }

    if image:
        image_filename = secure_filename(image.filename)
        image.save(os.path.join(UPLOAD_FOLDER, image_filename))
        update_data["image"] = image_filename

    vendor_services.update_one(
        {"_id": ObjectId(service_id)},
        {"$set": update_data}
    )

    create_activity_log(
        user_id=current_user_id,
        email=user.get("email", ""),
        name=user.get("name", ""),
        role="vendor",
        action="UPDATE_PACKAGE",
        title="Mengubah paket layanan",
        description=f"Anda mengubah paket layanan {name}.",
        target_type="service",
        target_id=service_id,
        metadata={
            "service_id": service_id,
            "vendor_id": service.get("vendor_id"),
            "vendor_name": vendor.get("business_name") if vendor else "",
            "old_service_name": service.get("name"),
            "new_service_name": name,
            "old_price": service.get("price"),
            "new_price": price
        }
    )

    print(f"[SERVICE EDIT] {name} berhasil diedit")

    return jsonify({
        "message": "Layanan berhasil diupdate"
    }), 200

# ==============================================================================
# DELETE SERVICE / PACKAGE
# ==============================================================================
@vendor_bp.route('/services/<service_id>', methods=['DELETE'])
@jwt_required()
def delete_service(service_id):
    current_user_id = get_jwt_identity()

    if not ObjectId.is_valid(service_id):
        return jsonify({
            "message": "ID layanan tidak valid"
        }), 400

    user = users.find_one({
        "_id": ObjectId(current_user_id)
    })

    if not user:
        return jsonify({
            "message": "User tidak ditemukan"
        }), 404

    service = vendor_services.find_one({
        "_id": ObjectId(service_id),
        "user_id": current_user_id
    })

    if not service:
        return jsonify({
            "message": "Layanan tidak ditemukan"
        }), 404

    vendor = vendor_registrations.find_one({
        "_id": ObjectId(service.get("vendor_id"))
    })

    vendor_services.delete_one({
        "_id": ObjectId(service_id)
    })

    create_activity_log(
        user_id=current_user_id,
        email=user.get("email", ""),
        name=user.get("name", ""),
        role="vendor",
        action="DELETE_PACKAGE",
        title="Menghapus paket layanan",
        description=f"Anda menghapus paket layanan {service.get('name')}.",
        target_type="service",
        target_id=service_id,
        metadata={
            "service_id": service_id,
            "vendor_id": service.get("vendor_id"),
            "vendor_name": vendor.get("business_name") if vendor else "",
            "service_name": service.get("name"),
            "price": service.get("price")
        }
    )

    print(f"[SERVICE DELETE] {service.get('name')} berhasil dihapus")

    return jsonify({
        "message": "Layanan berhasil dihapus"
    }), 200

# ==============================================================================
# GET MY SERVICES
# ==============================================================================
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

# ==============================================================================
# VENDOR DASHBOARD STATS
# ==============================================================================
@vendor_bp.route('/dashboard-stats', methods=['GET'])
@jwt_required()
def vendor_dashboard_stats():
    current_user_id = get_jwt_identity()

    vendor = vendor_registrations.find_one({
        "user_id": current_user_id,
        "status": "approved"
    })

    if not vendor:
        return jsonify({
            "message": "Vendor tidak ditemukan"
        }), 404

    vendor_id = str(vendor["_id"])

    booking_data = list(
        db.bookings.find({
            "vendor_id": vendor_id,
            "payment_status": "paid"
        })
    )

    package_counter = {}
    for booking in booking_data:
        package_name = booking.get("package_name", "Paket")
        if package_name not in package_counter:
            package_counter[package_name] = 0
        package_counter[package_name] += 1

    top_packages = [
        {
            "package_name": name,
            "total_booking": total
        }
        for name, total in package_counter.items()
    ]

    top_packages = sorted(
        top_packages,
        key=lambda x: x["total_booking"],
        reverse=True
    )[:5]

    total_booking = len(booking_data)

    completed_booking = len([
        booking for booking in booking_data
        if booking.get("booking_status") == "completed"
    ])

    total_pendapatan = sum(
        booking.get("total_price", 0)
        for booking in booking_data
    )

    dana_dicairkan = sum(
        booking.get("total_price", 0)
        for booking in booking_data
        if booking.get("vendor_payout_status") == "released"
    )

    dana_ditahan = sum(
        booking.get("total_price", 0)
        for booking in booking_data
        if booking.get("vendor_payout_status") == "hold"
    )

    review_data = list(
        reviews.find({
            "vendor_id": vendor_id
        })
    )

    total_reviews = len(review_data)
    average_rating = 0

    if total_reviews > 0:
        average_rating = round(
            sum(
                review.get("rating", 0)
                for review in review_data
            ) / total_reviews,
            1
        )

    return jsonify({
        "vendor_id": vendor_id,
        "total_booking": total_booking,
        "completed_booking": completed_booking,
        "total_pendapatan": total_pendapatan,
        "dana_dicairkan": dana_dicairkan,
        "dana_ditahan": dana_ditahan,
        "average_rating": average_rating,
        "total_reviews": total_reviews,
        "top_packages": top_packages,
    }), 200

# ==============================================================================
# APPROVE VENDOR
# ==============================================================================
@vendor_bp.route('/approve-vendor/<vendor_id>', methods=['PUT'])
@jwt_required()
def approve_vendor(vendor_id):
    if not ObjectId.is_valid(vendor_id):
        return jsonify({
            "message": "ID vendor tidak valid"
        }), 400

    vendor = vendor_registrations.find_one({
        "_id": ObjectId(vendor_id)
    })

    if not vendor:
        return jsonify({
            "message": "Vendor tidak ditemukan"
        }), 404

    vendor_registrations.update_one(
        {"_id": ObjectId(vendor_id)},
        {"$set": {"status": "approved"}}
    )

    users.update_one(
        {"_id": ObjectId(vendor["user_id"])},
        {
            "$set": {
                "role": "vendor",
                "vendor_status": "approved"
            }
        }
    )

    vendor_user = users.find_one({
        "_id": ObjectId(vendor["user_id"])
    })

    if vendor_user:
        create_activity_log(
            user_id=vendor["user_id"],
            email=vendor_user.get("email", ""),
            name=vendor_user.get("name", ""),
            role="vendor",
            action="VENDOR_APPROVED",
            title="Vendor disetujui",
            description=f"Pendaftaran vendor {vendor.get('business_name')} telah disetujui admin.",
            target_type="vendor",
            target_id=vendor_id,
            metadata={
                "vendor_id": vendor_id,
                "business_name": vendor.get("business_name"),
                "status": "approved"
            }
        )

    print(f"[VENDOR APPROVED] {vendor['business_name']} disetujui admin")

    return jsonify({
        "message": "Vendor berhasil diapprove"
    }), 200

# ==============================================================================
# REJECT VENDOR
# ==============================================================================
@vendor_bp.route('/reject-vendor/<vendor_id>', methods=['PUT'])
@jwt_required()
def reject_vendor(vendor_id):
    if not ObjectId.is_valid(vendor_id):
        return jsonify({
            "message": "ID vendor tidak valid"
        }), 400

    vendor = vendor_registrations.find_one({
        "_id": ObjectId(vendor_id)
    })

    if not vendor:
        return jsonify({
            "message": "Vendor tidak ditemukan"
        }), 404

    vendor_registrations.update_one(
        {"_id": ObjectId(vendor_id)},
        {"$set": {"status": "rejected"}}
    )

    users.update_one(
        {"_id": ObjectId(vendor["user_id"])},
        {
            "$set": {
                "role": "user",
                "vendor_status": "rejected"
            }
        }
    )

    vendor_user = users.find_one({
        "_id": ObjectId(vendor["user_id"])
    })

    if vendor_user:
        create_activity_log(
            user_id=vendor["user_id"],
            email=vendor_user.get("email", ""),
            name=vendor_user.get("name", ""),
            role="user",
            action="VENDOR_REJECTED",
            title="Vendor ditolak",
            description=f"Pendaftaran vendor {vendor.get('business_name')} ditolak oleh admin.",
            target_type="vendor",
            target_id=vendor_id,
            metadata={
                "vendor_id": vendor_id,
                "business_name": vendor.get("business_name"),
                "status": "rejected"
            }
        )

    return jsonify({
        "message": "Vendor ditolak"
    }), 200

# ==============================================================================
# PUBLIC VENDORS
# ==============================================================================
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

        vendor_reviews = list(
            reviews.find({
                "vendor_id": str(vendor["_id"])
            })
        )

        review_count = len(vendor_reviews)
        average_rating = 0

        if review_count > 0:
            average_rating = round(
                sum(
                    review.get("rating", 0)
                    for review in vendor_reviews
                ) / review_count,
                1
            )

        data.append({
            "id": str(vendor["_id"]),
            "vendor_user_id": vendor.get("user_id", ""),
            "name": vendor.get("business_name", ""),
            "category": vendor.get("category", ""),
            "description": vendor.get("description", ""),
            "location": vendor.get("location", ""),
            "phone": vendor.get("phone", ""),
            "rating": average_rating,
            "review_count": review_count,
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

# ==============================================================================
# PAYOUT HISTORY
# ==============================================================================
@vendor_bp.route('/payout-history', methods=['GET'])
@jwt_required()
def payout_history():
    current_user_id = get_jwt_identity()

    vendor = vendor_registrations.find_one({
        "user_id": current_user_id,
        "status": "approved"
    })

    if not vendor:
        return jsonify({
            "message": "Vendor tidak ditemukan"
        }), 404

    vendor_id = str(vendor["_id"])

    payout_data = list(
        db.bookings.find({
            "vendor_id": vendor_id,
            "vendor_payout_status": "released"
        }).sort("_id", -1)
    )

    result = []
    for booking in payout_data:
        result.append({
            "id": str(booking["_id"]),
            "customer_name": booking.get("customer_name", ""),
            "package_name": booking.get("package_name", ""),
            "event_date": booking.get("event_date", ""),
            "total_price": booking.get("total_price", 0),
            "vendor_payout_status": booking.get("vendor_payout_status", ""),
        })

    return jsonify({
        "data": result
    }), 200