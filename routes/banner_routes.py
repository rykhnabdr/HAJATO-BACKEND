import os
import time
from flask import Blueprint, request, jsonify, redirect  # 🟢 FIX: Tambahkan redirect ke import Flask
from werkzeug.utils import secure_filename
from config.mongo import db  
from bson.objectid import ObjectId  # 🟢 FIX UTAMA: Import ObjectId dari bson agar query MongoDB tidak crash

banner_bp = Blueprint('banner_bp', __name__)

# Konfigurasi lokasi folder upload gambar (Gunakan absolute path biar aman di VPS/Laptop)
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==============================================================================
# 🟢 API CREATE BANNER BARU
# ==============================================================================
@banner_bp.route("/api/admin/banners", methods=["POST"])
def create_banner():
    try:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        banners_collection = db['banners']
        
        title = request.form.get('title')
        subtitle = request.form.get('subtitle')
        
        if not title or not subtitle:
            return jsonify({"status": "error", "message": "Judul dan subtitle wajib diisi!"}), 400
        
        if 'image_file' not in request.files:
            return jsonify({"status": "error", "message": "File gambar tidak ditemukan dalam request!"}), 400
            
        file = request.files['image_file']
        
        if file.filename == '':
            return jsonify({"status": "error", "message": "Tidak ada file yang dipilih!"}), 400
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = f"{int(time.time())}_{filename}"
            
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            
            image_url = f"/static/uploads/{filename}"
            
            new_banner = {
                "title": title.strip(),
                "subtitle": subtitle.strip(),
                "image_url": image_url, 
                "click_action": "route_to_tips",
                "is_active": True
            }
            
            result = banners_collection.insert_one(new_banner)
            
            return jsonify({
                "status": "success", 
                "message": "Banner berhasil disimpan!",
                "id": str(result.inserted_id)
            }), 201
        else:
            return jsonify({"status": "error", "message": "Format file harus JPG, JPEG, PNG, atau WEBP!"}), 400
            
    except Exception as e:
        return jsonify({"status": "error", "message": f"Backend Crash: {str(e)}"}), 500


# ==============================================================================
# 🟢 API UPDATE / EDIT STATUS BANNER (SINKRON WEB ADMIN)
# ==============================================================================
@banner_bp.route("/api/admin/banners/edit/<banner_id>", methods=["POST"])
def edit_banner_admin(banner_id):
    try:
        # 🟢 Pastikan folder upload tersedia
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        title = request.form.get('title')
        subtitle = request.form.get('subtitle')
        is_active_str = request.form.get('is_active') # 'true' atau 'false'
        
        if not title or not subtitle:
            return jsonify({"status": "error", "message": "Judul dan subtitle wajib diisi!"}), 400
            
        update_data = {
            "title": title.strip(),
            "subtitle": subtitle.strip(),
            "is_active": True if is_active_str == 'true' else False
        }
        
        # Jika admin ganti foto baru pas edit
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file and file.filename != '':
                if allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filename = f"{int(time.time())}_{filename}"
                    file.save(os.path.join(UPLOAD_FOLDER, filename))
                    update_data["image_url"] = f"/static/uploads/{filename}"
                
        db['banners'].update_one({"_id": ObjectId(banner_id)}, {"$set": update_data})
        
        return redirect("/admin/banners")
    except Exception as e:
        return jsonify({"status": "error", "message": f"Edit Gagal: {str(e)}"}), 500


# ==============================================================================
# 🟢 API ACTION DELETE BANNER HAPUS PERMANEN
# ==============================================================================
@banner_bp.route("/api/admin/banners/delete/<banner_id>", methods=["POST"])
def delete_banner_admin(banner_id):
    try:
        # Hapus dokumen banner dari MongoDB Atlas menggunakan ObjectId yang valid
        db['banners'].delete_one({"_id": ObjectId(banner_id)})
        return redirect("/admin/banners")
    except Exception as e:
        return jsonify({"status": "error", "message": f"Delete Gagal: {str(e)}"}), 500                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               d