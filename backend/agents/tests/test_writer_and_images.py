"""Writer and illustrator against fake API clients (no network, no credits)."""
import base64
import io
from types import SimpleNamespace

import anthropic
import pytest
from PIL import Image

from agents.images import Illustrator, shrink
from agents.personas import Persona
from agents.writer import GUARDRAILS, OpeningText, ReceiptText, Writer, WriterError

MARIE = Persona(user_id='u1', name='Marie Kondo', email='m@example.com',
                sheet='Marie keeps the Repair Café shelves in order.', voice='Calm and cheerful.')
CARDS = [{'card_id': 'c1', 'title': 'Intentional space', 'care_about': 'Keeping only what serves'}]


class FakeMessages:
    def __init__(self, result=None, stop='end_turn', error=None):
        self.calls, self.result, self.stop, self.error = [], result, stop, error

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(parsed_output=self.result, stop_reason=self.stop,
                               usage=SimpleNamespace(input_tokens=1200, output_tokens=150), stop_details=None)


def fake_client(**kw):
    messages = FakeMessages(**kw)
    return SimpleNamespace(beta=SimpleNamespace(messages=messages)), messages


def test_every_request_carries_the_guardrails_and_the_persona():
    client, messages = fake_client(result=OpeningText(title='Spare jars', description='Clean jars to give away.'))
    used = []
    w = Writer(client=client, model='claude-opus-5-5', usage=lambda i, o: used.append((i, o)))
    out = w.opening(MARIE, {'name': 'Riverside Commons', 'description': 'A neighbourhood'}, 'offer',
                    recent=['Old title'])
    call = messages.calls[0]
    assert out.title == 'Spare jars'
    assert call['system'] == GUARDRAILS and 'Never write as the famous person' in GUARDRAILS
    assert call['model'] == 'claude-opus-5-5' and call['output_format'] is OpeningText
    assert call['output_config'] == {'effort': 'low'} and call['fallbacks'] == 'default'
    prompt = call['messages'][0]['content']
    assert 'You are Marie Kondo' in prompt and 'Repair Café' in prompt and 'Old title' in prompt
    assert used == [(1200, 150)]


def test_a_receipt_is_offered_the_personas_own_value_cards():
    client, messages = fake_client(result=ReceiptText(text='Thank you.', frankl_mode='experiential', card_ids=['c1']))
    Writer(client=client).receipt(MARIE, {'title': 'Fence', 'description': 'Rebuilt it'}, 'Joe', False, CARDS)
    prompt = messages.calls[0]['messages'][0]['content']
    assert 'c1: Intentional space' in prompt and 'You received' in prompt


def test_a_refusal_writes_nothing():
    client, _ = fake_client(result=None, stop='refusal')
    assert Writer(client=client).opening(MARIE, {'name': 'X'}, 'need') is None


def test_rate_limits_and_outages_are_retried_later():
    request = SimpleNamespace(method='POST', url='https://api.anthropic.com/v1/messages')
    response = SimpleNamespace(status_code=429, headers={}, request=request)
    err = anthropic.RateLimitError.__new__(anthropic.RateLimitError)
    Exception.__init__(err, 'rate limited')
    err.response, err.status_code = response, 429
    client, _ = fake_client(error=err)
    with pytest.raises(WriterError):
        Writer(client=client).opening(MARIE, {'name': 'X'}, 'need')


def _png(w, h):
    buf = io.BytesIO()
    Image.new('RGB', (w, h), (120, 160, 90)).save(buf, 'PNG')
    return buf.getvalue()


def test_banners_are_shrunk_to_a_small_jpeg():
    out = shrink(_png(1536, 1024))
    img = Image.open(io.BytesIO(out))
    assert img.format == 'JPEG' and img.size[0] <= 1280 and img.size[1] <= 720


def test_the_illustrator_asks_for_no_people_and_no_text():
    calls = []

    def generate(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(data=[SimpleNamespace(b64_json=base64.b64encode(_png(1536, 1024)).decode())])

    client = SimpleNamespace(images=SimpleNamespace(generate=generate))
    data = Illustrator(client=client, model='gpt-image-1-mini').banner('Loppers to lend')
    assert data[:3] == b'\xff\xd8\xff'                       # a JPEG
    c = calls[0]
    assert c['model'] == 'gpt-image-1-mini' and c['quality'] == 'low'
    assert 'No people' in c['prompt'] and 'No text' in c['prompt'] and 'Loppers to lend' in c['prompt']


def test_running_out_of_credit_is_retried_later_not_dropped():
    request = SimpleNamespace(method='POST', url='https://api.anthropic.com/v1/messages')
    response = SimpleNamespace(status_code=400, headers={}, request=request)
    err = anthropic.BadRequestError.__new__(anthropic.BadRequestError)
    Exception.__init__(err, 'Your credit balance is too low to access the Anthropic API.')
    err.response, err.status_code = response, 400
    client, _ = fake_client(error=err)
    with pytest.raises(WriterError):
        Writer(client=client).opening(MARIE, {'name': 'X'}, 'need')
