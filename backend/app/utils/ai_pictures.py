# Which pictures are AI-made, so they are labelled and kept out of evidence in
# real spheres (app/utils/evidence.py has that rule).
#
# A picture is known to be AI-made when
#   * we made it: every picture we generate is remembered, by the hash of its
#     bytes and by a 16x16 thumbnail that survives resizing and re-encoding; or
#   * its file says so: the IPTC "trained algorithmic media" source that C2PA
#     and XMP carry, or the prompt text some generators write into a PNG.
# That can't catch every AI picture made elsewhere, and doesn't claim to.
import io
import logging
import time
from datetime import datetime

from PIL import Image, ImageChops, ImageStat

from app.db import session
from app.utils import image_store

log = logging.getLogger(__name__)

TABLE_DDL = ('CREATE TABLE IF NOT EXISTS ai_pictures ('
             'digest text PRIMARY KEY, thumb blob, source text, made_at timestamp)')

SIDE = 16               # of a thumbnail
SAME_WITHIN = 6.0       # mean difference per channel, of 255
TOO_PLAIN = 10.0        # plainer pictures than this would all look alike
MAX_SIDE = 1280
FRESH_SECONDS = 10

# Our own pictures say what they are, for whoever else looks.
XMP = (b'<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>'
       b'<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
       b'<rdf:Description rdf:about="" xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/" '
       b'Iptc4xmpExt:DigitalSourceType="http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"/>'
       b'</rdf:RDF></x:xmpmeta><?xpacket end="r"?>')

_known = None
_thumbs = (frozenset(), [])


def ensure_tables():
    session.execute(TABLE_DDL)


class Known:
    """The registry's hashes as one process last read them. Every listing asks,
    so this read stays small: the thumbnails are read apart, when compared."""

    def __init__(self, digests):
        self.read_at = time.monotonic()
        self.digests = frozenset(digests)


def known(fresh=False):
    global _known
    if fresh or _known is None or time.monotonic() - _known.read_at > FRESH_SECONDS:
        _known = Known(r.digest for r in session.execute('SELECT digest FROM ai_pictures'))
    return _known


def known_thumbnails():
    """Re-read only when the registry has changed."""
    global _thumbs
    digests = known().digests
    if _thumbs[0] != digests:
        distinct = {bytes(r.thumb) for r in session.execute('SELECT digest, thumb FROM ai_pictures')
                    if r.thumb and len(r.thumb) == SIDE * SIDE * 3}
        _thumbs = (digests, [Image.frombytes('RGB', (SIDE, SIDE), t) for t in distinct])
    return _thumbs[1]


def thumbnail(data):
    """16x16 RGB, or None when it's no picture or too plain to tell from another."""
    try:
        with Image.open(io.BytesIO(data)) as img:
            small = img.convert('RGB').resize((SIDE, SIDE), Image.BILINEAR)
    except Exception:  # noqa: BLE001 - Pillow raises many kinds
        return None
    if sum(ImageStat.Stat(small).stddev) / 3 < TOO_PLAIN:
        return None
    return small


def alike(one, other):
    return sum(ImageStat.Stat(ImageChops.difference(one, other)).mean) / 3 <= SAME_WITHIN


def declares_ai(data):
    """The file itself says a model made or altered it."""
    if b'trainedalgorithmicmedia' in data.lower():
        return True
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        return False
    try:
        with Image.open(io.BytesIO(data)) as img:
            info = dict(img.info)
    except Exception:  # noqa: BLE001
        return False
    return 'Steps:' in str(info.get('parameters', '')) or ('prompt' in info and 'workflow' in info)


def looks_ai(data):
    if not data:
        return False
    if declares_ai(data):
        return True
    if image_store.digest(data) in known().digests:
        return True
    small = thumbnail(data)
    return small is not None and any(alike(small, other) for other in known_thumbnails())


def key_digest(key):
    """The content hash in a bucket key (banners/<hash>.jpg)."""
    return key.rsplit('/', 1)[-1].split('.', 1)[0] if key else None


def is_ai_key(key):
    return bool(key) and key_digest(key) in known().digests


def is_ai_stored(data):
    """For a stored picture's bytes: their hash is what its key is named after."""
    return bool(data) and image_store.digest(data) in known().digests


def remember(data, source, key=None):
    digests = {image_store.digest(data), key_digest(key)} - {None}
    small = thumbnail(data)
    thumb = small.tobytes() if small is not None else None
    for digest in digests:
        session.execute('INSERT INTO ai_pictures (digest, thumb, source, made_at) VALUES (%s, %s, %s, %s)',
                        [digest, thumb, source, datetime.utcnow()])
    known(fresh=True)


def note_upload(data, key):
    """An uploaded picture that looks AI-made is remembered under the key it
    was stored with, so that it gets labelled and isn't copied into evidence."""
    if data and key and not is_ai_key(key) and looks_ai(data):
        remember(data, 'uploaded', key)


def adopt(raw, source='generated'):
    """A freshly generated picture as we hand it out: small, saying it is AI-made,
    and remembered. Small enough that storing keeps it byte for byte."""
    img = Image.open(io.BytesIO(raw)).convert('RGB')
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    img.save(out, 'JPEG', quality=80, optimize=True, progressive=True, xmp=XMP)
    data = out.getvalue()
    remember(data, source)
    return data
