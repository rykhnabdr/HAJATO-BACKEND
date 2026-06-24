from db import activity_logs
from datetime import datetime

def log_activity(user_id, role, activity, description):
    try:
        activity_logs.insert_one({
            "user_id": user_id,
            "role": role,
            "activity": activity,
            "description": description,
            "created_at": datetime.utcnow()
        })
    except Exception as e:
        print("Gagal simpan log:", e)