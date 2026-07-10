import os
from werkzeug.utils import secure_filename
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId
from services.log_service import create_activity_log

from flask import Blueprint, request, jsonify
from config.mongo import db

from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity
)

from middleware.role_middleware import role_required

import bcrypt
import random
from datetime import datetime, timedelta
from flask_mail import Message
from config.mail_config import mail

from google.oauth2 import id_token
from google.auth.transport import requests

from services.face_service import generate_embedding_from_file, cosine_similarity

auth_bp = Blueprint('auth', __name__)

users = db.users
vendor_registrations = db.vendor_registrations
otp_collection = db.otp_codes
face_embeddings = db.face_embeddings

FACE_LOGIN_THRESHOLD = 0.50
FACE_LOGIN_MARGIN = 0.05

# =========================
# OTP HELPER
# =========================
def generate_and_save_otp(email, purpose):
    otp = str(random.randint(100000, 999999))
    expires_at = datetime.utcnow() + timedelta(minutes=5)

    otp_collection.delete_many({
        "email": email,
        "purpose": purpose
    })

    otp_collection.insert_one({
        "email": email,
        "otp": otp,
        "purpose": purpose,
        "expires_at": expires_at,
        "verified": False
    })

    return otp


def send_otp_email(email, name, otp, purpose):
    if purpose == "register":
        subject = "Kode OTP Verifikasi Akun HAJATO"
        title = "Verifikasi Akun HAJATO"
        subtitle = "Gunakan kode OTP berikut untuk menyelesaikan proses pendaftaran akun Anda."
        badge_text = "VERIFIKASI AKUN"
    else:
        subject = "Kode OTP Reset Password HAJATO"
        title = "Reset Password HAJATO"
        subtitle = "Gunakan kode OTP berikut untuk melanjutkan proses reset password akun Anda."
        badge_text = "RESET PASSWORD"

    plain_body = f"""
Halo {name},

{subtitle}

Kode OTP Anda adalah:

{otp}

Kode ini berlaku selama 5 menit.
Jangan bagikan kode ini kepada siapa pun.

Terima kasih,
HAJATO
"""

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>{subject}</title>
</head>
<body style="margin:0; padding:0; background-color:#F4F7F7; font-family:Arial, Helvetica, sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#F4F7F7; padding:32px 0;">
    <tr>
      <td align="center">
        <table width="100%" cellpadding="0" cellspacing="0" style="max-width:560px; background-color:#ffffff; border-radius:20px; overflow:hidden; box-shadow:0 10px 30px rgba(0,0,0,0.08);">
          
          <tr>
            <td style="background:linear-gradient(135deg,#00796B,#26A69A); padding:32px 28px; text-align:center;">
              <div style="margin-bottom: 12px;">
                <img src="https://i.ibb.co.com/qL3wHLwT/hajatonew.png" alt="HAJATO Logo" width="65" height="65" style="border-radius: 16px; object-fit: cover; border: 2px solid rgba(255,255,255,0.4); display: inline-block;" />
              </div>
              <h1 style="margin:0; color:#ffffff; font-size:26px; letter-spacing:1.5px; font-family: 'Playfair Display', Georgia, serif; font-weight: 900;">HAJATO</h1>
              <p style="margin:6px 0 0; color:#E0F2F1; font-size:14px;">Solusi digital untuk kebutuhan hajatan Anda</p>
            </td>
          </tr>

          <tr>
            <td style="padding:32px 28px 8px;">
              <div style="display:inline-block; background-color:#E0F2F1; color:#00796B; padding:7px 12px; border-radius:999px; font-size:11px; font-weight:bold; letter-spacing:0.6px;">
                {badge_text}
              </div>

              <h2 style="margin:20px 0 10px; color:#1F2937; font-size:23px;">
                Halo, {name}
              </h2>

              <p style="margin:0; color:#4B5563; font-size:15px; line-height:1.7;">
                {subtitle}
              </p>
            </td>
          </tr>

          <tr>
            <td align="center" style="padding:26px 28px;">
              <div style="background-color:#F9FAFB; border:1px dashed #26A69A; border-radius:18px; padding:24px 20px;">
                <p style="margin:0 0 10px; color:#6B7280; font-size:13px; font-weight:bold; letter-spacing:0.8px;">
                  KODE OTP ANDA
                </p>

                <div style="font-size:38px; font-weight:bold; letter-spacing:10px; color:#00796B; margin:8px 0;">
                  {otp}
                </div>

                <p style="margin:12px 0 0; color:#EF4444; font-size:13px;">
                  Kode ini berlaku selama 5 menit.
                </p>
              </div>
            </td>
          </tr>

          <tr>
            <td style="padding:0 28px 28px;">
              <div style="background-color:#FFF7ED; border-left:4px solid #F59E0B; padding:14px 16px; border-radius:12px;">
                <p style="margin:0; color:#92400E; font-size:13px; line-height:1.6;">
                  Jangan bagikan kode ini kepada siapa pun, termasuk pihak yang mengatasnamakan HAJATO.
                </p>
              </div>
            </td>
          </tr>

          <tr>
            <td style="padding:24px 28px; background-color:#F9FAFB; text-align:center; border-top:1px solid #E5E7EB;">
              <p style="margin:0; color:#6B7280; font-size:12px; line-height:1.6;">
                Email ini dikirim otomatis oleh sistem HAJATO.<br>
                Jika Anda tidak merasa melakukan permintaan ini, abaikan email ini.
              </p>
              <p style="margin:14px 0 0; color:#00796B; font-size:13px; font-weight:bold;">
                Terima kasih,<br>HAJATO
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

   # ── 🟢 GANTI KODE PALING BAWAHNYA MENJADI SEPERTI INI ───────
    msg = Message(
        subject=subject,
        sender=("HAJATO", "hajato.app@gmail.com"),
        recipients=[email],
        body=plain_body,
        html=html_body
    )

    # Membungkus pengiriman dengan try-except agar jika SMTP cloud timeout, Flask TIDAK gantung
    try:
        mail.send(msg)
        print(f"[MAIL SUCCESS] ✉️ OTP asli berhasil dikirim ke {email}")
    except Exception as mail_error:
        print(f"\n[MAIL CRASH WARNING] ⚠️ Gagal kirim email asli tapi alur diselamatkan: {str(mail_error)}\n")
        # Kode tetap jalan terus tanpa membuat loading Flutter lo muter-muter selamanya


# =========================
# UPLOAD FOLDER
# =========================
UPLOAD_FOLDER = "uploads"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# =========================
# REGISTER
# =========================
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
        "bio": "",
        "is_verified": False,
        "login_provider": "local",
        "created_at": datetime.utcnow()
    }

    result = users.insert_one(user_data)

    # =========================
    # KIRIM OTP REGISTER
    # =========================
    otp = generate_and_save_otp(
        email=email,
        purpose="register"
    )

    send_otp_email(
        email=email,
        name=name,
        otp=otp,
        purpose="register"
    )

    # =========================
    # CATAT LOG: REGISTER
    # =========================
    create_activity_log(
        user_id=result.inserted_id,
        email=email,
        name=name,
        role="user",
        action="REGISTER"
    )

    print(f"[REGISTER] User {email} berhasil register dan OTP dikirim")

    return jsonify({
        "message": "Register berhasil. Kode OTP telah dikirim ke email",
        "email": email
    }), 201


# =========================
# REGISTER WITH FACE
# =========================
@auth_bp.route('/register-with-face', methods=['POST'])
def register_with_face():

    name = request.form.get("name")
    email = request.form.get("email")
    phone = request.form.get("phone")
    password = request.form.get("password")

    # Untuk keamanan, role register biasa tetap user
    role = "user"

    if not name or not email or not phone or not password:
        return jsonify({
            "message": "Nama, email, nomor HP, dan password wajib diisi"
        }), 400

    existing_user = users.find_one({
        "email": email
    })

    if existing_user:
        return jsonify({
            "message": "Email sudah digunakan"
        }), 400

    # Support multipart: face_images[]
    face_images = request.files.getlist("face_images")

    # Support juga format: face_image_1, face_image_2, face_image_3
    if not face_images:
        for i in range(1, 6):
            file = request.files.get(f"face_image_{i}")
            if file and file.filename != "":
                face_images.append(file)

    if len(face_images) < 3:
        return jsonify({
            "message": "Minimal 3 foto wajah wajib dikirim"
        }), 400

    pose_types = request.form.getlist("pose_types")

    embedding_docs = []

    try:
        for index, face_file in enumerate(face_images):

            if not face_file or face_file.filename == "":
                return jsonify({
                    "message": f"Foto wajah ke-{index + 1} tidak valid"
                }), 400

            embedding = generate_embedding_from_file(face_file)

            pose_type = "unknown"

            if index < len(pose_types):
                pose_type = pose_types[index]
            else:
                pose_type = request.form.get(
                    f"pose_type_{index + 1}",
                    f"pose_{index + 1}"
                )

            embedding_docs.append({
                "pose_type": pose_type,
                "embedding": embedding,
                "created_at": datetime.utcnow()
            })

    except ValueError as e:
        return jsonify({
            "message": str(e)
        }), 400

    except Exception as e:
        print("REGISTER FACE ERROR:", e)
        return jsonify({
            "message": "Gagal memproses wajah"
        }), 500

    hashed_password = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    )

    user_data = {
        "name": name,
        "email": email,
        "phone": phone,
        "password": hashed_password,
        "role": role,
        "vendor_status": None,
        "bio": "",
        "is_verified": False,
        "login_provider": "local",
        "face_registered": True,
        "face_embedding_count": len(embedding_docs),
        "created_at": datetime.utcnow()
    }

    try:
        result = users.insert_one(user_data)
        user_id = str(result.inserted_id)

        for doc in embedding_docs:
            doc["user_id"] = user_id

        face_embeddings.insert_many(embedding_docs)

        otp = generate_and_save_otp(
            email=email,
            purpose="register"
        )

        send_otp_email(
            email=email,
            name=name,
            otp=otp,
            purpose="register"
        )

        create_activity_log(
            user_id=result.inserted_id,
            email=email,
            name=name,
            role=role,
            action="REGISTER_WITH_FACE"
        )

        return jsonify({
            "message": "Register berhasil. Kode OTP telah dikirim ke email",
            "email": email,
            "face_registered": True,
            "face_embedding_count": len(embedding_docs)
        }), 201

    except Exception as e:
        print("REGISTER WITH FACE DB ERROR:", e)

        if "result" in locals():
            users.delete_one({
                "_id": result.inserted_id
            })

            face_embeddings.delete_many({
                "user_id": str(result.inserted_id)
            })

        return jsonify({
            "message": "Register gagal"
        }), 500


# =========================
# LOGIN (FIXED: MENGIRIM EVENT_ID DAN PHOTO_URL TERAKHIR USER)
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

    stored_password = user.get("password", "")

    if not stored_password:
        return jsonify({
            "message": "Akun ini belum memiliki password"
        }), 400

    if isinstance(stored_password, bytes):
        stored_password_bytes = stored_password
    else:
        stored_password_bytes = stored_password.encode("utf-8")

    valid_password = bcrypt.checkpw(
        password.encode("utf-8"),
        stored_password_bytes
    )

    if not valid_password:
        return jsonify({
            "message": "Password salah"
        }), 401
    
# =========================
# CEK VERIFIKASI EMAIL
# =========================
    if user.get("login_provider", "local") == "local" and user.get("is_verified") is False:
        return jsonify({
        "message": "Akun belum diverifikasi. Silakan cek email dan masukkan kode OTP terlebih dahulu"
    }), 403


    business_name = ""

    if user.get("role") in ["vendor", "vendor_pending"]:
        vendor = vendor_registrations.find_one({
            "user_id": str(user["_id"])
        })

        if vendor:
            business_name = vendor.get("business_name", "")

    token = create_access_token(
        identity=str(user["_id"])
    )
    # =========================
    # CATAT LOG: LOGIN (API)
    # =========================
    create_activity_log(
        user_id=user["_id"],
        email=user["email"],
        name=user["name"],
        role=user.get("role", "user"),
        action="LOGIN"
    )

    # CARI ACARA TERBARU MILIK USER AGAR MENU DASHBOARD DI FLUTTER MUNCUL
    event_id_str = ""
    last_event = db.events.find_one({"user_id": str(user["_id"])}, sort=[("_id", -1)])
    if last_event:
        event_id_str = str(last_event["_id"])

    print(f"[LOGIN] User {email} berhasil login. Event ID Terdeteksi: {event_id_str}")

    return jsonify({
        "message": "Login berhasil",
        "token": token,
        "user_id": str(user["_id"]),
        "role": user["role"],
        "vendor_status": user.get("vendor_status"),
        "name": user["name"],
        "email": user["email"],
        "phone": user.get("phone", ""),
        "business_name": business_name,
        "event_id": event_id_str,
        "photo_url": user.get("photo_url", "")  # ── 🟢 FIX: Dikirim ke Flutter biar langsung ke-save pas login
    }), 200

# =========================
# FORGOT PASSWORD - SEND OTP
# =========================
@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():

    data = request.get_json()

    email = data.get("email")

    if not email:
        return jsonify({
            "message": "Email wajib diisi"
        }), 400

    user = users.find_one({
        "email": email
    })

    if not user:
        return jsonify({
            "message": "Email tidak terdaftar"
        }), 404

    otp = generate_and_save_otp(
        email=email,
        purpose="reset_password"
    )

    send_otp_email(
        email=email,
        name=user.get("name", "Pengguna"),
        otp=otp,
        purpose="reset_password"
    )

    print(f"[OTP] Kode OTP dikirim ke {email}")

    return jsonify({
        "message": "Kode OTP telah dikirim ke email"
    }), 200


# =========================
# VERIFY OTP RESET PASSWORD
# =========================
@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():

    data = request.get_json()

    email = data.get("email")
    otp = data.get("otp")

    if not email or not otp:
        return jsonify({
            "message": "Email dan OTP wajib diisi"
        }), 400

    otp_data = otp_collection.find_one({
        "email": email,
        "otp": otp,
        "purpose": "reset_password"
    })

    if not otp_data:
        return jsonify({
            "message": "OTP tidak valid"
        }), 400

    if datetime.utcnow() > otp_data["expires_at"]:
        return jsonify({
            "message": "OTP sudah kadaluarsa"
        }), 400

    otp_collection.update_one(
        {
            "_id": otp_data["_id"]
        },
        {
            "$set": {
                "verified": True
            }
        }
    )

    return jsonify({
        "message": "OTP berhasil diverifikasi"
    }), 200


# =========================
# VERIFY REGISTER OTP
# =========================
@auth_bp.route('/verify-register-otp', methods=['POST'])
def verify_register_otp():

    data = request.get_json()

    email = data.get("email")
    otp = data.get("otp")

    if not email or not otp:
        return jsonify({
            "message": "Email dan OTP wajib diisi"
        }), 400

    otp_data = otp_collection.find_one({
        "email": email,
        "otp": otp,
        "purpose": "register"
    })

    if not otp_data:
        return jsonify({
            "message": "OTP tidak valid"
        }), 400

    if datetime.utcnow() > otp_data["expires_at"]:
        return jsonify({
            "message": "OTP sudah kadaluarsa"
        }), 400

    user = users.find_one({
        "email": email
    })

    if not user:
        return jsonify({
            "message": "User tidak ditemukan"
        }), 404

    users.update_one(
        {
            "email": email
        },
        {
            "$set": {
                "is_verified": True
            }
        }
    )

    otp_collection.delete_many({
        "email": email,
        "purpose": "register"
    })

    # =========================
    # CATAT LOG: VERIFY REGISTER OTP
    # =========================
    create_activity_log(
        user_id=user["_id"],
        email=email,
        name=user.get("name", "Unknown"),
        role=user.get("role", "user"),
        action="VERIFY_REGISTER_OTP"
    )

    print(f"[VERIFY REGISTER OTP] Akun {email} berhasil diverifikasi")

    return jsonify({
        "message": "Akun berhasil diverifikasi. Silakan login"
    }), 200


# =========================
# RESET PASSWORD
# =========================
@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():

    data = request.get_json()

    email = data.get("email")
    otp = data.get("otp")
    new_password = data.get("new_password")

    if not email or not otp or not new_password:
        return jsonify({
            "message": "Semua field wajib diisi"
        }), 400

    otp_data = otp_collection.find_one({
        "email": email,
        "otp": otp,
        "purpose": "reset_password",
        "verified": True
    })

    if not otp_data:
        return jsonify({
            "message": "OTP belum diverifikasi"
        }), 400

    if datetime.utcnow() > otp_data["expires_at"]:
        return jsonify({
            "message": "OTP sudah kadaluarsa"
        }), 400

    hashed_password = bcrypt.hashpw(
        new_password.encode("utf-8"),
        bcrypt.gensalt()
    )

    users.update_one(
        {
            "email": email
        },
        {
            "$set": {
                "password": hashed_password
            }
        }
    )

    otp_collection.delete_many({
        "email": email,
        "purpose": "reset_password"
    })

    # =========================
    # CATAT LOG: RESET PASSWORD
    # =========================
    updated_user = users.find_one({"email": email})
    if updated_user:
        create_activity_log(
            user_id=updated_user["_id"],
            email=email,
            name=updated_user.get("name", "Unknown"),
            role=updated_user.get("role", "user"),
            action="RESET_PASSWORD"
        )

    print(f"[RESET PASSWORD] Password berhasil diubah untuk {email}")

    return jsonify({
        "message": "Password berhasil direset"
    }), 200


# =========================
# LOGIN FACE IDENTIFICATION 1:N
# =========================
@auth_bp.route('/login-face-identify', methods=['POST'])
def login_face_identify():

    face_image = request.files.get("face_image")

    if not face_image:
        face_image = request.files.get("image")

    if not face_image or face_image.filename == "":
        return jsonify({
            "message": "Foto wajah wajib dikirim"
        }), 400

    try:
        login_embedding = generate_embedding_from_file(face_image)

    except ValueError as e:
        return jsonify({
            "message": str(e)
        }), 400

    except Exception as e:
        print("LOGIN FACE PROCESS ERROR:", e)
        return jsonify({
            "message": "Gagal memproses wajah"
        }), 500

    all_embeddings = list(face_embeddings.find({}))

    if not all_embeddings:
        return jsonify({
            "message": "Belum ada data wajah terdaftar"
        }), 404

    best_by_user = {}

    for item in all_embeddings:
        user_id = item.get("user_id")
        stored_embedding = item.get("embedding")

        if not user_id or not stored_embedding:
            continue

        similarity = cosine_similarity(
            login_embedding,
            stored_embedding
        )

        if user_id not in best_by_user:
            best_by_user[user_id] = {
                "user_id": user_id,
                "similarity": similarity,
                "pose_type": item.get("pose_type", "unknown")
            }

        elif similarity > best_by_user[user_id]["similarity"]:
            best_by_user[user_id] = {
                "user_id": user_id,
                "similarity": similarity,
                "pose_type": item.get("pose_type", "unknown")
            }

    ranked_users = sorted(
        best_by_user.values(),
        key=lambda x: x["similarity"],
        reverse=True
    )

    if not ranked_users:
        return jsonify({
            "message": "Data wajah tidak valid"
        }), 400

    best_match = ranked_users[0]
    best_score = best_match["similarity"]

    second_score = 0.0

    if len(ranked_users) > 1:
        second_score = ranked_users[1]["similarity"]

    if best_score < FACE_LOGIN_THRESHOLD:
        return jsonify({
            "message": "Wajah tidak cocok dengan akun mana pun",
            "similarity": round(best_score, 4),
            "threshold": FACE_LOGIN_THRESHOLD
        }), 401

    if len(ranked_users) > 1 and (best_score - second_score) < FACE_LOGIN_MARGIN:
        return jsonify({
            "message": "Wajah belum dapat dipastikan. Silakan coba lagi atau login manual",
            "similarity": round(best_score, 4),
            "second_similarity": round(second_score, 4)
        }), 401

    try:
        matched_user_id = best_match["user_id"]

        user = users.find_one({
            "_id": ObjectId(matched_user_id)
        })

    except Exception:
        return jsonify({
            "message": "User hasil pencocokan tidak valid"
        }), 500

    if not user:
        return jsonify({
            "message": "User tidak ditemukan"
        }), 404

    if user.get("login_provider", "local") == "local" and user.get("is_verified") is False:
        return jsonify({
            "message": "Akun belum diverifikasi. Silakan verifikasi OTP terlebih dahulu"
        }), 403

    business_name = ""

    if user.get("role") in ["vendor", "vendor_pending"]:
        vendor = vendor_registrations.find_one({
            "user_id": str(user["_id"])
        })

        if vendor:
            business_name = vendor.get("business_name", "")

    token = create_access_token(
        identity=str(user["_id"])
    )

    create_activity_log(
        user_id=user["_id"],
        email=user["email"],
        name=user["name"],
        role=user.get("role", "user"),
        action="LOGIN_FACE"
    )

    event_id_str = ""
    last_event = db.events.find_one(
        {"user_id": str(user["_id"])},
        sort=[("_id", -1)]
    )

    if last_event:
        event_id_str = str(last_event["_id"])

    return jsonify({
        "message": "Login wajah berhasil",
        "token": token,
        "user_id": str(user["_id"]),
        "role": user["role"],
        "vendor_status": user.get("vendor_status"),
        "name": user["name"],
        "email": user["email"],
        "phone": user.get("phone", ""),
        "business_name": business_name,
        "event_id": event_id_str,
        "photo_url": user.get("photo_url", ""),
        "similarity": round(best_score, 4),
        "second_similarity": round(second_score, 4),
        "matched_pose": best_match.get("pose_type", "unknown")
    }), 200


# =========================
# GOOGLE LOGIN (FIXED: SEKARANG MENGIRIM EVENT_ID TERAKHIR USER)
# =========================
@auth_bp.route('/google-login', methods=['POST'])
def google_login():

    data = request.get_json()

    google_token = data.get("idToken")

    if not google_token:
        return jsonify({
            "message": "Google token wajib diisi"
        }), 400

    try:
        idinfo = id_token.verify_oauth2_token(
            google_token,
            requests.Request()
        )

        email = idinfo.get("email")
        name = idinfo.get("name", "")
        picture = idinfo.get("picture", "")

        if not email:
            return jsonify({
                "message": "Email Google tidak ditemukan"
            }), 400

        user = users.find_one({
            "email": email
        })

        # =========================
        # AUTO REGISTER GOOGLE USER
        # =========================
        if not user:
            user_data = {
                "name": name,
                "email": email,
                "phone": "",
                "password": "",
                "role": "user",
                "vendor_status": None,
                "bio": "",
                "photo_url": picture,
                "login_provider": "google"
            }

            result = users.insert_one(user_data)
            user_id = str(result.inserted_id)

            user = users.find_one({
                "_id": ObjectId(user_id)
            })

        else:
            users.update_one(
                {
                    "_id": user["_id"]
                },
                {
                    "$set": {
                        "photo_url": picture,
                        "login_provider": "google"
                    }
                }
            )

            user = users.find_one({
                "_id": user["_id"]
            })

        business_name = ""

        if user.get("role") in ["vendor", "vendor_pending"]:
            vendor = vendor_registrations.find_one({
                "user_id": str(user["_id"])
            })

            if vendor:
                business_name = vendor.get("business_name", "")

        token = create_access_token(
            identity=str(user["_id"])
        )
        # =========================
        # CATAT LOG: GOOGLE LOGIN
        # =========================
        create_activity_log(
            user_id=user["_id"],
            email=user["email"],
            name=user["name"],
            role=user.get("role", "user"),
            action="LOGIN"
        )

        # CARI ACARA TERBARU MILIK GOOGLE USER AGAR MENU DASHBOARD DI FLUTTER MUNCUL
        event_id_str = ""
        last_event = db.events.find_one({"user_id": str(user["_id"])}, sort=[("_id", -1)])
        if last_event:
            event_id_str = str(last_event["_id"])

        print(f"[GOOGLE LOGIN] User {email} berhasil login. Event ID Terdeteksi: {event_id_str}")

        return jsonify({
            "message": "Google login berhasil",
            "token": token,
            "role": user["role"],
            "vendor_status": user.get("vendor_status"),
            "name": user["name"],
            "email": user["email"],
            "phone": user.get("phone", ""),
            "business_name": business_name,
            "photo_url": user.get("photo_url", ""),
            "event_id": event_id_str  
        }), 200

    except Exception as e:
        print("GOOGLE LOGIN ERROR :", e)

        return jsonify({
            "message": "Google token tidak valid"
        }), 401        

# =========================
# PROFILE (MODIFIED FOR PHOTO_URL)
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
            "vendor_status": user.get("vendor_status"),
            "photo_url": user.get("photo_url", "") 
        }
    }), 200

# =========================
# UPDATE PROFILE (MODIFIED FOR MULTIPART AVATAR)
# =========================
@auth_bp.route('/update-profile', methods=['PUT'])
@jwt_required()
def update_profile():

    current_user_id = get_jwt_identity()

    name = request.form.get("name")
    phone = request.form.get("phone")
    bio = request.form.get("bio")

    if not name:
        return jsonify({
            "message": "Nama wajib diisi"
        }), 400

    update_data = {
        "name": name,
        "phone": phone,
        "bio": bio,
        "updated_at": datetime.utcnow()
    }

    avatar_image = request.files.get("avatar")
    
    if avatar_image and avatar_image.filename != '':
        file_extension = os.path.splitext(avatar_image.filename)[1]
        filename = secure_filename(f"avatar_{current_user_id}{file_extension}")
        
        avatar_image.save(os.path.join(UPLOAD_FOLDER, filename))
        
        photo_url = f"{request.url_root}uploads/{filename}"
        update_data["photo_url"] = photo_url

    result = users.update_one(
        {
            "_id": ObjectId(current_user_id)
        },
        {
            "$set": update_data
        }
    )

    print("UPDATE PROFILE HIT (MULTIPART)")
    print("USER ID:", current_user_id)
    print("MATCHED:", result.matched_count)
    print("MODIFIED:", result.modified_count)

    updated_user = users.find_one({
        "_id": ObjectId(current_user_id)
    })

    if updated_user:
        create_activity_log(
            user_id=current_user_id,
            email=updated_user.get("email"),
            name=updated_user.get("name"),
            role=updated_user.get("role", "user"),
            action="UPDATE_PROFILE"
        )

    return jsonify({
        "message": "Profil berhasil diperbarui",
        "data": {
            "name": updated_user.get("name", ""),
            "email": updated_user.get("email", ""),
            "phone": updated_user.get("phone", ""),
            "bio": updated_user.get("bio", ""),
            "photo_url": updated_user.get("photo_url", "") 
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
# =========================
@auth_bp.route('/register-vendor', methods=['POST'])
def register_vendor_direct():

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

    ktp_image = request.files.get("ktp_image")
    selfie_image = request.files.get("selfie_image")
    business_license = request.files.get("business_license")

    print("========== DIRECT REGISTER VENDOR ==========")
    print("NAME :", name)
    print("EMAIL :", email)
    print("BUSINESS NAME :", business_name)
    print("CATEGORY :", category)

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

    hashed_password = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    )

    user_data = {
        "name": name,
        "email": email,
        "phone": phone,
        "password": hashed_password,
        "role": "vendor_pending",
        "vendor_status": "pending",
        "bio": "",
        "is_verified": False,
        "login_provider": "local",
        "created_at": datetime.utcnow()
    }

    result = users.insert_one(user_data)
    user_id = str(result.inserted_id)

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

    otp = generate_and_save_otp(
        email=email,
        purpose="register"
    )

    send_otp_email(
        email=email,
        name=name,
        otp=otp,
        purpose="register"
    )

    create_activity_log(
        user_id=user_id,
        email=email,
        name=name,
        role="vendor_pending",
        action="VENDOR_REGISTER"
    )

    return jsonify({
        "message": "Pendaftaran vendor berhasil",
        "role": "vendor_pending",
        "vendor_status": "pending",
        "name": name,
        "email": email
    }), 201


# =========================
# REGISTER VENDOR WITH FACE
# =========================
@auth_bp.route('/register-vendor-with-face', methods=['POST'])
def register_vendor_with_face():

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

    ktp_image = request.files.get("ktp_image")
    selfie_image = request.files.get("selfie_image")
    business_license = request.files.get("business_license")

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
    # AMBIL FOTO WAJAH
    # =========================
    face_images = request.files.getlist("face_images")

    if not face_images:
        face_images = request.files.getlist("face_images[]")

    if not face_images:
        for i in range(1, 6):
            file = request.files.get(f"face_image_{i}")
            if file and file.filename != "":
                face_images.append(file)

    face_images = [
        file for file in face_images
        if file and file.filename != ""
    ]

    if len(face_images) < 3:
        return jsonify({
            "message": "Minimal 3 foto wajah wajib dikirim"
        }), 400

    pose_types = request.form.getlist("pose_types")

    if not pose_types:
        pose_types = request.form.getlist("pose_types[]")

    embedding_docs = []

    try:
        for index, face_file in enumerate(face_images):

            embedding = generate_embedding_from_file(face_file)

            if index < len(pose_types):
                pose_type = pose_types[index]
            else:
                pose_type = request.form.get(
                    f"pose_type_{index + 1}",
                    f"pose_{index + 1}"
                )

            embedding_docs.append({
                "pose_type": pose_type,
                "embedding": embedding,
                "created_at": datetime.utcnow()
            })

    except ValueError as e:
        return jsonify({
            "message": str(e)
        }), 400

    except Exception as e:
        print("REGISTER VENDOR FACE ERROR:", e)
        return jsonify({
            "message": "Gagal memproses wajah vendor"
        }), 500

    hashed_password = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    )

    user_data = {
        "name": name,
        "email": email,
        "phone": phone,
        "password": hashed_password,
        "role": "vendor_pending",
        "vendor_status": "pending",
        "bio": "",
        "is_verified": False,
        "login_provider": "local",
        "face_registered": True,
        "face_embedding_count": len(embedding_docs),
        "created_at": datetime.utcnow()
    }

    inserted_user_id = None
    inserted_vendor_id = None

    try:
        result = users.insert_one(user_data)
        inserted_user_id = result.inserted_id
        user_id = str(inserted_user_id)

        # =========================
        # SIMPAN FILE DOKUMEN VENDOR
        # =========================
        ktp_filename = None
        selfie_filename = None
        license_filename = None

        if ktp_image and ktp_image.filename != "":
            file_extension = os.path.splitext(ktp_image.filename)[1]
            ktp_filename = secure_filename(
                f"ktp_{user_id}{file_extension}"
            )
            ktp_image.save(
                os.path.join(UPLOAD_FOLDER, ktp_filename)
            )

        if selfie_image and selfie_image.filename != "":
            file_extension = os.path.splitext(selfie_image.filename)[1]
            selfie_filename = secure_filename(
                f"selfie_{user_id}{file_extension}"
            )
            selfie_image.save(
                os.path.join(UPLOAD_FOLDER, selfie_filename)
            )

        if business_license and business_license.filename != "":
            file_extension = os.path.splitext(business_license.filename)[1]
            license_filename = secure_filename(
                f"business_license_{user_id}{file_extension}"
            )
            business_license.save(
                os.path.join(UPLOAD_FOLDER, license_filename)
            )

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

            "status": "pending",
            "created_at": datetime.utcnow()
        }

        vendor_result = vendor_registrations.insert_one(vendor_data)
        inserted_vendor_id = vendor_result.inserted_id

        for doc in embedding_docs:
            doc["user_id"] = user_id
            doc["role"] = "vendor_pending"

        face_embeddings.insert_many(embedding_docs)

        otp = generate_and_save_otp(
            email=email,
            purpose="register"
        )

        send_otp_email(
            email=email,
            name=name,
            otp=otp,
            purpose="register"
        )

        create_activity_log(
            user_id=user_id,
            email=email,
            name=name,
            role="vendor_pending",
            action="VENDOR_REGISTER_WITH_FACE"
        )

        return jsonify({
            "message": "Pendaftaran vendor berhasil. Kode OTP telah dikirim ke email",
            "role": "vendor_pending",
            "vendor_status": "pending",
            "name": name,
            "email": email,
            "business_name": business_name,
            "face_registered": True,
            "face_embedding_count": len(embedding_docs)
        }), 201

    except Exception as e:
        print("REGISTER VENDOR WITH FACE DB ERROR:", e)

        if inserted_user_id:
            users.delete_one({
                "_id": inserted_user_id
            })

            face_embeddings.delete_many({
                "user_id": str(inserted_user_id)
            })

        if inserted_vendor_id:
            vendor_registrations.delete_one({
                "_id": inserted_vendor_id
            })

        return jsonify({
            "message": "Pendaftaran vendor gagal"
        }), 500

# =========================
# SAVE FCM TOKEN
# =========================
@auth_bp.route("/save-fcm-token", methods=["POST"])
@jwt_required()
def save_fcm_token():
    current_user_id = get_jwt_identity()
    data = request.get_json()

    fcm_token = data.get("fcm_token")

    if not fcm_token:
        return jsonify({
            "message": "FCM token wajib diisi"
        }), 400

    db.users.update_one(
        {"_id": ObjectId(current_user_id)},
        {
            "$set": {
                "fcm_token": fcm_token
            }
        }
    )

    return jsonify({
        "message": "FCM token berhasil disimpan"
    }), 200

# =========================
# LOGOUT
# =========================
@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    current_user_id = get_jwt_identity()
    user = users.find_one({"_id": ObjectId(current_user_id)})
    
    if user:
        create_activity_log(
            user_id=current_user_id,
            email=user.get("email", "-"),
            name=user.get("name", "-"),
            role=user.get("role", "user"),
            action="LOGOUT"
        )
        
    return jsonify({"message": "Logout berhasil"}), 200

# =========================
# CHANGE PASSWORD
# =========================
@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    current_user_id = get_jwt_identity()
    data = request.get_json()

    if not data:
        return jsonify({
            "message": "Data tidak boleh kosong"
        }), 400

    old_password = data.get("old_password")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")

    if not old_password or not new_password or not confirm_password:
        return jsonify({
            "message": "Password lama, password baru, and konfirmasi password wajib diisi"
        }), 400

    if new_password != confirm_password:
        return jsonify({
            "message": "Konfirmasi password baru tidak sama"
        }), 400

    user = users.find_one({
        "_id": ObjectId(current_user_id)
    })

    if not user:
        return jsonify({
            "message": "User tidak ditemukan"
        }), 404

    user_role = user.get("role", "user")
    min_password_length = 8 if user_role in ["vendor", "vendor_pending"] else 6

    if len(new_password) < min_password_length:
        return jsonify({
            "message": f"Password baru minimal {min_password_length} karakter"
        }), 400

    if old_password == new_password:
        return jsonify({
            "message": "Password baru tidak boleh sama dengan password lama"
        }), 400

    stored_password = user.get("password", "")
    login_provider = user.get("login_provider", "local")

    if not stored_password:
        return jsonify({
            "message": "Akun ini tidak memiliki password lokal"
        }), 400

    if login_provider not in ["local", "", None]:
        return jsonify({
            "message": "Akun ini tidak menggunakan password lokal"
        }), 400

    if isinstance(stored_password, bytes):
        stored_password_bytes = stored_password
    else:
        stored_password_bytes = stored_password.encode("utf-8")

    is_old_password_valid = bcrypt.checkpw(
        old_password.encode("utf-8"),
        stored_password_bytes
    )

    if not is_old_password_valid:
        return jsonify({
            "message": "Password lama salah"
        }), 400

    hashed_new_password = bcrypt.hashpw(
        new_password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    users.update_one(
        {
            "_id": ObjectId(current_user_id)
        },
        {
            "$set": {
                "password": hashed_new_password,
                "login_provider": "local",
                "updated_at": datetime.utcnow()
            }
        }
    )

    create_activity_log(
        user_id=current_user_id,
        email=user.get("email", ""),
        name=user.get("name", ""),
        role=user.get("role", "user"),
        action="CHANGE_PASSWORD",
        title="Mengubah password",
        description="Anda berhasil mengubah password akun.",
        target_type="user",
        target_id=current_user_id,
        metadata={
            "min_password_length": min_password_length
        }
    )

    return jsonify({
        "message": "Password berhasil diubah"
    }), 200