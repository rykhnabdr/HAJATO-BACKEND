from flask import Flask, render_template, request, redirect, session, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from bson.objectid import ObjectId
from routes.auth_routes import auth_bp
from routes.vendor_routes import vendor_bp
from routes.booking_routes import booking_bp
from config.mongo import db
from routes.payment_routes import payment_bp
from flask import send_from_directory
from services.notification_service import send_push_notification
from routes.notification_routes import notification_bp

from config.mail_config import mail

import bcrypt
import settings
import config.firebase_config
from services.notification_service import send_push_notification

app = Flask(__name__)
app.secret_key = "SECRET_ADMIN"

app.config["JWT_SECRET_KEY"] = settings.JWT_SECRET_KEY
app.config["JWT_TOKEN_LOCATION"] = ["headers"]

app.config["JWT_TOKEN_LOCATION"] = ["headers"]

app.config["MAIL_SERVER"] = settings.MAIL_SERVER
app.config["MAIL_PORT"] = settings.MAIL_PORT
app.config["MAIL_USE_TLS"] = settings.MAIL_USE_TLS
app.config["MAIL_USERNAME"] = settings.MAIL_USERNAME
app.config["MAIL_PASSWORD"] = settings.MAIL_PASSWORD
app.config["MAIL_DEFAULT_SENDER"] = settings.MAIL_USERNAME
app.register_blueprint(notification_bp)

JWTManager(app)
CORS(app)

mail.init_app(app)
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(vendor_bp)
app.register_blueprint(booking_bp)
app.register_blueprint(payment_bp)

users = db.users


@app.route("/")
def home():
    return redirect("/login")


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory("uploads", filename)


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

        return redirect("/dashboard")

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    total_vendors = db.vendor_registrations.count_documents({
        "status": "approved"
    })

    pending_approvals = db.vendor_registrations.count_documents({
        "status": "pending"
    })

    rejected_vendors = db.vendor_registrations.count_documents({
        "status": "rejected"
    })

    active_users = users.count_documents({
        "role": "user"
    })

    total_admins = users.count_documents({
        "role": "admin"
    })

    pending_data = list(
        db.vendor_registrations.find({
            "status": "pending"
        }).sort("_id", -1).limit(5)
    )

    pending_vendors = []

    for vendor in pending_data:
        user_email = "-"

        if vendor.get("user_id"):
            user_data = users.find_one({
                "_id": ObjectId(vendor["user_id"])
            })

            if user_data:
                user_email = user_data.get("email", "-")

        pending_vendors.append({
            "id": str(vendor["_id"]),
            "name": vendor.get("business_name", "-"),
            "category": vendor.get("category", "-"),
            "email": user_email,
            "status": vendor.get("status", "pending")
        })

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

        growth_labels=["Users", "Admins", "Vendors"],
        growth_values=[active_users, total_admins, total_vendors],

        cat_labels=["Users", "Admins", "Vendors"],
        cat_values=[active_users, total_admins, total_vendors],

        pending_vendors=pending_vendors
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

    db.bookings.update_one(
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

    vendor = db.vendor_registrations.find_one({
        "_id": ObjectId(booking.get("vendor_id"))
    })

    if vendor:
        vendor_user = db.users.find_one({
            "_id": ObjectId(vendor.get("user_id"))
        })

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


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )

