"""Pictures are labelled with their content (ETag): a client that already has
one gets a bodiless 304, and ?size= gives a smaller copy (app/utils/pictures)."""
import io

from PIL import Image


def test_a_picture_you_already_have_comes_back_not_modified(api):
    joe = api.uid('joe')
    first = api.client.get(f'/api/users/{joe}/avatar')
    assert first.status_code == 200 and first.headers.get('ETag'), first.headers
    assert 'stale-while-revalidate' in first.headers['Cache-Control']
    again = api.client.get(f'/api/users/{joe}/avatar', headers={'If-None-Match': first.headers['ETag']})
    assert again.status_code == 304 and not again.data
    assert again.headers['ETag'] == first.headers['ETag']


def test_a_small_copy_on_request(api):
    joe = api.uid('joe')
    full = api.client.get(f'/api/users/{joe}/avatar')
    small = api.client.get(f'/api/users/{joe}/avatar?size=160')
    assert small.status_code == 200
    if full.mimetype != 'image/svg+xml':               # a photo, not the initials
        assert max(Image.open(io.BytesIO(small.data)).size) <= 160
        assert small.headers['ETag'] != full.headers['ETag'] and len(small.data) < len(full.data)


def test_no_picture_is_a_404_not_an_empty_picture(api):
    status, _ = api.get('/api/openings/00000000-0000-0000-0000-000000000000/image')
    assert status == 404
