# AI help, and AI's place in evidence: pictures for offers, needs and groups;
# never evidence in a real sphere; demo spheres' evidence may be AI-made.
# The providers are stand-ins here: no network, no credits.
import base64
import io
import os
import random
import uuid
from types import SimpleNamespace

import pytest
from PIL import Image

from conftest import RIVERSIDE


def picture(size=(960, 640), fmt='JPEG'):
    """A picture unlike any other: big random blocks."""
    img = Image.frombytes('RGB', (8, 8), bytes(random.getrandbits(8) for _ in range(192))).resize(size, Image.NEAREST)
    out = io.BytesIO()
    img.save(out, fmt)
    return out.getvalue()


def reencoded(data, side=500):
    img = Image.open(io.BytesIO(data)).convert('RGB')
    img.thumbnail((side, side))
    out = io.BytesIO()
    img.save(out, 'JPEG', quality=70)
    return out.getvalue()


def multipart(field, *pictures):
    return {field: [(io.BytesIO(p), f'picture{i}.jpg') for i, p in enumerate(pictures)]}


def send(api, path, who, data):
    r = api.client.post(path, headers=api._hdr(who), data=data, content_type='multipart/form-data')
    return r.status_code, r.get_json(silent=True)


@pytest.fixture(autouse=True)
def bucket(app, monkeypatch, tmp_path):
    """Test pictures never reach the real bucket."""
    from app.utils import image_store
    held = {}

    class Fake:
        def put_object(self, Key, Body, **_):
            held[Key] = Body

        def get_object(self, Key, **_):
            return {'Body': io.BytesIO(held[Key])}

    monkeypatch.setattr(image_store, '_s3', lambda: Fake())
    for name in ('S3_BUCKET', 'S3_ACCESS_KEY', 'S3_SECRET_KEY'):
        monkeypatch.setenv(name, 'test')
    monkeypatch.setenv('IMAGE_CACHE_DIR', str(tmp_path))
    return held


@pytest.fixture(autouse=True)
def registry(app, db):
    """What a test remembers as AI-made is forgotten afterwards."""
    from app.utils import ai_pictures
    before = {r.digest for r in db.execute('SELECT digest FROM ai_pictures')}
    yield
    for r in list(db.execute('SELECT digest FROM ai_pictures')):
        if r.digest not in before:
            db.execute('DELETE FROM ai_pictures WHERE digest = %s', [r.digest])
    ai_pictures.known(fresh=True)


@pytest.fixture
def ai_picture(app):
    from app.utils import ai_pictures
    return ai_pictures.adopt(picture())


# -- Knowing an AI picture ----------------------------------------------------
def test_our_pictures_say_what_they_are_and_survive_reencoding(ai_picture):
    from app.utils import ai_pictures, image_store
    assert ai_pictures.declares_ai(ai_picture)
    assert image_store.normalise(ai_picture)[0] == ai_picture        # stored as it came, so its key is known
    copy = reencoded(ai_picture)
    assert not ai_pictures.declares_ai(copy) and ai_pictures.looks_ai(copy)


def test_photos_and_plain_pictures_are_left_alone(ai_picture):
    from app.utils import ai_pictures
    assert not any(ai_pictures.looks_ai(picture()) for _ in range(8))
    plain = io.BytesIO()
    Image.new('RGB', (400, 300), (120, 120, 118)).save(plain, 'JPEG')
    assert not ai_pictures.looks_ai(plain.getvalue())
    assert not ai_pictures.looks_ai(b'not a picture at all')


def test_files_that_declare_ai_are_believed(app):
    from PIL.PngImagePlugin import PngInfo
    from app.utils import ai_pictures
    info = PngInfo()
    info.add_text('parameters', 'a shed\nSteps: 20, Sampler: Euler')
    out = io.BytesIO()
    Image.open(io.BytesIO(picture())).save(out, 'PNG', pnginfo=info)
    assert ai_pictures.looks_ai(out.getvalue())
    assert ai_pictures.looks_ai(picture() + b'...compositeWithTrainedAlgorithmicMedia...')


# -- Evidence -----------------------------------------------------------------
def make_exchange(api, db, sphere, giver, receiver, banner):
    status, body = api.post('/api/openings', who=giver, json={
        'type': 'offer', 'title': 'AI evidence test', 'sphere_id': sphere})
    assert status == 201, body
    oid = body['service_id']
    assert send(api, f'/api/openings/{oid}/image', giver, multipart('image', banner))[0] == 200
    assert api.post(f'/api/openings/{oid}/accept', who=receiver, json={})[0] == 200
    status, body = api.post(f'/api/openings/{oid}/confirm', who=giver, json={'accepter_id': api.uid(receiver)})
    assert status == 200, body
    return oid, body['exchange_id']


def drop_exchange(api, db, oid, xid, giver):
    o, x = uuid.UUID(oid), uuid.UUID(xid)
    db.execute('DELETE FROM meaning_trail WHERE user_id = %s AND exchange_id = %s', [uuid.UUID(api.uid(giver)), x])
    db.execute('DELETE FROM receipt_photos WHERE exchange_id = %s', [x])
    for table in ('services', 'opening_acceptances', 'opening_likes'):
        db.execute(f'DELETE FROM {table} WHERE service_id = %s', [o])


@pytest.fixture
def real_exchange(api, db, ai_picture):
    """The throwaway admin gives to Marie in a sphere that isn't a demo."""
    status, s = api.post('/api/spheres', who='admin', json={'name': 'AI evidence test sphere (delete me)', 'description': 'x'})
    assert status == 201, s
    sid = s['sphere_id']
    made = None
    try:
        assert api.post(f'/api/spheres/{sid}/join', who='marie')[0] == 200
        made = make_exchange(api, db, sid, 'admin', 'marie', ai_picture)
        yield made
    finally:
        if made:
            drop_exchange(api, db, *made, giver='admin')
        db.execute('DELETE FROM spheres WHERE sphere_id = %s', [uuid.UUID(sid)])


@pytest.fixture
def demo_exchange(api, db, ai_picture):
    """David gives to Marie in Riverside, a demo sphere."""
    made = make_exchange(api, db, RIVERSIDE, 'david', 'marie', ai_picture)
    yield made
    drop_exchange(api, db, *made, giver='david')


def test_a_real_exchange_takes_no_ai_evidence(api, real_exchange, ai_picture):
    oid, xid = real_exchange
    status, opening = api.get(f'/api/openings/{oid}', who='admin')
    assert status == 200 and opening['has_image'] and opening['image_is_ai'] is True
    x = api.get(f'/api/exchange/{xid}', who='marie')[1]['exchange']
    assert x['has_image'] is False                       # the offer's AI picture didn't come along

    photos = f'/api/exchange/{xid}/receipt_photos'
    for fake in (ai_picture, reencoded(ai_picture)):
        status, body = send(api, photos, 'marie', multipart('photos', picture(), fake))
        assert status == 400 and 'AI' in body['message']
    assert send(api, photos, 'marie', multipart('photos', picture()))[0] == 200

    edit = f'/api/exchange/{xid}/edit'
    assert send(api, edit, 'admin', multipart('image', ai_picture))[0] == 400
    assert send(api, edit, 'admin', multipart('image', picture()))[0] == 200
    x = api.get(f'/api/exchange/{xid}', who='admin')[1]['exchange']
    assert x['has_image'] is True and x['image_is_ai'] is False


def test_a_demo_spheres_evidence_may_be_ai(api, demo_exchange, ai_picture):
    oid, xid = demo_exchange
    x = api.get(f'/api/exchange/{xid}', who='marie')[1]['exchange']
    assert x['has_image'] is True and x['image_is_ai'] is True
    assert send(api, f'/api/exchange/{xid}/receipt_photos', 'marie', multipart('photos', ai_picture))[0] == 200
    assert api.client.get(f'/api/exchange/{xid}/receipt_photo/0', headers=api._hdr('marie')).status_code == 200
    assert send(api, f'/api/exchange/{xid}/edit', 'david', multipart('image', ai_picture))[0] == 200


def test_a_sphere_that_stops_being_a_demo_stops_showing_ai_evidence(api, db, demo_exchange, ai_picture, keep_rows):
    from app.utils import demo
    _, xid = demo_exchange
    assert send(api, f'/api/exchange/{xid}/receipt_photos', 'marie', multipart('photos', ai_picture))[0] == 200
    keep_rows('spheres', sphere_id=RIVERSIDE)
    try:
        db.execute('UPDATE spheres SET is_demo = false WHERE sphere_id = %s', [uuid.UUID(RIVERSIDE)])
        demo.forget()
        assert api.get(f'/api/exchange/{xid}', who='marie')[1]['exchange']['has_image'] is False
        for path in ('image', 'receipt_photo/0'):
            assert api.client.get(f'/api/exchange/{xid}/{path}', headers=api._hdr('marie')).status_code == 404
    finally:
        db.execute('UPDATE spheres SET is_demo = true WHERE sphere_id = %s', [uuid.UUID(RIVERSIDE)])
        demo.forget()


# -- Asking for help ----------------------------------------------------------
@pytest.fixture
def asked(api, monkeypatch):
    """AI help switched on with stand-in providers; what they were sent."""
    from app.utils import assist
    monkeypatch.delenv('AI_ASSIST', raising=False)
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-key')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    sent = SimpleNamespace(material=[], prompts=[], fail=None)

    def claude(key, material):
        sent.material.append(material)
        if sent.fail:
            raise sent.fail
        return assist.CardDraft(
            title='Mending  first', care_about='I care about fixing what is broken.', because='Waste hurts.',
            looks_like=['Asking who can fix it', ''], drift_looks_like='Buying new', in_conflict='Patience',
            never_do='Bin what works', frankl_mode='creative', question='Is it the thing, or the people?')

    def openai(key, prompt):
        sent.prompts.append(prompt)
        if sent.fail:
            raise sent.fail
        return picture((1536, 1024))

    monkeypatch.setattr(assist, 'ask_claude', claude)
    monkeypatch.setattr(assist, 'ask_openai', openai)
    assist.forget(api.uid('marie'))
    yield sent
    assist.forget(api.uid('marie'))


def test_card_help_sends_only_what_was_typed(api, asked):
    status, body = api.post('/api/ai/value_card', who='marie', json={
        'notes': 'I hate throwing things out',
        'draft': {'title': 'Mending', 'user_id': 'not-for-sending'},
        'email': 'not-for-sending@example.com'})
    assert status == 200, body
    assert body['draft']['title'] == 'Mending first' and body['draft']['looks_like'] == ['Asking who can fix it']
    assert body['question']
    sent = asked.material[0]
    assert set(sent) == {'card_is_for', 'brief_card', 'notes', 'draft_so_far'}
    assert sent['draft_so_far'] == {'title': 'Mending'}
    assert 'not-for-sending' not in str(sent) and api.uid('marie') not in str(sent) and 'Marie' not in str(sent)


def test_a_brief_card_brings_nothing_the_member_cannot_see(api, asked):
    status, body = api.post('/api/ai/value_card', who='marie', json={'notes': 'mending', 'brief': True})
    assert status == 200 and set(body['draft']) == {'title', 'care_about', 'because'}
    assert api.post('/api/ai/value_card', who='marie', json={'notes': '  '})[0] == 400


def test_a_days_help_is_limited_and_failures_are_given_back(api, asked, monkeypatch):
    from app.utils import assist
    monkeypatch.setitem(assist.DAILY, assist.CARDS, (2, 10 ** 6))

    def ask():
        return api.post('/api/ai/value_card', who='marie', json={'notes': 'mending'})[0]

    def remaining():
        return api.get('/api/ai', who='marie')[1]['value_cards']['left']

    assert remaining() == 2
    asked.fail = assist.AssistError()
    assert ask() == 503 and remaining() == 2             # it failed her: given back
    asked.fail = assist.Declined()
    assert ask() == 422 and remaining() == 1             # it answered, and was paid for
    asked.fail = None
    assert ask() == 200 and remaining() == 0
    assert ask() == 429


def test_everyone_together_has_a_limit_too(api, asked, monkeypatch):
    from app.utils import assist
    monkeypatch.setitem(assist.DAILY, assist.CARDS, (99, 0))
    assert api.post('/api/ai/value_card', who='marie', json={'notes': 'mending'})[0] == 429


def test_a_picture_comes_back_marked_and_unsaved(api, asked, bucket):
    from app.utils import ai_pictures
    status, body = api.post('/api/ai/picture', who='marie', json={
        'purpose': 'opening', 'title': 'Loppers to lend', 'hint': 'autumn light'})
    assert status == 200, body
    data = base64.b64decode(body['image'])
    assert ai_pictures.declares_ai(data) and ai_pictures.is_ai_stored(data)
    assert bucket == {}                                  # saving is the member's step
    assert 'Loppers to lend' in asked.prompts[0] and api.uid('marie') not in asked.prompts[0]


def test_ai_never_draws_a_receipt(api, asked):
    for purpose in ('receipt', 'exchange', 'evidence', None, ['opening']):
        assert api.post('/api/ai/picture', who='marie', json={'purpose': purpose, 'title': 'x'})[0] == 400
    assert asked.prompts == []


def test_off_is_off(api, asked, monkeypatch):
    monkeypatch.setenv('AI_ASSIST', 'off')
    assert api.get('/api/ai', who='marie')[1]['pictures']['on'] is False
    assert api.post('/api/ai/value_card', who='marie', json={'notes': 'mending'})[0] == 503
    assert asked.material == []


def test_ai_help_is_for_members(app):
    c = app.test_client()
    assert c.get('/api/ai').status_code == 401
    assert c.post('/api/ai/value_card', json={'notes': 'x'}).status_code == 401
    assert c.post('/api/ai/picture', json={'purpose': 'opening', 'title': 'x'}).status_code == 401


def test_claude_is_asked_as_configured(app, monkeypatch):
    from app.utils import assist
    seen = {}
    answer = SimpleNamespace(stop_reason='end_turn', parsed_output='draft')

    def parse(**kw):
        seen.update(kw)
        return answer

    fake = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(parse=parse)))
    monkeypatch.setattr(assist, '_claude', lambda key: fake)
    assert assist.ask_claude('k', {'notes': 'mending'}) == 'draft'
    assert seen['model'] == assist.TEXT_MODEL and seen['output_format'] is assist.CardDraft
    assert seen['output_config'] == {'effort': 'low'} and seen['fallbacks'] == 'default'
    assert 'thinking' not in seen
    answer.stop_reason, answer.parsed_output = 'refusal', None
    with pytest.raises(assist.Declined):
        assist.ask_claude('k', {'notes': 'x'})


def test_a_whole_card_comes_back_with_every_field(api, asked):
    from app.utils import assist
    status, body = api.post('/api/ai/value_card', who='marie', json={'notes': 'I fix bikes so nobody buys new'})
    assert status == 200, body
    assert set(body['draft']) == {'title', 'care_about', 'because', 'looks_like', 'drift_looks_like', 'in_conflict',
                                  'never_do', 'frankl_mode'}
    assert all(body['draft'].values())
    # Asked to suggest every field, not to leave blanks for people to fill.
    assert 'fill in every field' in assist.CARD_SYSTEM and 'empty rather than guess' not in assist.CARD_SYSTEM
