# Every route that changes something refuses a request with no session, apart
# from the few meant for signed-out visitors. A decorator lost while editing
# (it happened once, caught before it shipped) fails here.
import re
import uuid

# Signed-out on purpose: joining, signing in, links from emails, invitation previews.
PUBLIC = {
    '/api/login', '/api/logout', '/api/register', '/api/register/confirm', '/api/password/forgot', '/api/password/reset',
    '/api/email/confirm', '/api/email/unsubscribe/<token>', '/api/invites/look',
    '/api/check_session',       # answers "inactive" to anyone, and changes nothing
}


def test_writes_need_a_session(app):
    client = app.test_client()
    open_doors = []
    for rule in app.url_map.iter_rules():
        methods = rule.methods & {'POST', 'PUT', 'PATCH', 'DELETE'}
        if not methods or not rule.rule.startswith('/api/') or rule.rule in PUBLIC:
            continue
        path = re.sub(r'<(?:[^:>]+:)?([^>]+)>', lambda m: '0' if m.group(1) == 'idx' else str(uuid.uuid4()), rule.rule)
        for method in sorted(methods):
            status = client.open(path, method=method, json={}).status_code
            if status != 401:
                open_doors.append((method, rule.rule, status))
    assert not open_doors, open_doors
