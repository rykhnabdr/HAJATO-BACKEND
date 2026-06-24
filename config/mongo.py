from pymongo import MongoClient
import settings

client = MongoClient(settings.MONGO_URI)

db = client[settings.DB_NAME]
users_collection = db["users"]
admin_logs_collection = db["admin_logs"]