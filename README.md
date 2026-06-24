# HAJATO Backend API

Backend API untuk aplikasi **HAJATO (Wedding & Event Organizer Platform)**.

Backend ini dibangun menggunakan Flask dan MongoDB untuk menangani autentikasi, manajemen vendor, pemesanan, pembayaran, ulasan, notifikasi, serta dashboard admin.

---

## 🚀 Teknologi

- Python 3.12
- Flask
- Flask JWT Extended
- MongoDB
- PyMongo
- Flask Mail
- Firebase Cloud Messaging (FCM)
- JWT Authentication
- bcrypt
- REST API

---

## 📂 Struktur Project

```bash
HAJATO-BACKEND/
│
├── app.py
├── config/
│   ├── mongo.py
│   ├── mail_config.py
│
├── routes/
│   ├── auth_routes.py
│   ├── booking_routes.py
│   ├── vendor_routes.py
│   ├── review_routes.py
│   ├── notification_routes.py
│   ├── admin_routes.py
│
├── middleware/
│   └── role_middleware.py
│
├── services/
│   └── log_service.py
│
├── uploads/
│
└── requirements.txt
```

---

## ⚙️ Instalasi

### Clone Repository

```bash
git clone https://github.com/username/hajato-backend.git
cd hajato-backend
```

### Buat Virtual Environment

```bash
python -m venv venv
```

Aktifkan:

Windows

```bash
venv\Scripts\activate
```

Linux / Mac

```bash
source venv/bin/activate
```

### Install Dependency

```bash
pip install -r requirements.txt
```

---

## 🔐 Environment Variables

Buat file:

```bash
.env
```

Isi:

```env
MONGO_URI=mongodb://localhost:27017
JWT_SECRET_KEY=your-secret-key

MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-password

GOOGLE_CLIENT_ID=your-google-client-id
```

---

## ▶️ Menjalankan Server

```bash
python app.py
```

Server berjalan di:

```bash
http://127.0.0.1:5000
https://untrod-chante-subectodermic.ngrok-free.dev
```

---

## 📌 Fitur Backend

### Authentication

- Register
- Login
- Login Google
- Email Verification OTP
- Forgot Password
- Reset Password
- Change Password
- Logout

### Vendor

- Registrasi Vendor
- Verifikasi Vendor
- Upload Dokumen Vendor
- Kelola Data Vendor
- Kelola Layanan Vendor

### Booking

- Buat Booking
- Status Booking
- Riwayat Booking
- Jadwal Vendor

### Review

- Tambah Review
- Rating Vendor
- Statistik Rating

### Notification

- Push Notification
- Firebase Cloud Messaging
- Notifikasi Booking

### Admin

- Dashboard Statistik
- Kelola User
- Kelola Vendor
- Kelola Booking
- Activity Log

---

## 🔒 Authentication

Menggunakan JWT Token.

Header:

```http
Authorization: Bearer <token>
```

---

## 📊 Database

MongoDB Collections:

```text
users
vendor_registrations
vendor_services
bookings
reviews
notifications
activity_logs
withdrawals
```

---

## 👨‍💻 Developer

Capstone Project

HAJATO – Wedding & Event Organizer Platform

2026
