import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = "mongodb://127.0.0.1:27017/"
DB_NAME = "hajato_db"

JWT_SECRET_KEY = "hajato_secret"