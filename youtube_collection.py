import os

from dotenv import load_dotenv
from googleapiclient.discovery import build
from pymongo import MongoClient


load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")


if not YOUTUBE_API_KEY:
    raise ValueError("YOUTUBE_API_KEY belum tersedia")

if not MONGO_URI:
    raise ValueError("MONGO_URI belum tersedia")

# Membuat koneksi ke YouTube Data API
youtube = build(
    "youtube",
    "v3",
    developerKey=YOUTUBE_API_KEY
)

# Kata kunci pencarian berdasarkan kategori vendor hajatan
keywords = {
    "dekorasi pernikahan": "dekorasi pernikahan",
    "pelaminan modern": "pelaminan modern",
    "makeup pengantin": "makeup pengantin",
    "catering wedding": "catering wedding",
    "sound system hajatan": "sound system hajatan",
    "vendor wedding indonesia": "vendor wedding indonesia"
}

print("Koneksi YouTube API berhasil disiapkan")

# Membuat koneksi ke MongoDB Atlas
mongo_client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=10000
)

database = mongo_client["hajato_db"]
collection = database["youtube_vendor"]

# Mengecek koneksi
mongo_client.admin.command("ping")

print("Koneksi MongoDB berhasil")

# Menampung hasil collection dari YouTube
collected_data = []

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
        video_id = item["id"]["videoId"]
        snippet = item["snippet"]

        data_video = {
            "video_id": video_id,
            "kategori": kategori,
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
            "channel": snippet.get("channelTitle", ""),
            "thumbnail": snippet["thumbnails"]["high"]["url"],
            "publish_date": snippet.get("publishedAt", ""),
            "video_link": f"https://www.youtube.com/watch?v={video_id}"
        }

        collected_data.append(data_video)

print(f"Jumlah data yang berhasil diambil: {len(collected_data)}")

# Membuat video_id menjadi unik agar data tidak duplikat
collection.create_index(
    "video_id",
    unique=True,
    partialFilterExpression={
        "video_id": {"$type": "string"}
    }
)

jumlah_baru = 0
jumlah_diperbarui = 0

for data_video in collected_data:
    hasil = collection.update_one(
        {"video_id": data_video["video_id"]},
        {"$set": data_video},
        upsert=True
    )

    if hasil.upserted_id:
        jumlah_baru += 1
    else:
        jumlah_diperbarui += 1

print(f"Data baru masuk: {jumlah_baru}")
print(f"Data lama diperbarui: {jumlah_diperbarui}")

mongo_client.close()

print("Proses collection selesai")