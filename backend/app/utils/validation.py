# Small input-validation helpers shared across routes.

from flask import Response


def entity_image_response(data):
    """Build an <img>-friendly HTTP response for a stored banner blob (sphere,
    alliance, project, opening). Public + cacheable — entity banners aren't
    sensitive, and serving them here keeps the (large) base64 out of the list
    JSON. Returns a 404 tuple when there's no image."""
    if not data:
        return ('', 404)
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        ctype = 'image/png'
    elif data[:6] in (b'GIF87a', b'GIF89a'):
        ctype = 'image/gif'
    elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        ctype = 'image/webp'
    else:
        ctype = 'image/jpeg'
    resp = Response(data, mimetype=ctype)
    resp.headers['Cache-Control'] = 'public, max-age=300'
    return resp


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
