"""Settings, from the environment (backend/agents.env on the host)."""
import os


def _flag(name, default):
    return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def _int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


# Off unless switched on; and while on, only logging what it would do until
# dry run is switched off too.
ENABLED = _flag('AGENTS_ENABLED', False)
DRY_RUN = _flag('AGENTS_DRY_RUN', True)

API = os.environ.get('AGENTS_API', 'http://127.0.0.1:5000').rstrip('/')
POLL_SECONDS = _int('AGENTS_POLL_SECONDS', 30)

TEXT_MODEL = os.environ.get('AGENTS_TEXT_MODEL', 'claude-opus-5-5')
IMAGE_MODEL = os.environ.get('AGENTS_IMAGE_MODEL', 'gpt-image-1-mini')

# Cost guards.
DAILY_CLAUDE_CALLS = _int('AGENTS_DAILY_CLAUDE_CALLS', 150)
DAILY_IMAGES = _int('AGENTS_DAILY_IMAGES', 20)
PER_MEMBER_PER_HOUR = _int('AGENTS_PER_MEMBER_PER_HOUR', 3)
# Answers to one member's messages, all personas together, per day.
ANSWERS_PER_MEMBER_PER_DAY = _int('AGENTS_ANSWERS_PER_MEMBER_PER_DAY', 20)
IMAGE_SHARE = float(os.environ.get('AGENTS_IMAGE_SHARE', '0.33'))   # of persona-posted openings

# Persona-to-persona activity runs on credits that real activity creates.
RIPPLE_PER_REAL_ACTION = _int('AGENTS_RIPPLE_PER_REAL_ACTION', 3)
RIPPLE_CAP = _int('AGENTS_RIPPLE_CAP', 10)
RIPPLE_MINUTES = _int('AGENTS_RIPPLE_MINUTES', 60)
