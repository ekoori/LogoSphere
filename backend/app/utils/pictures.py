"""HTTP responses for stored pictures (avatars, banners, exchange pictures,
receipt photos).

Each response is labelled with the picture's content (a strong ETag, the hash
its bucket key is named after), so a client that already holds it asks again
with If-None-Match and gets a bodiless 304. Clients keep a picture fresh for
five minutes, and browsers may show the copy they have while they check
(stale-while-revalidate). `?size=160|320|640` serves a smaller copy, made once
and cached (see image_store.scaled).
"""
from flask import Response, request

from app.utils import image_store

FRESH = 'max-age=300, stale-while-revalidate=86400'


def picture_response(data, private=False, ctype=None):
    """The response for one stored picture; a 404 when there is none.
    `private` for pictures behind a permission check (exchanges, receipts)."""
    if not data:
        return ('', 404)
    size = request.args.get('size', type=int)
    if size not in image_store.VARIANT_SIDES or ctype == 'image/svg+xml':
        size = None
    etag = image_store.digest(data) + (f'-{size}' if size else '')
    if request.if_none_match.contains_weak(etag):
        resp = Response(status=304)
    else:
        body, kind = image_store.scaled(data, size) if size else (data, ctype or image_store.sniff(data))
        resp = Response(body, mimetype=kind)
    resp.set_etag(etag)
    resp.headers['Cache-Control'] = f"{'private' if private else 'public'}, {FRESH}"
    return resp
