from firebase_admin import messaging
from datetime import datetime

from config.mongo import db


def send_push_notification(token, title, body, data=None):

    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    channel_id="hajato_channel",
                    sound="default"
                )
            ),
            data=data or {},
            token=token
        )

        response = messaging.send(message)

        print("NOTIFICATION SENT:", response)

        return True

    except Exception as e:
        print("NOTIFICATION ERROR:", e)

        return False


def save_notification(receiver_id, title, message, role=None):

    try:
        db.notifications.insert_one({
            "receiver_id": str(receiver_id),
            "role": role,
            "title": title,
            "message": message,
            "is_read": False,
            "created_at": datetime.utcnow()
        })

        print("NOTIFICATION SAVED")

        return True

    except Exception as e:
        print("SAVE NOTIFICATION ERROR:", e)

        return False