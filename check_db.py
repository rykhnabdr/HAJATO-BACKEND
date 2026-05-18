from config.mongo import db

try:

    collections = db.list_collection_names()

    print("MongoDB Connected")
    print(collections)

except Exception as e:
    print(e)