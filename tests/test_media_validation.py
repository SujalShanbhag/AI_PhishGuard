import pytest
from app.security.file_security import validate_file_content, sanitize_filename, calculate_sha256_bytes

def test_file_signature_validation_jpeg():
    # True JPEG magic bytes: FF D8 FF E0 ...
    valid_jpeg_header = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
    is_valid, mime = validate_file_content(valid_jpeg_header, "evidence.jpg", "image")
    assert is_valid is True
    assert mime == "image/jpeg"

def test_file_signature_validation_png():
    # True PNG magic bytes: \x89PNG\r\n\x1a\n ...
    valid_png_header = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01"
    is_valid, mime = validate_file_content(valid_png_header, "screenshot.png", "image")
    assert is_valid is True
    assert mime == "image/png"

def test_reject_corrupt_or_truncated_file():
    truncated = b"\xff\xd8"  # only 2 bytes
    is_valid, err = validate_file_content(truncated, "corrupt.jpg", "image")
    assert is_valid is False
    assert "truncated" in err.lower() or "too small" in err.lower()

def test_reject_fake_extension():
    # Executable header or plain text disguised as .jpg
    fake_payload = b"This is just a text file renamed to fake.jpg"
    is_valid, err = validate_file_content(fake_payload, "fake.jpg", "image")
    assert is_valid is False
    assert "Invalid image binary signature" in err

def test_sanitize_filename_prevents_traversal():
    malicious = "../../etc/passwd.jpg"
    clean = sanitize_filename(malicious)
    assert "/" not in clean
    assert "\\" not in clean
    assert "passwd.jpg" in clean

def test_sha256_bytes():
    payload = b"VERITAS_AI_INTEGRITY_TEST"
    hash1 = calculate_sha256_bytes(payload)
    assert len(hash1) == 64
    # Deterministic
    assert hash1 == calculate_sha256_bytes(payload)
