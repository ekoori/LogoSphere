# How much of LogoSphere a member wants to see: Simple (the gift economy, with
# fewer options) or Advanced (everything). Only how the clients present things:
# never a permission, so no route may ever check it.
from app.db import session
from app.utils.access import as_uuid

SIMPLE, ADVANCED = 'simple', 'advanced'
MODES = (SIMPLE, ADVANCED)

UI_MODE_DDL = 'ALTER TABLE users ADD IF NOT EXISTS ui_mode text'


def ensure_tables():
    session.execute(UI_MODE_DDL)


def mode_of(stored):
    """New accounts are given Simple. Accounts from before there was a choice
    have nothing stored and keep seeing everything."""
    return stored if stored in MODES else ADVANCED


def set_mode(user_id, mode):
    session.execute('UPDATE users SET ui_mode = %s WHERE user_id = %s', [mode, as_uuid(user_id)])
