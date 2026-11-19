"""The personas' API client sends a request again when a restarting backend
drops it, as long as sending it twice can't do anything twice."""
import urllib.error

import pytest

from agents import platform
from agents.platform import Platform


class _Reply:
    headers = {'Content-Type': 'application/json'}

    def read(self):
        return b'{"ok": true}'

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _server(monkeypatch, *failures):
    """urlopen that raises `failures` in turn, then answers; returns the methods it saw."""
    seen, pending = [], list(failures)

    def urlopen(req, timeout):
        seen.append(req.get_method())
        if pending:
            raise pending.pop(0)
        return _Reply()
    monkeypatch.setattr(platform.urllib.request, 'urlopen', urlopen)
    monkeypatch.setattr(platform.time, 'sleep', lambda s: None)
    return seen


def _reset():
    return ConnectionResetError(104, 'Connection reset by peer')


def test_a_read_dropped_by_a_restarting_worker_is_sent_again(monkeypatch):
    seen = _server(monkeypatch, _reset())
    assert Platform('t', base='http://api').get('/api/notifications') == {'ok': True}
    assert seen == ['GET', 'GET']


def test_a_dropped_write_is_not_sent_twice(monkeypatch):
    seen = _server(monkeypatch, _reset())
    with pytest.raises(ConnectionResetError):
        Platform('t', base='http://api').post('/api/openings/x/like', {'liked': True})
    assert seen == ['POST']


def test_a_refused_write_never_arrived_so_it_is_sent_again(monkeypatch):
    seen = _server(monkeypatch, urllib.error.URLError(ConnectionRefusedError(111, 'Connection refused')))
    assert Platform('t', base='http://api').post('/api/openings/x/like', {}) == {'ok': True}
    assert seen == ['POST', 'POST']


def test_a_second_drop_is_reported(monkeypatch):
    seen = _server(monkeypatch, _reset(), _reset())
    with pytest.raises(ConnectionResetError):
        Platform('t', base='http://api').get('/api/notifications')
    assert seen == ['GET', 'GET']
