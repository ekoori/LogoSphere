"""Pictures are normalised on the way in, stored once under their content, and
read back from the local cache or the bucket (app/utils/image_store)."""
import io

import pytest
from PIL import Image

from app.utils import image_store
from conftest import PNG_1PX


def _jpeg(size, orientation=None):
    out = io.BytesIO()
    img = Image.new('RGB', size, 'red')
    if orientation:
        exif = Image.Exif()
        exif[0x0112] = orientation
        img.save(out, 'JPEG', quality=95, exif=exif.tobytes())
    else:
        img.save(out, 'JPEG', quality=95)
    return out.getvalue()


def test_a_small_picture_is_kept_byte_for_byte():
    assert image_store.normalise(PNG_1PX, 'banner') == (PNG_1PX, 'image/png')


def test_a_large_phone_photo_is_scaled_down_and_turned_upright():
    # Stored landscape; its EXIF says "turn 90 degrees clockwise to view".
    body, ctype = image_store.normalise(_jpeg((4000, 2000), orientation=6), 'avatar')
    img = Image.open(io.BytesIO(body))
    assert ctype == 'image/jpeg' and img.size == (400, 800)
    assert img.getexif().get(0x0112) in (None, 1)


def test_transparency_survives_as_webp():
    out = io.BytesIO()
    Image.new('RGBA', (3000, 1500), (0, 128, 0, 100)).save(out, 'PNG')
    body, ctype = image_store.normalise(out.getvalue(), 'banner')
    img = Image.open(io.BytesIO(body))
    assert ctype == 'image/webp' and img.size == (1600, 800) and img.mode == 'RGBA'


def test_what_does_not_open_is_refused():
    with pytest.raises(image_store.UnreadableImage):
        image_store.normalise(b'\x89PNG\r\n\x1a\n' + b'0' * 32)


class FakeBucket:
    def __init__(self):
        self.objects, self.gets = {}, 0

    def put_object(self, Bucket, Key, Body, ContentType, CacheControl):
        self.objects[Key] = (Body, ContentType, CacheControl)

    def get_object(self, Bucket, Key):
        self.gets += 1
        return {'Body': io.BytesIO(self.objects[Key][0])}      # KeyError when missing


@pytest.fixture
def bucket(monkeypatch, tmp_path):
    for k, v in {'S3_BUCKET': 'test-bucket', 'S3_ACCESS_KEY': 'k', 'S3_SECRET_KEY': 's',
                 'IMAGE_CACHE_DIR': str(tmp_path)}.items():
        monkeypatch.setenv(k, v)
    fake = FakeBucket()
    monkeypatch.setattr(image_store, '_client', fake)
    return fake


def test_a_picture_is_stored_once_under_its_content_and_read_back(bucket, tmp_path):
    key, blob = image_store.store(PNG_1PX, 'banner')
    assert blob is None and key.startswith('banners/') and key.endswith('.png')
    assert bucket.objects[key][0] == PNG_1PX and 'immutable' in bucket.objects[key][2]
    assert image_store.store(PNG_1PX, 'banner') == (key, None)       # the same picture, the same key
    assert image_store.fetch(key) == PNG_1PX and bucket.gets == 0     # from the local cache
    for f in tmp_path.rglob('*.png'):
        f.unlink()
    assert image_store.fetch(key) == PNG_1PX and bucket.gets == 1     # from the bucket, cached again
    assert image_store.fetch(key) == PNG_1PX and bucket.gets == 1


def test_a_missing_picture_is_none_not_an_error(bucket):
    assert image_store.fetch('banners/' + '0' * 32 + '.jpg') is None
    assert image_store.fetch('../../etc/passwd') is None              # only keys this store makes
    assert image_store.fetch(None, b'old blob') == b'old blob'


def test_without_a_bucket_the_row_keeps_the_picture(monkeypatch):
    monkeypatch.delenv('S3_BUCKET', raising=False)
    assert image_store.store(PNG_1PX, 'banner') == (None, PNG_1PX)
    assert image_store.store(None) == (None, None)
