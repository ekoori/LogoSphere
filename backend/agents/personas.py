"""Who the personas are. personas.json holds each one's sheet (an everyday
neighbour drawn from their value cards and posts) and voice; their value
cards and memberships are read live from the platform."""
import json
from dataclasses import dataclass, field
from pathlib import Path

PATH = Path(__file__).with_name('personas.json')


@dataclass
class Persona:
    user_id: str
    name: str
    email: str
    sheet: str = ''
    voice: str = ''
    cards: list = field(default_factory=list)      # filled in live

    @property
    def first_name(self):
        return self.name.split()[0]


def load(path=PATH):
    if not Path(path).exists():
        return []
    return [Persona(**{k: v for k, v in p.items() if k in ('user_id', 'name', 'email', 'sheet', 'voice')})
            for p in json.loads(Path(path).read_text(encoding='utf-8'))]


def save(personas, path=PATH):
    Path(path).write_text(json.dumps(
        [{'user_id': p.user_id, 'name': p.name, 'email': p.email, 'sheet': p.sheet, 'voice': p.voice}
         for p in sorted(personas, key=lambda p: p.name)], indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
