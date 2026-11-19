# Small input-validation helpers shared across routes.

import io

from flask import Response


def entity_image_response(data):
    """An <img>-friendly response for a stored banner (sphere, alliance,
    project, opening): public, labelled with its content so a client that has
    it gets a 304 (see app/utils/pictures). A 404 when there's none."""
    from app.utils.pictures import picture_response
    return picture_response(data)


def is_supported_image(data):
    """True if `data` (raw bytes) starts with a recognised image magic number.
    Guards the banner/profile upload endpoints against non-image blobs — the
    frontend renders whatever is stored as a data URI, so we only want real
    images in there. Accepts JPEG, PNG, GIF, and WebP."""
    if not data or len(data) < 12:
        return False
    if not (
        data[:3] == b'\xff\xd8\xff'                      # JPEG
        or data[:8] == b'\x89PNG\r\n\x1a\n'              # PNG
        or data[:6] in (b'GIF87a', b'GIF89a')           # GIF
        or (data[:4] == b'RIFF' and data[8:12] == b'WEBP')  # WebP
    ):
        return False
    # The right first bytes aren't enough: pictures are re-encoded when they
    # are stored (app/utils/image_store), so they must really open.
    try:
        from PIL import Image
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
        return True
    except Exception:  # noqa: BLE001 - Pillow raises many kinds
        return False
