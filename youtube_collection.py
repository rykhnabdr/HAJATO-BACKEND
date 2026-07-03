import os
import re
import html
from datetime import datetime, timezone

from dotenv import load_dotenv
from googleapiclient.discovery import build
from pymongo import MongoClient


# =========================================================
# 0. KONFIGURASI
# Membaca YouTube API Key dan MongoDB URI
# dari environment variable / GitHub Secrets
# =========================================================

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

if not YOUTUBE_API_KEY:
    raise ValueError("YOUTUBE_API_KEY belum tersedia")

if not MONGO_URI:
    raise ValueError("MONGO_URI belum tersedia")


# =========================================================
# 1. FUNGSI DATA PREPARATION
# Membersihkan teks judul dan deskripsi video
# =========================================================

def clean_text(text):
    """
    Membersihkan teks dengan tahapan:
    1. Mengubah HTML entity menjadi karakter biasa
    2. Mengubah teks menjadi huruf kecil
    3. Menghapus URL
    4. Menghapus tanda baca dan simbol
    5. Menghapus spasi berlebih
    """

    if not text:
        return ""

    # Mengubah HTML entity, contoh: &amp; menjadi &
    text = html.unescape(str(text))

    # Mengubah semua teks menjadi huruf kecil
    text = text.lower()

    # Menghapus URL
    text = re.sub(
        r"https?://\S+|www\.\S+",
        " ",
        text
    )

    # Menghapus tanda baca dan simbol
    # Huruf, angka, dan spasi tetap dipertahankan
    text = re.sub(
        r"[^\w\s]",
        " ",
        text,
        flags=re.UNICODE
    )

    # Menghapus underscore
    text = text.replace("_", " ")

    # Menghapus spasi berlebih
    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text


# =========================================================
# 2. DATA COLLECTION DARI YOUTUBE API
# Membuat koneksi ke YouTube Data API
# =========================================================

youtube = build(
    "youtube",
    "v3",
    developerKey=YOUTUBE_API_KEY
)

print("Koneksi YouTube API berhasil disiapkan")


# Kata kunci pencarian berdasarkan kategori vendor hajatan
keywords = {
    "dekorasi pernikahan": "dekorasi pernikahan",
    "pelaminan modern": "pelaminan modern",
    "makeup pengantin": "makeup pengantin",
    "catering wedding": "catering wedding",
    "sound system hajatan": "sound system hajatan",
    "vendor wedding indonesia": "vendor wedding indonesia"
}


# =========================================================
# 3. DATA STORAGE MENGGUNAKAN MONGODB
# Membuat koneksi ke MongoDB Atlas
# =========================================================

mongo_client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=10000
)

database = mongo_client["hajato_db"]
collection = database["youtube_vendor"]

# Mengecek koneksi MongoDB
mongo_client.admin.command("ping")

print("Koneksi MongoDB berhasil")


# Waktu proses collection dijalankan
collection_time = datetime.now(timezone.utc)


# =========================================================
# 4. PROSES DATA COLLECTION
# Mengambil data video dari YouTube berdasarkan keyword
# =========================================================

raw_data = []

for kategori, keyword in keywords.items():
    print(f"Mengambil data kategori: {kategori}")

    request = youtube.search().list(
        q=keyword,
        part="snippet",
        type="video",
        maxResults=10,
        regionCode="ID",
        relevanceLanguage="id",
        order="date"
    )

    response = request.execute()

    for item in response.get("items", []):
        video_id = item.get("id", {}).get("videoId")
        snippet = item.get("snippet", {})

        # Melewati data yang tidak memiliki video_id
        if not video_id:
            continue

        # Mengambil thumbnail secara aman
        thumbnails = snippet.get("thumbnails", {})

        thumbnail_data = (
            thumbnails.get("high")
            or thumbnails.get("medium")
            or thumbnails.get("default")
            or {}
        )

        thumbnail_url = thumbnail_data.get("url", "")

        # Data mentah hasil collection YouTube
        video_data = {
            "video_id": video_id,
            "kategori": kategori,
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
            "channel": snippet.get("channelTitle", ""),
            "thumbnail": thumbnail_url,
            "publish_date": snippet.get("publishedAt", ""),
            "video_link": (
                f"https://www.youtube.com/watch?v={video_id}"
            )
        }

        raw_data.append(video_data)

print(
    f"Jumlah data mentah yang berhasil diambil: "
    f"{len(raw_data)}"
)


# =========================================================
# 5. DATA PREPARATION
#
# Tahapan:
# - Memilih atribut yang diperlukan
# - Menangani data kosong
# - Membersihkan judul
# - Membersihkan deskripsi
# - Menghapus duplikasi dalam satu kali collection
# - Menggabungkan kategori jika satu video ditemukan
#   pada beberapa keyword
# =========================================================

prepared_by_video_id = {}

for data in raw_data:
    video_id = data.get("video_id", "").strip()

    # Melewati data tanpa video_id
    if not video_id:
        continue

    kategori = data.get("kategori", "").strip()
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()

    if video_id not in prepared_by_video_id:
        prepared_by_video_id[video_id] = {
            "video_id": video_id,

            # Kategori utama
            "kategori": kategori,

            # Menampung semua kategori yang sesuai
            "categories": [kategori] if kategori else [],

            # Teks asli
            "title": title,
            "description": description,

            # Teks yang sudah dibersihkan
            "clean_title": clean_text(title),
            "clean_description": clean_text(description),

            "channel": data.get("channel", "").strip(),
            "thumbnail": data.get("thumbnail", "").strip(),
            "publish_date": data.get("publish_date", "").strip(),
            "video_link": data.get("video_link", "").strip(),

            # Waktu terakhir video diperoleh
            "last_collected_at": collection_time
        }

    else:
        # Jika satu video ditemukan pada keyword lain,
        # kategori tersebut ditambahkan ke array categories
        existing_categories = prepared_by_video_id[
            video_id
        ]["categories"]

        if kategori and kategori not in existing_categories:
            existing_categories.append(kategori)


prepared_data = list(prepared_by_video_id.values())

print(
    f"Jumlah data setelah preparation dan deduplikasi: "
    f"{len(prepared_data)}"
)


# =========================================================
# 6. DATA PREPARATION: PENCEGAHAN DUPLIKASI MONGODB
#
# video_id dijadikan field unik.
# Data lama yang tidak memiliki video_id akan diabaikan
# oleh partialFilterExpression.
# =========================================================

collection.create_index(
    "video_id",
    unique=True,
    partialFilterExpression={
        "video_id": {
            "$type": "string"
        }
    }
)


# =========================================================
# 7. DATA STORAGE KE MONGODB
#
# Jika video_id belum tersedia:
# → data baru dimasukkan
#
# Jika video_id sudah tersedia:
# → data lama diperbarui
# =========================================================

jumlah_baru = 0
jumlah_diperbarui = 0

for data_video in prepared_data:
    hasil = collection.update_one(
        {
            "video_id": data_video["video_id"]
        },
        {
            "$set": data_video,

            # created_at hanya dibuat ketika dokumen baru
            "$setOnInsert": {
                "created_at": collection_time
            }
        },
        upsert=True
    )

    if hasil.upserted_id:
        jumlah_baru += 1
    else:
        jumlah_diperbarui += 1


print(f"Data baru masuk: {jumlah_baru}")
print(f"Data lama diperbarui: {jumlah_diperbarui}")


# =========================================================
# 8. MENUTUP KONEKSI MONGODB
# =========================================================

mongo_client.close()

print("Proses collection, preparation, dan storage selesai")