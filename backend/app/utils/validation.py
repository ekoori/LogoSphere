# Small input-validation helpers shared across routes.


def is_supported_image(data):
    """True if `data` (raw bytes) starts with a recognised image magic number.
    Guards the banner/profile upload endpoints against non-image blobs — the
    frontend renders whatever is stored as a data URI, so we only want real
    images in there. Accepts JPEG, PNG, GIF, and WebP."""
    if not data or len(data) < 12:
        return False
    return (
        data[:3] == b'\xff\xd8\xff'                      # JPEG
        or data[:8] == b'\x89PNG\r\n\x1a\n'              # PNG
        or data[:6] in (b'GIF87a', b'GIF89a')           # GIF
        or (data[:4] == b'RIFF' and data[8:12] == b'WEBP')  # WebP
    )
