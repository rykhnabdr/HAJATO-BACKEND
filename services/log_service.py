from datetime import datetime
from config.mongo import db


def create_activity_log(
    user_id,
    email,
    name,
    role,
    action,
    title=None,
    description=None,
    target_type=None,
    target_id=None,
    metadata=None
):
    """
    Fungsi global untuk mencatat aktivitas user, vendor, dan admin ke MongoDB.
    """

    try:
        log_data = {
            "user_id": str(user_id),
            "email": email,
            "name": name,
            "role": role,
            "action": action,
            "title": title or get_default_title(action),
            "description": description or get_default_description(action),
            "target_type": target_type,
            "target_id": str(target_id) if target_id else None,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow()
        }

        db.activity_logs.insert_one(log_data)

        print(
            f"\n[ACTIVITY LOG] 🔵 {str(role).upper()} | {email} | {action} | {log_data['timestamp']} UTC\n"
        )

    except Exception as e:
        print(f"[LOG ERROR] Gagal mencatat log aktivitas: {e}")


def get_default_title(action):
    titles = {
        # =========================
        # AUTH / USER
        # =========================
        "REGISTER": "Registrasi akun",
        "VERIFY_REGISTER_OTP": "Verifikasi akun",
        "LOGIN": "Login berhasil",
        "LOGOUT": "Logout",
        "RESET_PASSWORD": "Reset password",
        "CHANGE_PASSWORD": "Mengubah password",
        "UPDATE_PROFILE": "Update profil",

        # =========================
        # BOOKING USER
        # =========================
        "CREATE_BOOKING": "Membuat booking",
        "CANCEL_BOOKING": "Membatalkan booking",

        # =========================
        # PAYMENT USER
        # =========================
        "CREATE_PAYMENT": "Membuat pembayaran",
        "PAYMENT_PENDING": "Pembayaran menunggu",
        "PAYMENT_SUCCESS": "Pembayaran berhasil",
        "PAYMENT_FAILED": "Pembayaran gagal",

        # =========================
        # REVIEW USER
        # =========================
        "CREATE_REVIEW": "Memberi ulasan",
        "UPDATE_REVIEW": "Mengubah ulasan",
        "DELETE_REVIEW": "Menghapus ulasan",

        # =========================
        # VENDOR
        # =========================
        "VENDOR_REGISTER": "Pendaftaran vendor",
        "VENDOR_APPROVED": "Vendor disetujui",
        "VENDOR_REJECTED": "Vendor ditolak",
        "UPDATE_VENDOR_PROFILE": "Update profil vendor",

        # =========================
        # PACKAGE / SERVICE VENDOR
        # =========================
        "CREATE_PACKAGE": "Menambahkan paket layanan",
        "UPDATE_PACKAGE": "Mengubah paket layanan",
        "DELETE_PACKAGE": "Menghapus paket layanan",

        # =========================
        # BOOKING VENDOR
        # =========================
        "RECEIVE_BOOKING": "Menerima booking baru",
        "ACCEPT_BOOKING": "Menerima booking",
        "REJECT_BOOKING": "Menolak booking",
        "COMPLETE_BOOKING": "Menyelesaikan booking",

        # =========================
        # PAYOUT VENDOR
        # =========================
        "PAYOUT_RELEASED": "Dana dicairkan",

        # =========================
        # BACKUP UNTUK LOG LAMA
        # =========================
        "ADD_REVIEW": "Memberi ulasan",
        "ADD_SERVICE": "Menambahkan paket layanan",
        "EDIT_SERVICE": "Mengubah paket layanan",
        "DELETE_SERVICE": "Menghapus paket layanan",
    }

    return titles.get(action, "Aktivitas")


def get_default_description(action):
    descriptions = {
        # =========================
        # AUTH / USER
        # =========================
        "REGISTER": "Anda berhasil membuat akun HAJATO.",
        "VERIFY_REGISTER_OTP": "Anda berhasil memverifikasi akun menggunakan kode OTP.",
        "LOGIN": "Anda berhasil masuk ke aplikasi HAJATO.",
        "LOGOUT": "Anda keluar dari aplikasi HAJATO.",
        "RESET_PASSWORD": "Anda berhasil mengubah password akun.",
        "CHANGE_PASSWORD": "Anda berhasil mengubah password akun.",
        "UPDATE_PROFILE": "Anda memperbarui data profil akun.",

        # =========================
        # BOOKING USER
        # =========================
        "CREATE_BOOKING": "Anda membuat pesanan baru.",
        "CANCEL_BOOKING": "Anda membatalkan pesanan.",

        # =========================
        # PAYMENT USER
        # =========================
        "CREATE_PAYMENT": "Anda membuat transaksi pembayaran.",
        "PAYMENT_PENDING": "Pembayaran sedang menunggu konfirmasi.",
        "PAYMENT_SUCCESS": "Pembayaran berhasil diproses.",
        "PAYMENT_FAILED": "Pembayaran gagal atau dibatalkan.",

        # =========================
        # REVIEW USER
        # =========================
        "CREATE_REVIEW": "Anda memberikan ulasan dan rating.",
        "UPDATE_REVIEW": "Anda mengubah ulasan.",
        "DELETE_REVIEW": "Anda menghapus ulasan.",

        # =========================
        # VENDOR
        # =========================
        "VENDOR_REGISTER": "Anda melakukan pendaftaran sebagai vendor HAJATO.",
        "VENDOR_APPROVED": "Pendaftaran vendor Anda telah disetujui admin.",
        "VENDOR_REJECTED": "Pendaftaran vendor Anda ditolak oleh admin.",
        "UPDATE_VENDOR_PROFILE": "Anda memperbarui data profil vendor.",

        # =========================
        # PACKAGE / SERVICE VENDOR
        # =========================
        "CREATE_PACKAGE": "Anda menambahkan paket layanan baru.",
        "UPDATE_PACKAGE": "Anda mengubah data paket layanan.",
        "DELETE_PACKAGE": "Anda menghapus paket layanan.",

        # =========================
        # BOOKING VENDOR
        # =========================
        "RECEIVE_BOOKING": "Anda menerima booking baru dari pelanggan.",
        "ACCEPT_BOOKING": "Anda menerima pesanan dari pelanggan.",
        "REJECT_BOOKING": "Anda menolak pesanan dari pelanggan.",
        "COMPLETE_BOOKING": "Anda menyelesaikan pesanan pelanggan.",

        # =========================
        # PAYOUT VENDOR
        # =========================
        "PAYOUT_RELEASED": "Dana dari pesanan telah dicairkan oleh admin.",

        # =========================
        # BACKUP UNTUK LOG LAMA
        # =========================
        "ADD_REVIEW": "Anda memberikan ulasan dan rating.",
        "ADD_SERVICE": "Anda menambahkan paket layanan baru.",
        "EDIT_SERVICE": "Anda mengubah data paket layanan.",
        "DELETE_SERVICE": "Anda menghapus paket layanan.",
    }

    return descriptions.get(action, "Anda melakukan aktivitas di aplikasi HAJATO.")