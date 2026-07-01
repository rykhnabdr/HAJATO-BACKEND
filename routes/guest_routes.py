from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from config.mongo import db
from bson.objectid import ObjectId
from datetime import datetime

# ── 🟢 IMPORT LOG SERVICE BIAR BISA MASUK DASHBOARD ──
from services.log_service import create_activity_log

guest_bp = Blueprint('guest', __name__)

# ── 1. AMBIL DAFTAR TAMU PER ACARA (GET /api/guests/<event_id>) ──
@guest_bp.route('/<event_id>', methods=['GET'])
@jwt_required()
def get_event_guests(event_id):
    try:
        raw_guests = list(db.guests.find({"event_id": ObjectId(event_id)}).sort("created_at", -1))
        
        formatted_guests = []
        for g in raw_guests:
            formatted_guests.append({
                "id": str(g["_id"]),
                "name": g.get("name", "-"),
                "phone": g.get("phone", ""),
                "status": g.get("status", "pending"),
                "qr_code": g.get("qr_code", "")
            })

        return jsonify({
            "status": "success",
            "data": formatted_guests
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ── 2. TAMBAH TAMU MANUAL (POST /api/guests/<event_id>/add) ──
# ── 2. TAMBAH TAMU MANUAL (POST /api/guests/<event_id>/add) ──
@guest_bp.route('/<event_id>/add', methods=['POST'])
@jwt_required()
def add_guest_manual(event_id):
    try:
        current_user_id = get_jwt_identity()
        current_user = db.users.find_one({"_id": ObjectId(current_user_id)}) or {}

        data = request.get_json()
        name = data.get('name')
        # 🟢 Ganti phone jadi address (untuk menangkap data Asal/Rombongan dari Flutter)
        address = data.get('address', '-').strip() 

        if not name:
            return jsonify({"status": "error", "message": "Nama tamu wajib diisi"}), 400

        # Suffix acak berbasis waktu sebagai pengganti nomor HP agar QR Code tetap unik
        unique_suffix = datetime.utcnow().strftime("%H%M%S%f")

        new_guest = {
            "event_id": ObjectId(event_id),
            "name": name,
            "address": address,  # 🟢 Simpan data Asal/Rombongan ke database
            "phone": "-",        # Nomor HP dimatikan, isi default strip saja
            "status": "attended",  # 🟢 OTOMATIS LANGSUNG HADIR (BYPASS SCAN QR)
            "qr_code": f"HAJATO-BYPASS-{event_id}-{unique_suffix}",  
            "created_at": datetime.utcnow()
        }

        result = db.guests.insert_one(new_guest)

        # 🟢 CATAT LOG AKTIVITAS DASHBOARD (SINKRON PER ACARA)
        create_activity_log(
            user_id=current_user_id,
            email=current_user.get("email", ""),
            name=current_user.get("name", ""),
            role=current_user.get("role", "user"),
            action="ADD_GUEST",
            title="Tamu Manual Terdaftar",
            description=f"{name} ({address}) berhasil didaftarkan langsung oleh panitia.",
            target_type="guest",
            target_id=result.inserted_id,
            metadata={
                "event_id": str(event_id),
                "guest_name": name,
                "guest_address": address
            }
        )

        return jsonify({
            "status": "success",
            "message": f"Tamu {name} berhasil masuk sistem!",
            "data": {
                "id": str(result.inserted_id),
                "name": name,
                "address": address,
                "status": "attended"
            }
        }), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
# ── 3. VERIFIKASI CHECK-IN SCAN QR (POST /api/guests/checkin) ──
@guest_bp.route('/checkin', methods=['POST'])
@jwt_required()
def checkin_guest():
    try:
        current_user_id = get_jwt_identity()
        current_user = db.users.find_one({"_id": ObjectId(current_user_id)}) or {}

        data = request.get_json()
        qr_code = data.get('qr_code')

        if not qr_code:
            return jsonify({"status": "error", "message": "Data QR Code kosong"}), 400

        guest = db.guests.find_one({"qr_code": qr_code})

        if not guest:
            return jsonify({"status": "error", "message": "QR Code tidak valid / Tamu tidak ditemukan"}), 404

        if guest.get("status") == "attended":
            return jsonify({
                "status": "error", 
                "message": f"Tamu atas nama {guest['name']} sudah melakukan check-in sebelumnya!"
            }), 400 

        db.guests.update_one(
            {"_id": guest["_id"]},
            {"$set": {
                "status": "attended", 
                "updated_at": datetime.utcnow()
            }}
        )

        # ── 🟢 CATAT LOG KUNCI: SCAN QR TAMU BERHASIL (DASHBOARD SYNC PER ACARA) ──
        create_activity_log(
            user_id=current_user_id,
            email=current_user.get("email", ""),
            name=current_user.get("name", ""),
            role=current_user.get("role", "user"),
            action="CHECKIN_GUEST",
            title="Tamu Check-in",
            description=f"{guest['name']} berhasil masuk ke lokasi acara via QR Scan.",
            target_type="guest",
            target_id=guest["_id"],
            metadata={
                "event_id": str(guest.get("event_id")), # ── 🟢 KUNCI UTAMA FILTER DASHBOARD APP.PY LO
                "guest_name": guest['name']
            }
        )

        return jsonify({
            "status": "success",
            "message": f"Check-in sukses. Selamat datang {guest['name']}!",
            "data": {
                "name": guest["name"],
                "status": "attended"
            }
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ── 4. UPDATE STATUS TAMU MANUAL (PUT /api/guests/status/<guest_id>) ──
@guest_bp.route('/status/<guest_id>', methods=['PUT'])
@jwt_required()
def update_guest_status(guest_id):
    try:
        data = request.get_json()
        new_status = data.get('status') 

        db.guests.update_one(
            {"_id": ObjectId(guest_id)},
            {"$set": {"status": new_status, "updated_at": datetime.utcnow()}}
        )
        return jsonify({
            "status": "success",
            "message": f"Status tamu berhasil diubah menjadi {new_status}"
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ── 5. HAPUS TAMU PERMANEN (DELETE /api/guests/delete/<guest_id>) ──
@guest_bp.route('/delete/<guest_id>', methods=['DELETE'])
@jwt_required()
def delete_guest_permanently(guest_id):
    try:
        db.guests.delete_one({"_id": ObjectId(guest_id)})
        return jsonify({
            "status": "success",
            "message": "Data tamu berhasil dihapus secara permanen"
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ── 6. PENDAFTARAN MANDIRI TAMU DARI WEB UNDANGAN (POST /api/guests/<event_id>/register-self) ──
@guest_bp.route('/<event_id>/register-self', methods=['POST'])
def register_guest_self(event_id):
    try:
        data = request.get_json() or {}
        name = data.get('name', '').strip()

        if not name:
            return jsonify({"status": "error", "message": "Nama wajib diisi untuk membuka undangan"}), 400

        new_guest = {
            "event_id": ObjectId(event_id),
            "name": name,
            "phone": "-",
            "status": "pending",
            "qr_code": "", 
            "created_at": datetime.utcnow()
        }

        result = db.guests.insert_one(new_guest)
        guest_id = str(result.inserted_id)

        generated_qr = f"HAJATO-{guest_id}"

        db.guests.update_one(
            {"_id": ObjectId(guest_id)},
            {"$set": {"qr_code": generated_qr}}
        )

        return jsonify({
            "status": "success",
            "message": "Berhasil terdaftar sebagai tamu!",
            "data": {
                "id": guest_id,
                "name": name,
                "status": "pending",
                "qr_code": generated_qr
            }
        }), 201

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500