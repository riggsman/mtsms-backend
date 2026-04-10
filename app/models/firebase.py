from pydantic import BaseModel


class TokenRequest(BaseModel):
    token: str


class NotificationRequest(BaseModel):
    title: str
    body: str




