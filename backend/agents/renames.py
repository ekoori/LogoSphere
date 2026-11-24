"""The demo personas' names since 2026-11-25: each real person's name one letter off ("Jo Rodan"),
as Igor chose for Google Play's impersonation rules. Used by rename_personas.py (the database) and
kept as the record of who was whom; their pictures stayed."""

NAMES = {
    'Barack Obama': 'Barack Obana',
    'Bill Gates': 'Bill Gales',
    'David Attenborough': 'David Attenbarough',
    'Elon Musk': 'Elon Mask',
    'Emma Watson': 'Emma Wotson',
    'J.K. Rowling': 'J.K. Bowling',
    'James Cameron': 'James Cameran',
    'Jeff Bezos': 'Jeff Belos',
    'Jeff Goldblum': 'Jeff Goldblun',
    'Joe Rogan': 'Jo Rodan',
    'Jordan Peterson': 'Jordan Petersen',
    'Marie Kondo': 'Marie Konda',
    'Morgan Freeman': 'Morgan Treeman',
    'Neil deGrasse Tyson': 'Neil deGrasse Tison',
    'Oprah Winfrey': 'Oprah Winfree',
    'Pope Francis': 'Pope Frankis',
    'Quentin Tarantino': 'Quentin Tarantina',
    'Richard Branson': 'Richard Bramson',
    'Stephen Hawking': 'Stephen Hawkins',
    'Steve Wozniak': 'Steve Wozniac',
}

# Their sign-in addresses (example.com: no mailbox anywhere), by the same letters.
EMAILS = {
    'barack.obama@example.com': 'barack.obana@example.com',
    'bill.gates@example.com': 'bill.gales@example.com',
    'david.attenborough@example.com': 'david.attenbarough@example.com',
    'elon.musk@example.com': 'elon.mask@example.com',
    'emma.watson@example.com': 'emma.wotson@example.com',
    'jk.rowling@example.com': 'jk.bowling@example.com',
    'james.cameron@example.com': 'james.cameran@example.com',
    'jeff.bezos@example.com': 'jeff.belos@example.com',
    'jeff.goldblum@example.com': 'jeff.goldblun@example.com',
    'joe.rogan@example.com': 'jo.rodan@example.com',
    'jordan.peterson@example.com': 'jordan.petersen@example.com',
    'marie.kondo@example.com': 'marie.konda@example.com',
    'morgan.freeman@example.com': 'morgan.treeman@example.com',
    'neil.tyson@example.com': 'neil.tison@example.com',
    'oprah.winfrey@example.com': 'oprah.winfree@example.com',
    'pope.francis@example.com': 'pope.frankis@example.com',
    'quentin.tarantino@example.com': 'quentin.tarantina@example.com',
    'richard.branson@example.com': 'richard.bramson@example.com',
    'stephen.hawking@example.com': 'stephen.hawkins@example.com',
    'steve.wozniak@example.com': 'steve.wozniac@example.com',
}


def renamed(text):
    """Full names and addresses replaced (addresses whatever their case); anything else left alone."""
    if not isinstance(text, str):
        return text
    for old, new in NAMES.items():
        text = text.replace(old, new)
    lowered = text.lower()
    for old, new in EMAILS.items():
        start = lowered.find(old)
        while start != -1:
            text = text[:start] + new + text[start + len(old):]
            lowered = text.lower()
            start = lowered.find(old, start + len(new))
    return text
