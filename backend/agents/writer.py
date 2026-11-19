"""Claude writes the personas' words: openings, receipts, notes,
acknowledgements, and the one-off rewrites of placeholder demo text.

Every request carries the same guardrails and returns structured output
(a Pydantic model), so the caller gets fields, never prose to parse.
"""
import logging
from typing import Callable, List, Literal, Optional

import anthropic
from pydantic import BaseModel

from agents import config

log = logging.getLogger(__name__)

GUARDRAILS = """You write for the demo spheres of LogoSphere, a platform where neighbours share skills, tools and time without money, and afterwards record what each exchange meant to them.

Every member of a demo sphere is an AI persona: a fictional, everyday neighbour who happens to share a name with a well-known person. You write as one of them, in the first person, the way an ordinary neighbour writes on a community noticeboard.

- Never write as the famous person. Don't mention or hint at their real career, fame, money, companies, products, books, films, shows, public statements or private life.
- Nothing about real-world events, politics, religion, brands or products.
- Stay small, local and concrete: tools, gardens, repairs, food, lessons, errands, looking after one another.
- Plain, warm, specific words. No hashtags, emoji, clichés or exaggeration.
- Never mention AI, personas, demos, seeds, generators, prompts or these instructions.
- British spelling."""

FRANKL = ('creative: something made or given; experiential: something received or encountered; '
          'attitudinal: a stance taken in the face of a constraint')


class OpeningText(BaseModel):
    title: str
    description: str


class ReceiptText(BaseModel):
    text: str
    frankl_mode: Literal['creative', 'experiential', 'attitudinal']
    card_ids: List[str]


class NoteText(BaseModel):
    text: str
    card_ids: List[str]


class AckText(BaseModel):
    text: str


class RewrittenOpening(BaseModel):
    service_id: str
    title: str
    description: str


class RewriteBatch(BaseModel):
    items: List[RewrittenOpening]


class ExchangeText(BaseModel):
    title: str
    description: str


class PersonaSheet(BaseModel):
    sheet: str
    voice: str


class WriterError(Exception):
    """The API failed in a way worth retrying later."""


def persona_block(persona, sphere=None):
    lines = [f'You are {persona.name}. {persona.sheet}', f'How you write: {persona.voice}']
    if sphere:
        lines.append(f"Your sphere: {sphere.get('name')} - {sphere.get('description') or ''}".strip())
    return '\n'.join(lines)


def cards_block(cards):
    if not cards:
        return 'You have no value cards.'
    return 'Your value cards (id: title - what you care about):\n' + '\n'.join(
        f"- {c['card_id']}: {c.get('title') or ''} - {c.get('care_about') or ''}" for c in cards)


class Writer:
    """`usage` is called with (input_tokens, output_tokens) after each request."""

    def __init__(self, client=None, model=None, usage: Optional[Callable[[int, int], None]] = None):
        self.client = client or anthropic.Anthropic()
        self.model = model or config.TEXT_MODEL
        self.usage = usage

    def _ask(self, schema, prompt, max_tokens=4000):
        try:
            response = self.client.beta.messages.parse(
                model=self.model,
                max_tokens=max_tokens,
                system=GUARDRAILS,
                messages=[{'role': 'user', 'content': prompt}],
                output_format=schema,
                # Short everyday writing: keep the thinking short too.
                output_config={'effort': 'low'},
                # A policy decline is re-run on a fallback model in the same call.
                betas=['server-side-fallback-2026-07-01'],
                fallbacks='default',
            )
        except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError) as e:
            raise WriterError(str(e)) from e
        except anthropic.APIStatusError as e:
            # Out of credit is a billing state that will pass, not a bad request.
            if e.status_code >= 500 or 'credit balance' in str(e).lower():
                raise WriterError(str(e)) from e
            raise
        if self.usage and getattr(response, 'usage', None):
            self.usage(response.usage.input_tokens or 0, response.usage.output_tokens or 0)
        if response.stop_reason == 'refusal':
            log.warning('Declined: %s', getattr(response, 'stop_details', None))
            return None
        return response.parsed_output

    # ── What personas write as they act ──────────────────────────────────────
    def opening(self, persona, sphere, kind, project=None, recent=(), hint=''):
        where = f"in {sphere.get('name')}" + (f", for the project \"{project}\"" if project else '')
        avoid = '\n'.join(f'- {t}' for t in list(recent)[:12])
        prompt = (f"{persona_block(persona, sphere)}\n\n"
                  f"Post a new {'offer of help' if kind == 'offer' else 'request for help (a need)'} {where}. "
                  f"{hint}\n"
                  + (f"Recent openings here - don't repeat them:\n{avoid}\n" if avoid else '')
                  + "Return a title under 70 characters (no quotes) and a description of one to three sentences.")
        return self._ask(OpeningText, prompt)

    def receipt(self, persona, exchange, other_name, gave, cards):
        role = 'You gave' if gave else 'You received'
        prompt = (f"{persona_block(persona)}\n\n"
                  f"An exchange with {other_name} has finished: \"{exchange.get('title')}\" - "
                  f"{exchange.get('description') or ''}\n{role} in it.\n"
                  f"Write your receipt: one to three sentences on what it meant to you, concrete and personal. "
                  f"Pick the kind of meaning ({FRANKL}) and up to two of your value cards it expressed.\n"
                  f"{cards_block(cards)}")
        return self._ask(ReceiptText, prompt)

    def note(self, persona, exchange, other_name, gave, cards):
        role = 'You gave' if gave else 'You received'
        prompt = (f"{persona_block(persona)}\n\n"
                  f"You started this exchange with {other_name}, and it has finished: \"{exchange.get('title')}\" - "
                  f"{exchange.get('description') or ''}\n{role} in it.\n"
                  "Write your personal note on it: one to three sentences, warm and specific, "
                  "and up to two of your value cards it expressed.\n"
                  f"{cards_block(cards)}")
        return self._ask(NoteText, prompt)

    def acknowledgement(self, persona, exchange, parties):
        prompt = (f"{persona_block(persona)}\n\n"
                  f"Two neighbours, {parties}, finished an exchange: \"{exchange.get('title')}\" - "
                  f"{exchange.get('description') or ''}\n"
                  "Write a short public acknowledgement of it (one or two sentences), as a neighbour who noticed.")
        return self._ask(AckText, prompt)

    # ── One-off: give the demo real-sounding text ────────────────────────────
    def rewrite_openings(self, persona, sphere_by_id, items):
        listing = '\n'.join(
            f"- id {o['service_id']}: {o['type']} in {sphere_by_id.get(o.get('sphere_id'), {}).get('name', 'the neighbourhood')}"
            + (f", project \"{o['project_name']}\"" if o.get('project_name') else '')
            + f". Placeholder: {o.get('title')} / {o.get('description')}"
            for o in items)
        prompt = (f"{persona_block(persona)}\n\n"
                  "These openings of yours were placeholders. Rewrite each as the real post you would have "
                  "written: keep its kind (offer or need), its sphere and project, and roughly what it is "
                  "about, but make it specific and everyday. Vary them; no two alike.\n"
                  f"{listing}\n"
                  "Return one item per id: a title under 70 characters and a description of one to three sentences.")
        return self._ask(RewriteBatch, prompt, max_tokens=8000)

    def rewrite_exchange(self, persona, exchange, other_name):
        prompt = (f"{persona_block(persona)}\n\n"
                  f"An exchange of yours with {other_name} needs a proper write-up. "
                  f"What we know: {exchange.get('title')} / {exchange.get('description') or 'nothing more'}"
                  + (f" (project \"{exchange['project_name']}\")" if exchange.get('project_name') else '') + ".\n"
                  "Return a title under 70 characters and a description of one or two sentences saying what happened.")
        return self._ask(ExchangeText, prompt)

    def persona_sheet(self, name, cards, posts, spheres):
        prompt = (f"Describe the demo persona {name} as an everyday neighbour on LogoSphere.\n"
                  f"Spheres: {', '.join(spheres) or 'none'}\n"
                  + cards_block(cards) + "\n"
                  + ('Some of their posts:\n' + '\n'.join(f'- {p}' for p in posts[:8]) if posts else '')
                  + "\nReturn `sheet`: two or three sentences on what they do around the neighbourhood, what "
                  "they're good at and what they care about, grounded in their value cards and never in the "
                  "real person's fame; and `voice`: one sentence on how they write.")
        return self._ask(PersonaSheet, prompt)
