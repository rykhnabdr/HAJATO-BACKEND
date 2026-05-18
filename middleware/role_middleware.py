from functools import wraps
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import verify_jwt_in_request


from config.mongo import db
from bson.objectid import ObjectId

users = db.users


def role_required(required_role):

    def wrapper(fn):

        @wraps(fn)
        def decorator(*args, **kwargs):

            verify_jwt_in_request()

            current_user_id = get_jwt_identity()

            user = users.find_one({
                "_id": ObjectId(current_user_id)
            })

            if not user:
                return {
                    "message": "User tidak ditemukan"
                }, 404

            if user["role"] != required_role:
                return {
                    "message": "Akses ditolak"
                }, 403

            return fn(*args, **kwargs)

        return decorator

    return wrapper