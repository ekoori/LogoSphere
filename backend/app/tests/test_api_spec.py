# The OpenAPI spec (LogoSphereAPI.yaml, at the repository root) must describe
# every API route and nothing that isn't one. It had drifted to documenting
# about half of them.
import re
from pathlib import Path

SPEC = Path(__file__).resolve().parents[3] / 'LogoSphereAPI.yaml'


def _spec_operations():
    ops, current = set(), None
    for line in SPEC.read_text(encoding='utf-8').splitlines():
        m = re.match(r'^  (/[^:\s]+):\s*$', line)
        if m:
            current = m.group(1)
            continue
        m = re.match(r'^    (get|post|put|patch|delete):\s*$', line)
        if m and current:
            ops.add((re.sub(r'\{[^}]+\}', '{}', current), m.group(1).upper()))
    return ops


def _app_operations(app):
    ops = set()
    for rule in app.url_map.iter_rules():
        if rule.rule.startswith('/api/'):
            path = re.sub(r'<[^>]+>', '{}', rule.rule)
            ops |= {(path, m) for m in rule.methods - {'OPTIONS', 'HEAD'}}
    return ops


def test_every_route_is_documented(app):
    missing = sorted(_app_operations(app) - _spec_operations())
    assert not missing, f'add these to LogoSphereAPI.yaml: {missing}'


def test_the_spec_documents_only_real_routes(app):
    stale = sorted(_spec_operations() - _app_operations(app))
    assert not stale, f'no longer routes - remove from LogoSphereAPI.yaml: {stale}'
