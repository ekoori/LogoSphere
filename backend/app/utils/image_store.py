"""Pictures in object storage.

Every picture - opening and group banners, exchange pictures, receipt photos,
profile pictures - is stored once in an S3-compatible bucket (production:
Linode Object Storage, bucket logosphere-images in London) under a key made
from its content. The Cassandra row keeps only that key, in its *_object
column. Multi-megabyte blobs in Cassandra rows used to stall the driver's
connection, and every page that touched them paid for it.

Pictures are normalised as they are stored: turned upright (EXIF
orientation), scaled down to what the apps show, and re-encoded as JPEG (WebP
when they have transparency). A picture that is already small enough is kept
byte for byte, so storing the same picture twice gives the same key.

Reads come from a local disk cache first - a key never changes content, so
the cache never goes stale - and from the bucket on a miss. The bucket stays
private: the backend serves pictures through the same endpoints, with the
same permission checks, as before.

Without bucket settings (local development) `store` returns the normalised
bytes for the row's blob column instead, and `fetch` reads them from there.

Settings: S3_ENDPOINT, S3_REGION, S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY,
IMAGE_CACHE_DIR (default: a folder in the system temp directory).
"""
import hashlib
import io
import logging
import os
import re
import tempfile
import threading

log = logging.getLogger(__name__)

# Longest side, in pixels, by where a picture is shown.
MAX_SIDE = {'banner': 1600, 'photo': 1600, 'avatar': 800}
KEEP_UNDER = 600 * 1024          # a picture this small (and within MAX_SIDE) is stored as it came
JPEG_QUALITY = 82
EXT = {'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp', 'image/gif': 'gif'}
FORMAT_TYPE = {'JPEG': 'image/jpeg', 'PNG': 'image/png', 'WEBP': 'image/webp', 'GIF': 'image/gif'}
_KEY = re.compile(r'^[a-z]+/[0-9a-f]{32}\.(jpg|png|webp|gif)$')

_client = None
_client_lock = threading.Lock()


class UnreadableImage(Exception):
    """The bytes don't open as a picture."""


def enabled():
    return all(os.environ.get(k) for k in ('S3_BUCKET', 'S3_ACCESS_KEY', 'S3_SECRET_KEY'))


def _s3():
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                import boto3
                from botocore.config import Config
                _client = boto3.client(
                    's3',
                    endpoint_url=os.environ.get('S3_ENDPOINT') or None,
                    region_name=os.environ.get('S3_REGION') or None,
                    aws_access_key_id=os.environ['S3_ACCESS_KEY'],
                    aws_secret_access_key=os.environ['S3_SECRET_KEY'],
                    config=Config(s3={'addressing_style': 'virtual'}, signature_version='s3v4',
                                  connect_timeout=5, read_timeout=30,
                                  retries={'max_attempts': 3, 'mode': 'standard'}))
    return _client


# ── Normalising ─────────────────────────────────────────────────────────────
def normalise(data, kind='banner'):
    """(bytes, content type) ready to store. Raises UnreadableImage."""
    from PIL import Image, ImageOps
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as e:  # noqa: BLE001 - Pillow raises many kinds (incl. decompression bombs)
        raise UnreadableImage(str(e)) from e
    fmt = (img.format or '').upper()
    side = MAX_SIDE.get(kind, MAX_SIDE['banner'])
    if fmt == 'GIF' and getattr(img, 'is_animated', False):
        return data, 'image/gif'            # re-encoding would lose the animation
    try:
        orientation = img.getexif().get(0x0112, 1)
    except Exception:  # noqa: BLE001
        orientation = 1
    if fmt in FORMAT_TYPE and max(img.size) <= side and len(data) <= KEEP_UNDER and orientation in (1, None):
        return data, FORMAT_TYPE[fmt]
    img = ImageOps.exif_transpose(img)
    img.thumbnail((side, side), Image.LANCZOS)
    out = io.BytesIO()
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        img.convert('RGBA').save(out, 'WEBP', quality=85, method=4)
        return out.getvalue(), 'image/webp'
    img.convert('RGB').save(out, 'JPEG', quality=JPEG_QUALITY, optimize=True, progressive=True)
    return out.getvalue(), 'image/jpeg'


# ── Local cache ─────────────────────────────────────────────────────────────
def _cache_path(key):
    root = os.environ.get('IMAGE_CACHE_DIR') or os.path.join(tempfile.gettempdir(), 'logosphere-image-cache')
    return os.path.join(root, *key.split('/'))


def _cache_get(key):
    try:
        with open(_cache_path(key), 'rb') as fh:
            return fh.read()
    except OSError:
        return None


def _cache_put(key, data):
    path = _cache_path(key)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f'{path}.{os.getpid()}-{threading.get_ident()}.tmp'
        with open(tmp, 'wb') as fh:
            fh.write(data)
        os.replace(tmp, path)
    except OSError as e:
        log.warning('Picture cache: could not write %s: %s', key, e)


# ── What the models call ────────────────────────────────────────────────────
def store(data, kind='banner'):
    """What a row should hold for a new picture: (bucket key, None) when the
    bucket is configured, else (None, normalised bytes) for the blob column;
    (None, None) for no picture. Raises UnreadableImage."""
    if not data:
        return None, None
    body, ctype = normalise(data, kind)
    if not enabled():
        return None, body
    key = f'{kind}s/{hashlib.sha256(body).hexdigest()[:32]}.{EXT[ctype]}'
    _s3().put_object(Bucket=os.environ['S3_BUCKET'], Key=key, Body=body, ContentType=ctype,
                     CacheControl='public, max-age=31536000, immutable')
    _cache_put(key, body)
    return key, None


def load(key):
    """A stored picture's bytes, or None when it can't be had (no such key,
    bucket unreachable): a missing picture is a 404, never a 500."""
    if not key or not _KEY.match(key):
        return None
    data = _cache_get(key)
    if data is not None:
        return data
    if not enabled():
        return None
    try:
        data = _s3().get_object(Bucket=os.environ['S3_BUCKET'], Key=key)['Body'].read()
    except Exception as e:  # noqa: BLE001
        log.warning('Picture %s not loaded from the bucket: %s', key, e)
        return None
    _cache_put(key, data)
    return data


def fetch(key, blob=None):
    """A row's picture: from its bucket key when it has one, else its blob."""
    return load(key) if key else (blob or None)


# ── Serving ─────────────────────────────────────────────────────────────────
# Smaller copies the apps may ask for (?size=): avatars are shown at ~20-96 px,
# and a phone screen is ~1080 px wide.
VARIANT_SIDES = (160, 320, 640)


def digest(data):
    """A picture's content label - the same hash its bucket key is named after,
    so it never changes while the picture doesn't (an HTTP ETag)."""
    return hashlib.sha256(data).hexdigest()[:32]


def sniff(data):
    """A picture's content type, from its first bytes."""
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return 'image/png'
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return 'image/gif'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'image/webp'
    if data.lstrip()[:4] in (b'<svg', b'<?xm'):
        return 'image/svg+xml'
    return 'image/jpeg'


def scaled(data, side):
    """(bytes, content type) of the picture fitting within side x side pixels,
    made once and kept in the local cache under its content. A picture already
    that small (or animated, or not a bitmap) comes back as it is."""
    original = (data, sniff(data))
    if side not in VARIANT_SIDES or original[1] == 'image/svg+xml':
        return original
    key = f'variants/{digest(data)}-{side}'
    hit = _cache_get(key)
    if hit is not None:
        return hit, sniff(hit)
    from PIL import Image
    try:
        img = Image.open(io.BytesIO(data))
        if max(img.size) <= side or getattr(img, 'is_animated', False):
            return original
        img.load()
    except Exception:  # noqa: BLE001 - serve what is stored rather than fail
        return original
    img.thumbnail((side, side), Image.LANCZOS)
    out = io.BytesIO()
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        img.convert('RGBA').save(out, 'WEBP', quality=85, method=4)
    else:
        img.convert('RGB').save(out, 'JPEG', quality=JPEG_QUALITY, optimize=True, progressive=True)
    body = out.getvalue()
    _cache_put(key, body)
    return body, sniff(body)
