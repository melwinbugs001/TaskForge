import base64
import binascii
import ipaddress
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator


def _validate_endpoint(value: str) -> str:
    parsed = urlsplit(value)
    hostname = (parsed.hostname or "").rstrip(".").lower()
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or hostname == "localhost"
        or hostname.endswith((".localhost", ".local", ".internal"))
    ):
        raise ValueError("Push endpoints must be secure public HTTPS URLs")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return value
    if not address.is_global:
        raise ValueError("Push endpoints must not use a private or reserved IP")
    return value


def _decode_key(value: str, expected_length: int, name: str) -> str:
    try:
        decoded = base64.b64decode(
            value + "=" * ((4 - len(value) % 4) % 4),
            altchars=b"-_",
            validate=True,
        )
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"{name} must be a base64url-encoded key") from exc
    if len(decoded) != expected_length:
        raise ValueError(f"{name} has an invalid key length")
    return value


class PushSubscriptionKeys(BaseModel):
    p256dh: str = Field(min_length=32, max_length=512)
    auth: str = Field(min_length=16, max_length=256)

    @field_validator("p256dh")
    @classmethod
    def validate_p256dh(cls, value: str) -> str:
        return _decode_key(value, 65, "p256dh")

    @field_validator("auth")
    @classmethod
    def validate_auth(cls, value: str) -> str:
        return _decode_key(value, 16, "auth")


class PushSubscriptionInput(BaseModel):
    endpoint: str = Field(min_length=1, max_length=4096)
    keys: PushSubscriptionKeys

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, value: str) -> str:
        return _validate_endpoint(value)


class PushSubscriptionStatus(BaseModel):
    enabled: bool
    subscription_count: int = Field(ge=0)


class VapidPublicKeyRead(BaseModel):
    public_key: str


class PushSubscriptionDelete(BaseModel):
    endpoint: str = Field(min_length=1, max_length=4096)

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, value: str) -> str:
        return _validate_endpoint(value)