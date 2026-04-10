from fastapi import APIRouter
import firebase_admin
from firebase_admin import credentials, messaging

from app.services.firebase import NotificationRequest, TokenRequest


router = APIRouter("/api/v1/firebase", tags=["firebase"])

cred = credentials.Certificate("serviceAccount.json")


firebase_admin.initialize_app(cred)

tokens = []


@router.post("/save-token")
def save_token(request: TokenRequest):

    if request.token not in tokens:
        tokens.append(request.token)

    return {"status": "token saved"}


@router.post("/send-notification")
def send_notification(notification: NotificationRequest):

    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=notification.title,
            body=notification.body
        ),
        tokens=tokens
    )

    response = messaging.send_multicast(message)

    return {
        "success": response.success_count,
        "failure": response.failure_count
    }