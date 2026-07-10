import os  # WAJIB: Untuk manajemen folder upload biner foto asli
import time
from flask import request, jsonify
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
# FIX: Menambahkan url_for pada baris import Flask utama
from flask import Flask, render_template, request, redirect, session, jsonify, send_from_directory, url_for
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from bson.objectid import ObjectId
from routes.auth_routes import auth_bp
from routes.vendor_routes import vendor_bp
from routes.booking_routes import booking_bp
from config.mongo import db
from routes.payment_routes import payment_bp
from services.notification_service import send_push_notification
from services.log_service import create_activity_log
from routes.notification_routes import notification_bp
from routes.review_routes import review_bp
from datetime import datetime, timedelta
from routes.activity_log_routes import activity_log_bp
from routes.guest_routes import guest_bp
from bson import ObjectId
from routes.banner_routes import banner_bp

# ========================================================
# TAMBAHAN TAMU & ACARA: Import Blueprint Event Baru
# ========================================================
from routes.event_routes import event_bp

from config.mail_config import mail

import bcrypt
import settings
import config.firebase_config
from routes.chat_routes import chat_bp

app = Flask(__name__)
app.secret_key = "SECRET_ADMIN"

# ── 🟢 CONFIG GLOBAL: Jalur Penyimpanan Folder Upload Gambar HAJATO ───────
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Bikin folder static/uploads dan sub-folder gallery otomatis di VPS/Laptop biar ga error pas simpan file
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'gallery'), exist_ok=True)

app.config["JWT_SECRET_KEY"] = settings.JWT_SECRET_KEY
# ── 🟢 FIX TOKEN EXPIRED: Token dibikin aktif selama 30 hari biar ga bolak-balik login ──
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=30)
app.config["JWT_TOKEN_LOCATION"] = ["headers"]

# ── 🟢 KODE BARU (Memaksa tipe data int dan boolean yang benar) ───────
app.config["MAIL_SERVER"] = settings.MAIL_SERVER

# 1. Memastikan port dibaca sebagai Integer angka resmi Flask
app.config["MAIL_PORT"] = int(settings.MAIL_PORT) if settings.MAIL_PORT else 587

# 2. Memastikan TLS bernilai Boolean True jika berisi teks 'true', 'True', atau boolean True
mail_tls_env = settings.MAIL_USE_TLS
app.config["MAIL_USE_TLS"] = str(mail_tls_env).lower() in ['true', '1', 'yes']

app.config["MAIL_USERNAME"] = settings.MAIL_USERNAME
app.config["MAIL_PASSWORD"] = settings.MAIL_PASSWORD
app.config["MAIL_DEFAULT_SENDER"] = settings.MAIL_USERNAME
app.register_blueprint(notification_bp)
app.register_blueprint(review_bp)
# Registrasi route tamu
app.register_blueprint(guest_bp, url_prefix="/api/guests")

JWTManager(app)
CORS(app)

mail.init_app(app)
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(vendor_bp)
app.register_blueprint(booking_bp)
app.register_blueprint(payment_bp)
app.register_blueprint(banner_bp)

app.register_blueprint(chat_bp)

# ========================================================
# TAMBAHAN TAMU & ACARA: Daftarkan Blueprint Event API
# ========================================================
app.register_blueprint(event_bp, url_prefix="/api/events")

users = db.users

app.register_blueprint(
    activity_log_bp,
    url_prefix='/api/activity-logs'
)

@app.route("/")
def home():
    return redirect("/login")


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory("uploads", filename)


# ── 🟢 ENDPOINT BARU: Agar Browser Bisa Akses Gambar Galeri Undangan ──
@app.route("/uploads/gallery/<filename>")
def uploaded_gallery_file(filename):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], 'gallery'), filename)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = users.find_one({"email": email})

        if not user:
            return render_template("login.html", error="Email tidak ditemukan")

        valid_password = bcrypt.checkpw(
            password.encode("utf-8"),
            user["password"]
        )

        if not valid_password:
            return render_template("login.html", error="Password salah")

        if user.get("role") != "admin":
            return render_template("login.html", error="Akses hanya untuk admin")

        session["user_id"] = str(user["_id"])
        session["name"] = user["name"]
        session["role"] = user["role"]
        session["email"] = user["email"]

        # =========================
        # LOG ACTIVITY (GLOBAL)
        # =========================
        log_data = {
            "user_id": str(user["_id"]),
            "email": user["email"],
            "name": user["name"],
            "role": user["role"], 
            "action": "LOGIN",
            "timestamp": datetime.utcnow()
        }
        db.activity_logs.insert_one(log_data) 
        print(f"\n[ACTIVITY LOG] 🟢 {user['role'].upper()} {user['email']} berhasil LOGIN pada {log_data['timestamp']} UTC\n")

        return redirect("/dashboard")

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    total_vendors = db.vendor_registrations.count_documents({"status": "approved"})
    pending_approvals = db.vendor_registrations.count_documents({"status": "pending"})
    rejected_vendors = db.vendor_registrations.count_documents({"status": "rejected"})
    active_users = users.count_documents({"role": "user"})
    total_admins = users.count_documents({"role": "admin"})

    pending_data = list(db.vendor_registrations.find({"status": "pending"}).sort("_id", -1).limit(5))
    pending_vendors = []

    for vendor in pending_data:
        user_email = "-"
        if vendor.get("user_id"):
            user_data = users.find_one({"_id": ObjectId(vendor["user_id"])})
            if user_data:
                user_email = user_data.get("email", "-")

        pending_vendors.append({
            "id": str(vendor["_id"]),
            "name": vendor.get("business_name", "-"),
            "category": vendor.get("category", "-"),
            "email": user_email,
            "status": vendor.get("status", "pending")
        })

    raw_logs = list(db.activity_logs.find().sort("timestamp", -1).limit(10))
    recent_logs = []
    
    for log in raw_logs:
        waktu = log.get("timestamp")
        waktu_str = waktu.strftime("%d %b %Y, %H:%M:%S") if waktu else "-"
        recent_logs.append({
            "email": log.get("email", "-"),
            "role": log.get("role", "unknown"), 
            "action": log.get("action", "-"),
            "timestamp": waktu_str
        })

# ==========================================
# DATA GRAFIK LAYANAN TOP 5 (UNTUK GRAFIK BARU)
# ==========================================
    pipeline_chart = [
        {
            "$group": {
                "_id": "$package_name", 
                "vendor_name": {"$first": "$vendor_name"}, # 🟢 Tarik nama vendornya juga
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    top_services = list(db.bookings.aggregate(pipeline_chart))

    service_labels = []
    service_values = []
    
    for svc in top_services:
        nama_layanan = svc.get("_id")
        nama_vendor = svc.get("vendor_name", "-")
        
        if not nama_layanan:
            nama_layanan = "Lainnya"
            
        # 🟢 Format List dalam List: Membuat teks di grafik Chart.js menjadi 2 baris
        service_labels.append([nama_layanan, f"({nama_vendor})"])
        service_values.append(svc.get("count", 0))

    if not service_labels:
        service_labels = [["Belum ada pesanan", "(-)"]]
        service_values = [0]

    stats = {
        "total_vendors": total_vendors,
        "rejected_vendors": rejected_vendors,
        "pending_approvals": pending_approvals,
        "active_users": active_users
    }

    return render_template(
        "dashboard.html",
        active_page="dashboard",
        stats=stats,

        # Data untuk grafik lama (User Growth & Statistik User)
        growth_labels=["Users", "Admins", "Vendors"],
        growth_values=[active_users, total_admins, total_vendors],
        cat_labels=["Users", "Admins", "Vendors"],
        cat_values=[active_users, total_admins, total_vendors],

        # Data untuk grafik baru (Layanan)
        service_labels=service_labels,
        service_values=service_values,

        pending_vendors=pending_vendors,
        recent_logs=recent_logs  
    )

@app.route("/vendors")
def vendors():
    if "user_id" not in session:
        return redirect("/login")

    vendor_data = list(
        db.vendor_registrations.find().sort("_id", -1)
    )

    vendors = []

    for vendor in vendor_data:
        user_email = "-"

        if vendor.get("user_id"):
            user_data = users.find_one({
                "_id": ObjectId(vendor["user_id"])
            })

            if user_data:
                user_email = user_data.get("email", "-")

        vendors.append({
            "id": str(vendor["_id"]),
            "name": vendor.get("business_name", "-"),
            "category": vendor.get("category", "-"),
            "email": user_email,

            "owner_name": vendor.get("owner_name", "-"),
            "phone": vendor.get("phone", "-"),
            "location": vendor.get("location", "-"),
            "description": vendor.get("description", "-"),
            "nik": vendor.get("nik", "-"),
            "npwp": vendor.get("npwp", "-"),

            "ktp_image": vendor.get("ktp_image"),
            "selfie_image": vendor.get("selfie_image"),
            "business_license": vendor.get("business_license"),

            "rating": 5.0,
            "status": vendor.get("status", "pending").lower()
        })

    return render_template(
        "vendors.html",
        active_page="vendors",
        vendors=vendors
    )


@app.route("/users")
def users_page():
    if "user_id" not in session:
        return redirect("/login")

    all_data = list(
        users.find({
            "role": "user"
        }).sort("_id", -1)
    )

    formatted_users = []

    for user in all_data:
        formatted_users.append({
            "id": str(user["_id"])[-5:],
            "name": user.get("name", "-"),
            "email": user.get("email", "-"),
            "role": user.get("role", "user").capitalize(),
            "status": "Active",
            "phone": user.get("phone", "-")
        })

    return render_template(
        "users.html",
        active_page="users",
        all_users=formatted_users
    )

@app.route("/bookings")
def bookings_page():
    if "user_id" not in session:
        return redirect("/login")

    booking_data = list(
        db.bookings.find().sort("_id", -1)
    )

    bookings = []

    for booking in booking_data:
        bookings.append({
            "id": str(booking["_id"]),
            "user_id": booking.get("user_id", "-"),
            "vendor_name": booking.get("vendor_name", "-"),
            "package_name": booking.get("package_name", "-"),
            "event_date": booking.get("event_date", "-"),
            "event_time": booking.get("event_time", "-"),
            "location": booking.get("location", "-"),
            "payment_method": booking.get("payment_method", "-"),
            "payment_detail": booking.get("payment_detail", "-"),
            "payment_proof": booking.get("payment_proof", ""),
            "total_price": booking.get("total_price", 0),
            "booking_status": booking.get("booking_status", "-"),
            "payment_status": booking.get("payment_status", "-"),
            "vendor_payout_status": booking.get("vendor_payout_status", "-"),
        })

    return render_template(
        "bookings.html",
        active_page="bookings",
        bookings=bookings
    )

@app.route("/bookings/approve/<booking_id>", methods=["POST"])
def approve_booking(booking_id):
    if "user_id" not in session:
        return redirect("/login")

    db.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {
            "$set": {
                "booking_status": "confirmed",
                "payment_status": "paid",
                "vendor_payout_status": "hold"
            }
        }
    )

    return redirect("/bookings")


@app.route("/bookings/reject/<booking_id>", methods=["POST"])
def reject_booking(booking_id):
    if "user_id" not in session:
        return redirect("/login")

    db.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {
            "$set": {
                "booking_status": "rejected",
                "payment_status": "refund_required",
                "vendor_payout_status": "refund"
            }
        }
    )

    return redirect("/bookings")

@app.route("/uploads/payment_proofs/<filename>")
def uploaded_payment_proof(filename):
    return send_from_directory(
        "uploads/payment_proofs",
        filename
    )

@app.route("/bookings/release/<booking_id>", methods=["POST"])
def release_payout(booking_id):
    if "user_id" not in session:
        return redirect("/login")

    booking = db.bookings.find_one({
        "_id": ObjectId(booking_id)
    })

    if not booking:
        return redirect("/bookings")

    result = db.bookings.update_one(
        {
            "_id": ObjectId(booking_id),
            "booking_status": "completed",
            "vendor_payout_status": "hold"
        },
        {
            "$set": {
                "vendor_payout_status": "released"
            }
        }
    )

    if result.modified_count == 0:
        return redirect("/bookings")

    vendor = db.vendor_registrations.find_one({
        "_id": ObjectId(booking.get("vendor_id"))
    })

    if vendor:
        vendor_user = db.users.find_one({
            "_id": ObjectId(vendor.get("user_id"))
        })

        # =========================
        # CATAT LOG: PAYOUT RELEASED
        # =========================
        if vendor_user:
            create_activity_log(
                user_id=vendor.get("user_id"),
                email=vendor_user.get("email", ""),
                name=vendor_user.get("name", ""),
                role="vendor",
                action="PAYOUT_RELEASED",
                title="Dana dicairkan",
                description=f"Dana untuk booking paket {booking.get('package_name')} dari pelanggan {booking.get('customer_name')} telah dicairkan admin.",
                target_type="booking",
                target_id=booking_id,
                metadata={
                    "booking_id": booking_id,
                    "vendor_id": booking.get("vendor_id"),
                    "vendor_name": vendor.get("business_name"),
                    "customer_name": booking.get("customer_name"),
                    "package_name": booking.get("package_name"),
                    "event_date": booking.get("event_date"),
                    "event_time": booking.get("event_time"),
                    "total_price": booking.get("total_price"),
                    "vendor_payout_status": "released"
                }
            )

        if vendor_user and vendor_user.get("fcm_token"):
            send_push_notification(
                vendor_user.get("fcm_token"),
                "Dana Dicairkan",
                f"Dana untuk booking {booking.get('package_name')} telah dicairkan admin."
            )

    return redirect("/bookings")

@app.route("/vendors/approve/<vendor_id>", methods=["POST"])
def approve_vendor_web(vendor_id):
    if "user_id" not in session:
        return redirect("/login")

    vendor = db.vendor_registrations.find_one({
        "_id": ObjectId(vendor_id)
    })

    if not vendor:
        return redirect("/vendors")

    db.vendor_registrations.update_one(
        {"_id": ObjectId(vendor_id)},
        {
            "$set": {
                "status": "approved"
            }
        }
    )

    db.users.update_one(
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

    vendor_user = db.users.find_one({
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
                "approved_by_admin_id": session.get("user_id"),
                "approved_by_admin_email": session.get("email"),
                "status": "approved"
            }
        )

    return redirect("/vendors")

@app.route("/vendors/reject/<vendor_id>", methods=["POST"])
def reject_vendor_web(vendor_id):
    if "user_id" not in session:
        return redirect("/login")

    vendor = db.vendor_registrations.find_one({
        "_id": ObjectId(vendor_id)
    })

    if not vendor:
        return redirect("/vendors")

    db.vendor_registrations.update_one(
        {"_id": ObjectId(vendor_id)},
        {
            "$set": {
                "status": "rejected"
            }
        }
    )

    db.users.update_one(
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

    vendor_user = db.users.find_one({
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
                "rejected_by_admin_id": session.get("user_id"),
                "rejected_by_admin_email": session.get("email"),
                "status": "rejected"
            }
        )

    return redirect("/vendors")

@app.route("/vendors/edit/<vendor_id>", methods=["POST"])
def edit_vendor(vendor_id):
    if "user_id" not in session:
        return redirect("/login")

    name = request.form.get("name")
    category = request.form.get("category")
    status = request.form.get("status")

    vendor = db.vendor_registrations.find_one({
        "_id": ObjectId(vendor_id)
    })

    if not vendor:
        return redirect("/vendors")

    db.vendor_registrations.update_one(
        {
            "_id": ObjectId(vendor_id)
        },
        {
            "$set": {
                "business_name": name,
                "category": category,
                "status": status
            }
        }
    )

    if status == "approved":
        db.users.update_one(
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

    elif status == "rejected":
        db.users.update_one(
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

    elif status == "pending":
        db.users.update_one(
            {
                "_id": ObjectId(vendor["user_id"])
            },
            {
                "$set": {
                    "role": "vendor_pending",
                    "vendor_status": "pending"
                }
            }
        )

    return redirect("/vendors")


@app.route("/vendors/delete/<vendor_id>", methods=["POST"])
def delete_vendor(vendor_id):
    if "user_id" not in session:
        return redirect("/login")

    vendor = db.vendor_registrations.find_one({
        "_id": ObjectId(vendor_id)
    })

    if vendor and vendor.get("user_id"):
        db.users.update_one(
            {
                "_id": ObjectId(vendor["user_id"])
            },
            {
                "$set": {
                    "role": "user",
                    "vendor_status": "none"
                }
            }
        )

    db.vendor_registrations.delete_one({
        "_id": ObjectId(vendor_id)
    })

    return redirect("/vendors")


@app.route("/reports")
def reports():
    if "user_id" not in session:
        return redirect("/login")

    return render_template(
        "reports.html",
        active_page="reports"
    )


@app.route("/settings")
def settings_page():
    if "user_id" not in session:
        return redirect("/login")

    return render_template(
        "settings.html",
        active_page="settings"
    )


@app.route("/logout")
def logout():
    if "email" in session:
        log_data = {
            "user_id": session.get("user_id"),
            "email": session.get("email"),
            "name": session.get("name"),
            "role": session.get("role"), 
            "action": "LOGOUT",
            "timestamp": datetime.utcnow()
        }
        db.activity_logs.insert_one(log_data) 
        print(f"\n[ACTIVITY LOG] 🔴 {session.get('role', '').upper()} {session.get('email')} melakukan LOGOUT pada {log_data['timestamp']} UTC\n")

    session.clear()
    return redirect("/login")


@app.route("/web-login", methods=["POST"])
def web_login():
    data = request.get_json()

    email = data.get("email")
    password = data.get("password")

    user = users.find_one({"email": email})

    if not user:
        return jsonify({"message": "Email tidak ditemukan"}), 404

    valid_password = bcrypt.checkpw(
        password.encode("utf-8"),
        user["password"]
    )

    if not valid_password:
        return jsonify({"message": "Password salah"}), 401

    if user["role"] != "admin":
        return jsonify({"message": "Akses hanya untuk admin"}), 403

    session["user_id"] = str(user["_id"])
    session["name"] = user["name"]
    session["role"] = user["role"]
    session["email"] = user["email"]

    return jsonify({"message": "Login berhasil"}), 200

@app.route("/test-notification", methods=["POST"])
def test_notification():
    data = request.get_json()

    token = data.get("token")

    if not token:
        return jsonify({
            "message": "Token wajib diisi"
        }), 400

    success = send_push_notification(
        token,
        "HAJATO",
        "Ini test notifikasi dari Flask"
    )

    if success:
        return jsonify({
            "message": "Notifikasi berhasil dikirim"
        }), 200

    return jsonify({
        "message": "Notifikasi gagal dikirim"
    }), 500

@app.route("/logs")
def activity_logs_page():
    if "user_id" not in session:
        return redirect("/login")

    selected_role = request.args.get("role", "all")
    selected_category = request.args.get("category", "all")

    category_actions = {
        "akun": [
            "REGISTER",
            "VERIFY_REGISTER_OTP",
            "LOGIN",
            "LOGOUT",
            "RESET_PASSWORD",
            "UPDATE_PROFILE",
        ],
        "booking": [
            "CREATE_BOOKING",
            "CANCEL_BOOKING",
            "RECEIVE_BOOKING",
            "COMPLETE_BOOKING",
            "ACCEPT_BOOKING",
            "REJECT_BOOKING",
        ],
        "payment": [
            "CREATE_PAYMENT",
            "PAYMENT_PENDING",
            "PAYMENT_SUCCESS",
            "PAYMENT_FAILED",
        ],
        "vendor": [
            "VENDOR_REGISTER",
            "VENDOR_APPROVED",
            "VENDOR_REJECTED",
            "UPDATE_VENDOR_PROFILE",
        ],
        "paket": [
            "CREATE_PACKAGE",
            "UPDATE_PACKAGE",
            "DELETE_PACKAGE",
            "ADD_SERVICE",
            "EDIT_SERVICE",
            "DELETE_SERVICE",
        ],
        "dana": [
            "PAYOUT_RELEASED",
        ],
        "review": [
            "CREATE_REVIEW",
            "UPDATE_REVIEW",
            "DELETE_REVIEW",
            "ADD_REVIEW",
        ],
        "event": [                     
            "CREATE_EVENT",
            "UPDATE_EVENT",
            "DELETE_EVENT"
        ]
    }

    query = {}

    if selected_role == "admin":
        query["role"] = "admin"

    elif selected_role == "user":
        query["role"] = "user"

    elif selected_role == "vendor":
        query["role"] = {
            "$in": [
                "vendor",
                "vendor_pending"
            ]
        }

    if selected_category != "all":
        actions = category_actions.get(selected_category)

        if actions:
            query["action"] = {
                "$in": actions
            }

    raw_logs = list(
        db.activity_logs.find(query)
        .sort("timestamp", -1)
        .limit(150)
    )

    recent_logs = []

    for log in raw_logs:
        waktu = log.get("timestamp")

        if waktu:
            waktu_wib = waktu + timedelta(hours=7)
            waktu_str = waktu_wib.strftime("%d %b %Y, %H:%M:%S")
        else:
            waktu_str = "-"

        recent_logs.append({
            "email": log.get("email", "-"),
            "name": log.get("name", "-"),
            "role": log.get("role", "unknown"),
            "action": log.get("action", "-"),
            "title": log.get("title") or log.get("action", "-"),
            "description": log.get("description", "-"),
            "timestamp": waktu_str,
        })

    return render_template(
        "logs.html",
        active_page="logs",
        recent_logs=recent_logs,
        selected_role=selected_role,
        selected_category=selected_category
    )

# ==============================================================================
#  ROUTE MEMBUKA UNDANGAN DIGITAL (FIX CLEAN & DINAMIS MURNI ALL TEMPLATE)
# ==============================================================================
@app.route('/api/events/rsvp/<event_id>', methods=['GET'])
def render_rsvp_page(event_id):
    try:
        event_data = db.events.find_one({"_id": ObjectId(event_id)})
        if not event_data:
            return "<h1>Error 404</h1><p>Maaf, Undangan tidak ditemukan.</p>", 404
            
        # Menarik maksimal 3 komentar ucapan doa terbaru khusus untuk event_id ini
        recent_comments = list(db.comments.find({"event_id": ObjectId(event_id)})
                               .sort("created_at", -1)
                               .limit(3))
            
        # Ambil field template dari database dokumen acara (default ke template_1)
        pilihan_template = event_data.get('template', 'template_1')
        
        # Bersihkan string untuk mengambil nomor template-nya saja (misal: 'template_3' -> '3')
        nomor_template = pilihan_template.replace('template_', '')
        
        # Pengecualian khusus: template_1 dipetakan ke undangan.html sesuai struktur foldermu
        if nomor_template == '1':
            nama_file_template = "undangan.html"
        else:
            nama_file_template = f"undangan_{nomor_template}.html"
            
        print(f"\n=== 📥 [HAJATO RENDER] Template: {pilihan_template} -> File Fisik: {nama_file_template} ===")
        
        # Render otomatis secara dinamis murni tanpa if-else berderet
        return render_template(nama_file_template, event=event_data, comments=recent_comments)
            
    except Exception as e:
        return f"<h1>Terjadi Kesalahan</h1><p>{str(e)}</p>", 500


# ==============================================================================
# ROUTE: Menangani Pengiriman Form Doa Tamu Secara Asinkron (JSON)
# ==============================================================================
@app.route('/api/events/rsvp/<event_id>/comment', methods=['POST'])
def submit_comment(event_id):
    try:
        nama_tamu = request.form.get('name')
        ucapan_doa = request.form.get('message')

        if not nama_tamu or not ucapan_doa:
            return jsonify({"status": "error", "message": "Nama dan ucapan wajib diisi!"}), 400

        # Simpan objek doa tamu baru ke dalam collection 'comments' MongoDB Atlas
        db.comments.insert_one({
            "event_id": ObjectId(event_id),
            "name": nama_tamu.strip(),
            "message": ucapan_doa.strip(),
            "created_at": datetime.utcnow()
        })

        return jsonify({
            "status": "success",
            "message": "Ucapan doa berhasil disimpan!"
        }), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ==============================================================================
# ENDPOINT STATS DASHBOARD FIXED PER ACARA (SINKRON DATA VENDOR)
# ==============================================================================
@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    try:
        event_id_str = request.args.get('event_id')
        
        query_filter = {}
        nama_acara_aktif = "Aplikasi Hajato" 
        is_fallback_active = False

        # ── 1. VALIDASI & KUNCI FILTER UTAMA PER ACARA ──
        if event_id_str and event_id_str.strip() != "" and ObjectId.is_valid(event_id_str):
            query_filter = {"event_id": ObjectId(event_id_str)}
            
            try:
                event_data = db.events.find_one({"_id": ObjectId(event_id_str)})
                if event_data:
                    nama_acara_aktif = event_data.get("name") or event_data.get("title") or event_data.get("nama_acara") or "Acara Tanpa Nama"
            except Exception:
                pass

            if nama_acara_aktif == "Aplikasi Hajato":
                tamu_pertama = db.guests.find_one(query_filter)
                if tamu_pertama:
                    nama_acara_aktif = f"Acara {tamu_pertama.get('name', 'Hajato')}"
                else:
                    nama_acara_aktif = f"Acara ID: {event_id_str[:6]}..."
        else:
            # Jika memori HP bener-bener kosong/belum milih acara
            is_fallback_active = True

        # ── 2. HITUNG DATA TAMU MURNI PER ACARA (SINKRON TIDAK GLOBAL) ──
        if is_fallback_active:
            total_guest = db.guests.count_documents({})
            tamu_hadir = db.guests.count_documents({"status": "attended"})
            recent_checked_in = list(db.guests.find({"status": "attended"}).limit(3))
        else:
            # Ambil total tamu yang terdaftar di event_id ini aja
            total_guest = db.guests.count_documents(query_filter)
            # Ambil tamu hadir yang statusnya attended DAN event_id-nya cocok
            tamu_hadir_filter = {"status": "attended", "event_id": ObjectId(event_id_str)}
            tamu_hadir = db.guests.count_documents(tamu_hadir_filter)
            recent_checked_in = list(db.guests.find(tamu_hadir_filter).limit(3))

        tamu_checkin = tamu_hadir

        # ── 3. AMBIL DATA VENDOR PER ACARA (SUDAH FIX) ──
        vendors_list = []
        try:
            if not is_fallback_active:
                booking_cursor = db.bookings.find({"event_id": ObjectId(event_id_str)})
                for b in booking_cursor:
                    vendors_list.append({
                        "name": b.get("vendor_name", "Nama Vendor"),
                        "cat": b.get("package_name", "Kategori"),
                        "status": b.get("booking_status", "pending"),
                        "icon": "store"
                    })
        except Exception as e:
            print(f"[ERROR VENDOR DASHBOARD STATS]: {str(e)}")
            
        # ── 4. AMBIL DATA AKTIVITAS MURNI PER ACARA DARI COLLECTION ASLI ──
        activities_list = []
        try:
            # Ganti dari db.logs ke db.activity_logs (Sesuai collection log lo, Han)
            log_query = {} if is_fallback_active else {"metadata.event_id": event_id_str}
            activity_cursor = db.activity_logs.find(log_query).sort("timestamp", -1).limit(4)
            for a in activity_cursor:
                # Format waktu lampau simpel
                waktu = a.get("timestamp")
                waktu_str = waktu.strftime("%H:%M WIB") if waktu else "Baru saja"
                
                activities_list.append({
                    "text": a.get("description", a.get("title", "Aktivitas tercatat")),
                    "time": waktu_str
                })
        except Exception as e:
            print(f"[ERROR LOG DASHBOARD STATS]: {str(e)}")
            
        # Generasi fallback text jika log aktivitas khusus acara masih kosong
        if not activities_list:
            for rg in recent_checked_in:
                activities_list.append({
                    "text": f"{rg.get('name', 'Tamu')} berhasil check-in via QR",
                    "time": "Baru saja"
                })

        return jsonify({
            "status": "success",
            "data": {
                "event_name": nama_acara_aktif, 
                "total_guest": total_guest,
                "tamu_hadir": tamu_hadir,
                "tamu_checkin": tamu_checkin,
                "total_vendor": len(vendors_list),
                "total_booking": len(vendors_list),
                "weekly_data": [total_guest, tamu_hadir, tamu_checkin, 0, 0, 0, 0],
                "vendors": vendors_list,             
                "recent_activities": activities_list 
            }
        }), 200
    except Exception as e:
        print(f"\n[CRASH FLASK] ERROR GAES: {str(e)}\n")
        return jsonify({"status": "error", "message": str(e)}), 500
    

# ==============================================================================
# ROUTE BARU: API TOTAL LAYANAN & LAYANAN TERBANYAK (DASHBOARD ADMIN WEB)
# ==============================================================================
@app.route('/api/stats/services', methods=['GET'])
def get_service_stats_web():
    try:
        # 1. Menghitung total layanan unik dari collection bookings berdasarkan package_name
        # (Atau jika kamu punya db.packages, bisa ganti jadi db.packages.count_documents({}))
        unik_packages = db.bookings.distinct("package_name")
        total_services = len(unik_packages)
        
        # 2. Mencari paket/layanan yang paling sering di-booking
        pipeline = [
            {
                "$group": {
                    "_id": "$package_name", 
                    "totalOrders": {"$sum": 1},
                    "vendor_name": {"$first": "$vendor_name"} # Ambil nama vendor dari data booking
                }
            },
            {"$sort": {"totalOrders": -1}},
            {"$limit": 1}
        ]
        
        popular_result = list(db.bookings.aggregate(pipeline))
        
        popular_service = "Belum ada"
        popular_vendor = "-"
        
        # Jika ada transaksi booking, ambil data peringkat 1
        if popular_result and popular_result[0].get("_id"):
            popular_service = popular_result[0]["_id"]
            popular_vendor = popular_result[0].get("vendor_name", "-")
            
        return jsonify({
            "total_services": total_services,
            "popular_service": popular_service,
            "popular_vendor": popular_vendor
        }), 200
        
    except Exception as e:
        print(f"[ERROR SERVICE STATS WEB]: {str(e)}")
        return jsonify({
            "total_services": 0, 
            "popular_service": "Gagal memuat", 
            "popular_vendor": "-"
        }), 500
    

# ==============================================================================
# API YOUTUBE: VIDEO TERBARU UNTUK BERANDA USER DAN VENDOR
# ==============================================================================
@app.route("/api/youtube/latest", methods=["GET"])
def get_latest_youtube_videos():
    try:
        # Jumlah default 5 video, maksimal 10
        limit = request.args.get("limit", default=5, type=int)

        if limit is None:
            limit = 5

        limit = max(1, min(limit, 10))

        # Mengambil video terbaru dari MongoDB
        cursor = (
            db.youtube_vendor
            .find(
                {
                    "video_id": {
                        "$exists": True,
                        "$ne": ""
                    }
                },
                {
                    "_id": 0,
                    "video_id": 1,
                    "kategori": 1,
                    "categories": 1,
                    "title": 1,
                    "description": 1,
                    "channel": 1,
                    "thumbnail": 1,
                    "publish_date": 1,
                    "video_link": 1
                }
            )
            .sort("publish_date", -1)
            .limit(limit)
        )

        videos = list(cursor)

        return jsonify({
            "status": "success",
            "total": len(videos),
            "data": videos
        }), 200

    except Exception as e:
        print(f"[ERROR YOUTUBE LATEST]: {str(e)}")

        return jsonify({
            "status": "error",
            "message": "Gagal mengambil video terbaru",
            "data": []
        }), 500
    
# ==============================================================================
# API YOUTUBE: DAFTAR SEMUA VIDEO UNTUK HALAMAN INSIGHT
# ==============================================================================
@app.route("/api/youtube/videos", methods=["GET"])
def get_youtube_videos():
    try:
        kategori = request.args.get("kategori", "").strip()
        page = request.args.get("page", default=1, type=int)
        limit = request.args.get("limit", default=10, type=int)

        page = max(page or 1, 1)
        limit = max(1, min(limit or 10, 50))

        query = {
            "video_id": {
                "$exists": True,
                "$ne": ""
            }
        }

        # Filter kategori jika pengguna memilih kategori tertentu
        if kategori and kategori.lower() != "semua":
            query["categories"] = {
                "$regex": f"^{kategori}$",
                "$options": "i"
            }

        total_data = db.youtube_vendor.count_documents(query)

        videos = list(
            db.youtube_vendor
            .find(
                query,
                {
                    "_id": 0,
                    "video_id": 1,
                    "kategori": 1,
                    "categories": 1,
                    "title": 1,
                    "description": 1,
                    "channel": 1,
                    "thumbnail": 1,
                    "publish_date": 1,
                    "video_link": 1
                }
            )
            .sort("publish_date", -1)
            .skip((page - 1) * limit)
            .limit(limit)
        )

        return jsonify({
            "status": "success",
            "page": page,
            "limit": limit,
            "total_data": total_data,
            "total_pages": (total_data + limit - 1) // limit,
            "data": videos
        }), 200

    except Exception as e:
        print(f"[ERROR YOUTUBE VIDEOS]: {str(e)}")

        return jsonify({
            "status": "error",
            "message": "Gagal mengambil daftar video",
            "data": []
        }), 500
    
# ==============================================================================
# API YOUTUBE: RINGKASAN INSIGHT UNTUK DASHBOARD APLIKASI
# ==============================================================================
@app.route("/api/youtube/summary", methods=["GET"])
def get_youtube_summary():
    try:
        # Hanya menghitung dokumen yang mempunyai video_id
        video_query = {
            "video_id": {
                "$exists": True,
                "$ne": ""
            }
        }

        # Menghitung seluruh video
        total_video = db.youtube_vendor.count_documents(video_query)

# ==============================================================
# ANALISIS JUMLAH VIDEO PER KATEGORI
# ==============================================================

        pipeline_kategori = [
            {
                "$match": video_query
            },
            {
                "$set": {
                    "categories_normalized": {
                        "$cond": [
                            {"$isArray": "$categories"},
                            {
                                "$cond": [
                                    {"$gt": [{"$size": "$categories"}, 0]},
                                    "$categories",
                                    {
                                        "$cond": [
                                            {"$ne": [{"$ifNull": ["$kategori", ""]}, ""]},
                                            ["$kategori"],
                                            []
                                        ]
                                    }
                                ]
                            },
                            {
                                "$cond": [
                                    {"$ne": [{"$ifNull": ["$kategori", ""]}, ""]},
                                    ["$kategori"],
                                    []
                                ]
                            }
                        ]
                    }
                }
            },
            {"$unwind": "$categories_normalized"},
            {
                "$match": {
                    "categories_normalized": {
                        "$nin": ["", None]
                    }
                }
            },
            {
                "$group": {
                    "_id": "$categories_normalized",
                    "jumlah": {"$sum": 1}
                }
            },
            {"$sort": {"jumlah": -1, "_id": 1}}
        ]

        hasil_kategori = list(db.youtube_vendor.aggregate(pipeline_kategori))

        category_stats = []

        for item in hasil_kategori:
            category_stats.append({
                "kategori": item.get("_id", "Tidak diketahui"),
                "jumlah": item.get("jumlah", 0)
            })

# ==============================================================
# ANALISIS TREND MODEL HAJATAN
#
# Menghitung kemunculan kata kunci model / tema hajatan
# berdasarkan clean_title dan clean_description
# ==============================================================

        trend_keywords = [
            {
                "model": "modern",
                "keywords": ["modern"]
            },
            {
                "model": "mewah",
                "keywords": ["mewah", "luxury", "glamour", "glamor"]
            },
            {
                "model": "elegan",
                "keywords": ["elegan", "elegant"]
            },
            {
                "model": "minimalis",
                "keywords": ["minimalis", "minimalist"]
            },
            {
                "model": "sederhana",
                "keywords": ["sederhana", "simple", "simpel"]
            },
            {
                "model": "outdoor",
                "keywords": ["outdoor", "luar ruangan"]
            },
            {
                "model": "indoor",
                "keywords": ["indoor", "dalam ruangan"]
            },
            {
                "model": "garden",
                "keywords": ["garden", "taman"]
            },
            {
                "model": "tradisional",
                "keywords": ["tradisional", "adat", "jawa", "sunda"]
            },
            {
                "model": "pelaminan",
                "keywords": ["pelaminan"]
            },
            {
                "model": "dekorasi",
                "keywords": ["dekorasi", "decoration", "decor"]
            },
            {
                "model": "catering",
                "keywords": ["catering", "katering"]
            }
        ]

        trend_counter = {}

        for trend in trend_keywords:
            trend_counter[trend["model"]] = 0

        video_cursor = db.youtube_vendor.find(
            video_query,
            {
                "_id": 0,
                "title": 1,
                "description": 1,
                "clean_title": 1,
                "clean_description": 1
            }
        )

        for video in video_cursor:
            clean_title = video.get("clean_title", "")
            clean_description = video.get("clean_description", "")

            # Fallback jika data lama belum punya clean_title / clean_description
            if not clean_title:
                clean_title = video.get("title", "")

            if not clean_description:
                clean_description = video.get("description", "")

            combined_text = f"{clean_title} {clean_description}".lower()

            for trend in trend_keywords:
                model = trend["model"]
                keywords = trend["keywords"]

                # Satu video dihitung satu kali untuk satu model
                if any(keyword in combined_text for keyword in keywords):
                    trend_counter[model] += 1

        trend_stats = []

        for model, jumlah in trend_counter.items():
            if jumlah > 0:
                trend_stats.append({
                    "model": model,
                    "jumlah": jumlah
                })

        trend_stats = sorted(
            trend_stats,
            key=lambda item: item["jumlah"],
            reverse=True
        )

        # Ambil maksimal 8 trend teratas agar grafik tidak terlalu panjang
        trend_stats = trend_stats[:8]

        # ==============================================================
        # LAST UPDATE
        # ==============================================================

        latest_document = db.youtube_vendor.find_one(
            {
                "video_id": {"$exists": True, "$ne": ""},
                "last_collected_at": {"$exists": True, "$ne": None}
            },
            {"_id": 0, "last_collected_at": 1},
            sort=[("last_collected_at", -1)]
        )

        last_update = None

        if latest_document:
            waktu = latest_document.get("last_collected_at")

            if waktu:
                last_update = waktu.isoformat()

        total_data_kategori = sum(
            item["jumlah"] for item in category_stats
        )

        return jsonify({
            "status": "success",
            "data": {
                "total_video": total_video,
                "total_kategori": len(category_stats),
                "total_data_kategori": total_data_kategori,
                "last_update": last_update,
                "category_stats": category_stats,
                "trend_stats": trend_stats
            }
        }), 200

    except Exception as e:
        print(f"[ERROR YOUTUBE SUMMARY]: {str(e)}")

        return jsonify({
            "status": "error",
            "message": "Gagal mengambil ringkasan insight",
            "data": {
                "total_video": 0,
                "total_kategori": 0,
                "total_data_kategori": 0,
                "last_update": None,
                "category_stats": [],
                "trend_stats": []
            }
        }), 500
# ==============================================================================
# HALAMAN WEB ADMIN BANNER (SINKRON DATA LIST UNTUK FORM EDIT & HAPUS)
# ==============================================================================
@app.route('/admin/banners')
def banners_page():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
        
    try:
        # Ambil semua data banner dari MongoDB (di-sort dari yang terbaru)
        banners_cursor = db['banners'].find().sort("_id", -1)
        
        all_banners = []
        for b in banners_cursor:
            all_banners.append({
                "id": str(b["_id"]),
                "title": b.get("title", "-"),
                "subtitle": b.get("subtitle", "-"),
                "image_url": b.get("image_url", ""),
                "is_active": b.get("is_active", True)
            })
            
        # Kirim data 'all_banners' ke dalam file HTML lo
        return render_template('banners.html', active_page='banners', banners=all_banners)
    except Exception as e:
        print(f"[ERROR ADMIN BANNERS PAGE]: {str(e)}")
        return render_template('banners.html', active_page='banners', banners=[], error=str(e))


# ==============================================================================
# 🟢 ENDPOINT GET BANNER AKTIF (LANGSUNG DI APP.PY UNTUK AKURASI FLUTTER)
# ==============================================================================
@app.route("/api/banners/active", methods=["GET"])
def get_active_banners_direct():
    try:
        banners_collection = db['banners']
        cursor = banners_collection.find({"is_active": True})
        
        banners_list = []
        for banner in cursor:
            banners_list.append({
                "title": banner.get("title", "Info Spesial"),
                "subtitle": banner.get("subtitle", ""),
                "image_url": banner.get("image_url", ""),
                "click_action": banner.get("click_action", "route_to_tips")
            })
        
        return jsonify({
            "status": "success",
            "data": banners_list
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )