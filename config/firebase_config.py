import os
import json
import firebase_admin
from firebase_admin import credentials

if not firebase_admin._apps:
    # 1. Coba intip dulu apakah ada data di Environment Variable Railway
    firebase_env = os.getenv("FIREBASE_CONFIG_JSON")

    if firebase_env:
        try:
            # Kalau di server cloud, ubah teks JSON dari env jadi dictionary
            firebase_info = json.loads(firebase_env)
            cred = credentials.Certificate(firebase_info)
            print("[FIREBASE] 🟢 Berhasil inisialisasi menggunakan Environment Variable Railway!")
        except Exception as e:
            print(f"[FIREBASE] ⚠️ Gagal parse JSON dari Env, mencoba fallback file: {str(e)}")
            cred = credentials.Certificate("firebase/serviceAccountKey.json")
    else:
        # 2. Kalau di laptop lokal (env kosong), tetep pake file fisik bawaanmu
        cred = credentials.Certificate("firebase/serviceAccountKey.json")
        print("[FIREBASE] 💻 Berhasil inisialisasi menggunakan file serviceAccountKey.json lokal.")

    firebase_admin.initialize_app(cred)