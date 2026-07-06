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
    if not text:
        return ""

    text = html.unescape(str(text))
    text = text.lower()

    text = re.sub(
        r"https?://\S+|www\.\S+",
        " ",
        text
    )

    text = re.sub(
        r"[^\w\s]",
        " ",
        text,
        flags=re.UNICODE
    )

    text = text.replace("_", " ")

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
# 2A. FUNGSI CEK COUNTRY CHANNEL
# Hanya channel dengan country ID yang akan disimpan
# =========================================================

channel_country_cache = {}

def get_channel_country(channel_id):
    if not channel_id:
        return ""

    if channel_id in channel_country_cache:
        return channel_country_cache[channel_id]

    try:
        request = youtube.channels().list(
            part="snippet",
            id=channel_id
        )

        response = request.execute()
        items = response.get("items", [])

        country = ""

        if items:
            country = items[0].get("snippet", {}).get("country", "")

        country = country.upper()

        channel_country_cache[channel_id] = country

        return country

    except Exception as error:
        print(f"Gagal mengecek country channel {channel_id}: {error}")
        channel_country_cache[channel_id] = ""
        return ""


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

mongo_client.admin.command("ping")

print("Koneksi MongoDB berhasil")


# Waktu proses collection dijalankan
collection_time = datetime.now(timezone.utc)

# ID batch untuk menandai hasil collection terbaru
collection_batch_id = collection_time.strftime("%Y%m%d%H%M%S")


# =========================================================
# 4. PROSES DATA COLLECTION
# Mengambil data video dari YouTube berdasarkan keyword
# dan hanya menyimpan channel dengan country Indonesia
# =========================================================

raw_data = []

for kategori, keyword in keywords.items():
    print(f"Mengambil data kategori: {kategori}")

    request = youtube.search().list(
        q=f"{keyword} Indonesia",
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

        if not video_id:
            continue

        channel_id = snippet.get("channelId", "")
        channel_country = get_channel_country(channel_id)

        # Filter utama:
        # hanya simpan video dari channel dengan country Indonesia
        if channel_country != "ID":
            print(
                f"Skip bukan channel Indonesia: "
                f"{snippet.get('channelTitle', '')} "
                f"| country={channel_country or 'UNKNOWN'}"
            )
            continue

        thumbnails = snippet.get("thumbnails", {})

        thumbnail_data = (
            thumbnails.get("high")
            or thumbnails.get("medium")
            or thumbnails.get("default")
            or {}
        )

        thumbnail_url = thumbnail_data.get("url", "")

        video_data = {
            "video_id": video_id,
            "kategori": kategori,
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
            "channel": snippet.get("channelTitle", ""),
            "channel_id": channel_id,
            "channel_country": channel_country,
            "thumbnail": thumbnail_url,
            "publish_date": snippet.get("publishedAt", ""),
            "video_link": (
                f"https://www.youtube.com/watch?v={video_id}"
            )
        }

        raw_data.append(video_data)

print(
    f"Jumlah data mentah dari channel Indonesia: "
    f"{len(raw_data)}"
)


# =========================================================
# 5. DATA PREPARATION
# =========================================================

prepared_by_video_id = {}

for data in raw_data:
    video_id = data.get("video_id", "").strip()

    if not video_id:
        continue

    kategori = data.get("kategori", "").strip()
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()

    if video_id not in prepared_by_video_id:
        prepared_by_video_id[video_id] = {
            "video_id": video_id,

            "kategori": kategori,
            "categories": [kategori] if kategori else [],

            "title": title,
            "description": description,

            "clean_title": clean_text(title),
            "clean_description": clean_text(description),

            "channel": data.get("channel", "").strip(),
            "channel_id": data.get("channel_id", "").strip(),
            "channel_country": data.get("channel_country", "").strip(),

            "thumbnail": data.get("thumbnail", "").strip(),
            "publish_date": data.get("publish_date", "").strip(),
            "video_link": data.get("video_link", "").strip(),

            "last_collected_at": collection_time
        }

    else:
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
# 6. VALIDASI DATA BARU
#
# Data lama TIDAK akan dihapus jika:
# - collection gagal
# - data kosong
# - data terlalu sedikit
# - kategori terlalu sedikit
# =========================================================

MIN_TOTAL_DATA = 10
MIN_TOTAL_KATEGORI = 3

if not prepared_data:
    raise ValueError(
        "Prepared data kosong. Data lama tidak dihapus."
    )

if len(prepared_data) < MIN_TOTAL_DATA:
    raise ValueError(
        f"Jumlah data terlalu sedikit: {len(prepared_data)}. "
        "Data lama tidak dihapus."
    )

kategori_terkumpul = set()

for data_video in prepared_data:
    for kategori in data_video.get("categories", []):
        if kategori:
            kategori_terkumpul.add(kategori)

if len(kategori_terkumpul) < MIN_TOTAL_KATEGORI:
    raise ValueError(
        f"Kategori yang terkumpul hanya {len(kategori_terkumpul)}. "
        "Data lama tidak dihapus."
    )

print("Validasi data baru berhasil")
print(f"Jumlah data valid: {len(prepared_data)}")
print(f"Jumlah kategori valid: {len(kategori_terkumpul)}")


# =========================================================
# 7. DATA STORAGE KE MONGODB DENGAN SISTEM BATCH
#
# Alur:
# 1. Data baru di-insert/update dulu
# 2. Kalau proses berhasil, data lama yang bukan batch terbaru dihapus
#
# Jadi kalau collection hari ini gagal,
# data kemarin tetap aman.
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

jumlah_baru = 0
jumlah_diperbarui = 0

for data_video in prepared_data:
    data_video["collection_batch_id"] = collection_batch_id
    data_video["collection_date"] = collection_time.strftime("%Y-%m-%d")
    data_video["last_collected_at"] = collection_time

    hasil = collection.update_one(
        {
            "video_id": data_video["video_id"]
        },
        {
            "$set": data_video,
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


hapus_data_lama = collection.delete_many(
    {
        "collection_batch_id": {
            "$ne": collection_batch_id
        }
    }
)

print(
    f"Data lama yang bukan batch terbaru dihapus: "
    f"{hapus_data_lama.deleted_count}"
)


# =========================================================
# 8. MENUTUP KONEKSI MONGODB
# =========================================================

mongo_client.close()

print("Proses collection, preparation, dan storage selesai")