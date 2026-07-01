import os
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from config.mongo import db  # Menyelaraskan dengan instance DB kamu
from bson.objectid import ObjectId
from services.log_service import create_activity_log  # Integrasi log bawaanmu
from datetime import datetime
import json # 🟢 WAJIB: Untuk membaca text string JSON rundown dari Flutter

event_bp = Blueprint('event', __name__)

# ==========================================
# 1. ENDPOINT: MEMBUAT ACARA BARU (POST /api/events/create) -> DENGAN UPLOAD FOTO HP
# ==========================================
@event_bp.route('/create', methods=['POST'])
@jwt_required()
def create_event():
    current_user_id = get_jwt_identity()  # Mengambil ID user dari token JWT
    
    # 🟢 CARA BARU: Ambil data teks dari request.form (Bukan request.get_json lagi, anti error 415)
    nama_acara = request.form.get('name')
    tanggal_acara = request.form.get('date')
    lokasi_acara = request.form.get('location')
    deskripsi_acara = request.form.get('description', '')
    time_acara = request.form.get('time', '09:00')
    
    # ── 🟢 TAMBAHAN BARU: Tangkap data info rekening bank dari Flutter ──
    rekening_acara = request.form.get('rekening', '-') 

    # ── 🟢 SELESAI INTEGRASI: Tangkap parameter string pilihan template dari Flutter ──
    template_pilihan = request.form.get('template', 'template_1')

    # ── 🟢 FIX UTAMA MULTI-EVENT: Tangkap data sakelar kategori dari Flutter ──
    kategori_acara = request.form.get('category', 'wedding')

    if not nama_acara or not tanggal_acara or not lokasi_acara:
        return jsonify({"status": "error", "message": "Nama acara, tanggal, dan lokasi wajib diisi"}), 400

    # Ambil data user pembuka untuk kebutuhan activity log
    user = db.users.find_one({"_id": ObjectId(current_user_id)})
    if not user:
        return jsonify({"status": "error", "message": "User tidak ditemukan"}), 404

    # 🟢 PARSING RUNDOWN: Decode string JSON array rundown dari Flutter menjadi List Python
    rundown_raw = request.form.get('rundown', '[]')
    try:
        rundown_list = json.loads(rundown_raw)
    except Exception:
        rundown_list = []

    # 🟢 PROSES MULTIPART FILE GALLERY (VERSI FIX ANTI-GAGAL)
    uploaded_files = request.files.getlist('gallery')
    gallery_paths = []

    for file in uploaded_files:
        if file and file.filename != '':
            # 1. Ambil ekstensi asli file secara aman (misal: .jpg atau .png)
            ext = os.path.splitext(file.filename)[1].lower()
            if not ext:
                ext = '.jpg' # Jaga-jaga jika ekstensi tidak terbaca
                
            # 2. Bikin nama file baru murni dari timestamp agar tidak bentrok dan anti-error karakter
            unique_filename = f"{datetime.utcnow().timestamp()}_{int(datetime.utcnow().microsecond)}{ext}"
            
            # 3. Tentukan path lengkap folder tujuan simpan
            save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'gallery', unique_filename)
            
            # 4. Perintah simpan berkas fisik ke folder uploads/gallery
            file.save(save_path)
            
            # 5. Masukkan nama file unik ke array MongoDB
            gallery_paths.append(unique_filename)

    # Susun struktur dokumen MongoDB Atlas lengkap dengan field baru
    new_event = {
        "user_id": ObjectId(current_user_id),
        "name": nama_acara,
        "date": tanggal_acara,
        "time": time_acara,
        "location": lokasi_acara,
        "description": deskripsi_acara,
        "rekening": rekening_acara, 
        "template": template_pilihan,  # ── 🟢 Pilihan tema tersimpan permanen di database
        "category": kategori_acara,    # ── 🟢 FIX: Sakelar kategori multi-event resmi terdaftar di DB
        "rundown": rundown_list,    # 🟢 Menyimpan array susunan kegiatan
        "gallery": gallery_paths,   # 🟢 Menyimpan array file/path foto pengantin
        "created_at": datetime.utcnow()
    }

    result = db.events.insert_one(new_event)
    event_id = str(result.inserted_id)

    # =========================
    # CATAT LOG AKTIVITAS (Menggunakan fungsi log bawaanmu)
    # =========================
    create_activity_log(
        user_id=current_user_id,
        email=user.get("email", ""),
        name=user.get("name", ""),
        role=user.get("role", "user"),
        action="CREATE_EVENT",
        title="Membuat Acara Baru",
        description=f"Berhasil membuat acara {new_event['name']} berlokasi di {new_event['location']}.",
        target_type="event",
        target_id=event_id,
        metadata={
            "event_id": event_id,
            "name": new_event["name"],
            "date": new_event["date"],
            "category": new_event["category"]
        }
    )

    return jsonify({
        "status": "success",
        "message": "Acara berhasil dibuat!",
        "data": {
            "id": event_id,
            "name": new_event["name"],
            "date": new_event["date"],
            "location": new_event["location"],
            "description": new_event["description"],
            "rekening": new_event["rekening"], 
            "template": new_event["template"], 
            "category": new_event["category"], 
            "rundown": new_event["rundown"],
            "gallery": new_event["gallery"]
        }
    }), 201


# ==========================================
# 2. ENDPOINT: MENGAMBIL DAFTAR ACARA USER (GET /api/events/)
# ==========================================
@event_bp.route('/', methods=['GET'])
@jwt_required()
def get_user_events():
    current_user_id = get_jwt_identity()
    
    # Mencari semua acara milik user yang sedang login
    events_cursor = db.events.find({"user_id": ObjectId(current_user_id)}).sort("created_at", -1)
    
    list_events = []
    for doc in events_cursor:
        list_events.append({
            "id": str(doc["_id"]),
            "user_id": str(doc["user_id"]),
            "name": doc.get("name", "-"),
            "date": doc.get("date", "-"),
            "time": doc.get("time", "-"),
            "location": doc.get("location", "-"),
            "description": doc.get("description", ""),
            "rekening": doc.get("rekening", "-"), 
            "template": doc.get("template", "template_1"), 
            "category": doc.get("category", "wedding"),     
            "rundown": doc.get("rundown", []),   
            "gallery": doc.get("gallery", [])    
        })

    return jsonify({
        "status": "success",
        "data": list_events
    }), 200