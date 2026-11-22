# Evidence (receipts' photos and exchanges' pictures) and AI.
#
# Evidence between real people is real: no AI pictures. Demo spheres are openly
# a playground of AI personas, so theirs may be AI-made. An exchange outside
# any sphere is real unless nobody real is in it (demo.exchange_is_demo).
from app.utils import access, ai_pictures, demo

REFUSAL = ('That picture looks AI-made. Receipts and exchanges in real spheres need real photos; '
           'AI pictures are for offers, needs and groups.')


def may_be_ai(exchange):
    """`exchange`: a meaning_trail row or a dict of one."""
    sphere = access.exchange_sphere(exchange)
    if sphere:
        return demo.is_demo_sphere(sphere)
    return demo.exchange_is_demo(exchange)


def refusal(exchange, images):
    """Why these can't be this exchange's evidence, or None."""
    given = [data for data in images if data]
    if not given:
        return None
    # The picture may have been drawn a second ago by another worker.
    ai_pictures.known(fresh=True)
    if any(ai_pictures.looks_ai(data) for data in given) and not may_be_ai(exchange):
        return REFUSAL
    return None


def inherited(exchange, key, data=None):
    """The opening's picture as a new exchange may take it: (key, bytes)."""
    if not key and not data:
        return None, None
    ai_pictures.known(fresh=True)
    made_by_ai = ai_pictures.is_ai_key(key) if key else ai_pictures.looks_ai(data)
    if made_by_ai and not may_be_ai(exchange):
        return None, None
    return key, data


def picture_state(exchange, key):
    """(may be shown, is AI-made) of an exchange's stored picture."""
    made_by_ai = ai_pictures.is_ai_key(key)
    return (not made_by_ai or may_be_ai(exchange)), made_by_ai


def photo_may_show(exchange, data):
    """A stored receipt photo, as it is served."""
    return not ai_pictures.is_ai_stored(data) or may_be_ai(exchange)
