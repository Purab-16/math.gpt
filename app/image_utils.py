"""Helpers for checking uploaded images safely."""

from typing import Optional

from fastapi import UploadFile

from app.exceptions import InvalidInputError

# Maximum allowed image size (10 MB)
MAX_IMAGE_BYTES = 10 * 1024 * 1024
READ_CHUNK_BYTES = 1024 * 1024


def detect_image_type(data: bytes) -> Optional[str]:
    """Return the MIME type based on the file's first bytes (magic bytes).

    The file name and the browser's content type are not trusted, because
    they are easy to fake. Only PNG, JPEG, and WEBP are allowed.
    """
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(data) >= 12 and data[0:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


async def read_image(upload: UploadFile) -> tuple[bytes, str]:
    """Read an uploaded image in chunks and validate its size and type.

    Returns:
        tuple[bytes, str]: The image bytes and the detected MIME type.

    Raises:
        InvalidInputError: If the image is empty, too large, or not PNG/JPEG/WEBP.
    """
    chunks = []
    total_size = 0

    # Read in chunks so we can stop as soon as the size limit is crossed
    while chunk := await upload.read(READ_CHUNK_BYTES):
        total_size += len(chunk)
        if total_size > MAX_IMAGE_BYTES:
            raise InvalidInputError(
                "Image is too large. Please upload an image under 10 MB.",
                error_code="IMAGE_TOO_LARGE",
            )
        chunks.append(chunk)

    data = b"".join(chunks)

    mime_type = detect_image_type(data)
    if mime_type is None:
        raise InvalidInputError(
            "Invalid image. Please upload a PNG, JPEG, or WEBP image.",
            error_code="INVALID_IMAGE",
        )

    return data, mime_type
