import hashlib
import re
import os
from pathlib import Path
from typing import Tuple
from fastapi import HTTPException, UploadFile, status

# Allowed MIME signatures by Magic Bytes
MAGIC_SIGNATURES = {
    # Images
    "jpeg": [b"\xff\xd8\xff"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "webp": [b"RIFF"], # followed by WEBP at offset 8
    # Video
    "mp4": [b"ftyp", b"moov", b"mdat"], # usually at offset 4
    "avi": [b"RIFF"], # followed by AVI at offset 8
    # Audio
    "wav": [b"RIFF"], # followed by WAVE at offset 8
    "mp3": [b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"],
}

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal and harmful characters."""
    clean = os.path.basename(filename)
    clean = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", clean)
    if not clean or clean.startswith("."):
        clean = f"media_{clean}"
    return clean

def calculate_sha256(file_path: str) -> str:
    """Calculate SHA-256 hash of a file on disk."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def calculate_sha256_bytes(data: bytes) -> str:
    """Calculate SHA-256 hash of byte buffer."""
    return hashlib.sha256(data).hexdigest()

def validate_file_content(file_bytes: bytes, filename: str, expected_type: str) -> Tuple[bool, str]:
    """
    Validate file by true binary header rather than relying solely on filename extension.
    expected_type in ('image', 'video', 'audio')
    """
    if len(file_bytes) < 12:
        return False, "File is too small or truncated."

    ext = Path(filename).suffix.lower().lstrip(".")
    header = file_bytes[:16]

    if expected_type == "image":
        if header.startswith(b"\xff\xd8\xff"):
            return True, "image/jpeg"
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return True, "image/png"
        if header.startswith(b"RIFF") and b"WEBP" in header[8:16]:
            return True, "image/webp"
        return False, "Invalid image binary signature. Only genuine JPG, PNG, and WEBP are accepted."

    elif expected_type == "video":
        # MP4 typically has 'ftyp' starting at byte 4
        if b"ftyp" in header[4:12] or header.startswith(b"\x00\x00\x00"):
            return True, "video/mp4"
        if header.startswith(b"RIFF") and b"AVI " in header[8:16]:
            return True, "video/avi"
        # Apple QuickTime MOV
        if b"moov" in header[4:16] or b"wide" in header[4:16] or b"mdat" in header[4:16]:
            return True, "video/quicktime"
        # Support common container check
        if ext in ["mp4", "mov", "avi"]:
            return True, f"video/{ext}"
        return False, "Invalid video binary signature. Supported formats: MP4, MOV, AVI."

    elif expected_type == "audio":
        if header.startswith(b"RIFF") and b"WAVE" in header[8:16]:
            return True, "audio/wav"
        if header.startswith(b"ID3") or header[:2] in [b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"]:
            return True, "audio/mpeg"
        if ext in ["wav", "mp3"]:
            return True, f"audio/{ext}"
        return False, "Invalid audio binary signature. Supported formats: WAV, MP3."

    return False, f"Unknown media category: {expected_type}"
