"""The original admitted body and a deliberately small transport receipt."""

from dataclasses import dataclass

from .canonical import Object, digest


@dataclass(frozen=True)
class ApifyResponse:
    body: bytes
    status: int
    content_type: str
    content_encoding: str
    encoded_bytes: int

    def receipt(self) -> Object:
        return {
            "status": self.status,
            "content_type": self.content_type,
            "content_encoding": self.content_encoding,
            "encoded_bytes": self.encoded_bytes,
            "decoded_bytes": len(self.body),
            "body_sha256": digest(self.body),
        }
