"""Wrong passwords at sign-in, limited.

Counted for an address from one network, so nobody can lock someone out from
elsewhere, and for the network as a whole, against one password tried on many
addresses. A right password never counts. Hashed and forgotten after a quarter
of an hour, like the other allowances (app/utils/mailer.take).
"""
from app.utils import mailer

WINDOW = 15 * 60
PER_ADDRESS, PER_NETWORK = 10, 60       # a hall of people signing in together share a network
TOO_MANY = 'Too many wrong tries. Wait 15 minutes, or ask for a password reset link.'


def _allowances(email, address):
    net = mailer.network(address)
    return ((f'login:{net}:{email}', PER_ADDRESS), (f'login:{net}', PER_NETWORK))


def _used(name):
    return mailer.used(name)


def _count(name, most):
    mailer.take(name, most, WINDOW)


def too_many(email, address):
    return any(_used(name) >= most for name, most in _allowances(email, address))


def failed(email, address):
    for name, most in _allowances(email, address):
        _count(name, most)
