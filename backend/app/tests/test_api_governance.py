# Liquid democracy: policies, proposals, weighted votes with delegation,
# automatic application of a passed policy, project phase enforcement.
import uuid
import pytest
from conftest import REPAIR_CAFE, TOOL_LIBRARY


def test_tally_weights_delegations_transitively_and_direct_vote_overrides():
    from app.models.governance import tally, passes
    a, b, c, d, e = (uuid.uuid4() for _ in range(5))
    members = [a, b, c, d, e]
    # a -> b -> c (c votes yes): c carries a and b.  d delegates to e; e votes no.
    counts = tally(members, {c: 'yes', e: 'no'}, {a: b, b: c, d: e})
    assert counts['yes'] == 3 and counts['no'] == 2 and counts['unrepresented'] == 0
    # b now votes directly -> overrides the delegation (a still flows to b, not c)
    counts = tally(members, {c: 'yes', e: 'no', b: 'abstain'}, {a: b, b: c, d: e})
    assert counts == {'yes': 1, 'no': 2, 'abstain': 2, 'eligible': 5, 'unrepresented': 0, 'direct_votes': 3}
    # cycles and non-members stop the chain -> unrepresented
    counts = tally([a, b], {}, {a: b, b: a})
    assert counts['unrepresented'] == 2
    assert passes({'yes': 3, 'no': 2}, 'majority') is True
    assert passes({'yes': 3, 'no': 2}, 'supermajority') is False
    assert passes({'yes': 4, 'no': 2}, 'supermajority') is True
    assert passes({'yes': 1, 'no': 1}, 'consensus') is False
    assert passes({'yes': 0, 'no': 0}, 'majority') is False


@pytest.fixture
def clean_alliance_governance(api, db):
    """David joins Repair Cafe as a plain member for the test (Joe is a platform
    admin, Marie a steward, Steve the Lead - none of them is 'just a member');
    afterwards remove him and any proposals/votes/delegations, and reset the
    alliance's policies."""
    api.post(f'/api/alliances/{REPAIR_CAFE}/join', who='david')
    yield
    aid = uuid.UUID(REPAIR_CAFE)
    api.post(f'/api/alliances/{REPAIR_CAFE}/members/{api.uid("david")}/role', who='joe', json={'role': 'remove'})
    for r in db.execute('SELECT proposal_id FROM governance_proposals WHERE entity_id = %s', [aid]):
        db.execute('DELETE FROM governance_votes WHERE proposal_id = %s', [r.proposal_id])
    db.execute('DELETE FROM governance_proposals WHERE entity_id = %s', [aid])
    db.execute('DELETE FROM governance_delegations WHERE entity_id = %s', [aid])
    db.execute("UPDATE alliances SET decision_policy = 'majority', confirm_policy = 'board', pm_policy = 'single-pm' WHERE alliance_id = %s", [aid])


def test_governance_view_is_members_only(api):
    status, body = api.get(f'/api/alliances/{REPAIR_CAFE}/governance', who='elon')
    assert status in (403, 404)
    status, g = api.get(f'/api/alliances/{REPAIR_CAFE}/governance', who='marie')
    assert status == 200
    assert set(g['policies']) == {'join_policy', 'decision_policy', 'pm_policy', 'confirm_policy'}
    assert g['is_member'] is True and g['my_delegate'] is None


def test_policy_proposal_lifecycle(api, clean_alliance_governance):
    """Steve (Lead), Joe (member), Marie (steward) are the three members.
    Joe delegates to Marie; Marie votes yes -> weight 2 vs Steve's no -> passes
    by majority and the policy is applied."""
    # Joe proposes confirm_policy -> any-member
    status, p = api.post(f'/api/alliances/{REPAIR_CAFE}/proposals', who='joe', json={
        'kind': 'policy', 'policy_key': 'confirm_policy', 'policy_value': 'any-member', 'days': 3})
    assert status == 201, p
    pid = p['proposal_id']
    assert p['status'] == 'open' and p['tally']['eligible'] == 4   # Steve, Joe, Marie + David for this test
    # proposing the current value is refused
    assert api.post(f'/api/alliances/{REPAIR_CAFE}/proposals', who='joe', json={
        'kind': 'policy', 'policy_key': 'confirm_policy', 'policy_value': 'board'})[0] == 400
    # Joe delegates to Marie
    status, body = api.post(f'/api/alliances/{REPAIR_CAFE}/delegation', who='joe', json={'delegate_id': api.uid('marie')})
    assert status == 200 and body['my_delegate']['name'] == 'Marie Kondo'
    assert api.post(f'/api/alliances/{REPAIR_CAFE}/delegation', who='joe', json={'delegate_id': api.uid('joe')})[0] == 400
    # Marie votes yes (weight 2), Steve isn't logged in here - so majority stands
    status, p = api.post(f'/api/alliances/{REPAIR_CAFE}/proposals/{pid}/vote', who='marie', json={'choice': 'yes'})
    assert status == 200 and p['tally']['yes'] == 2 and p['tally']['direct_votes'] == 1 and p['would_pass'] is True
    # Joe voting himself overrides his delegation
    status, p = api.post(f'/api/alliances/{REPAIR_CAFE}/proposals/{pid}/vote', who='joe', json={'choice': 'no'})
    assert status == 200 and p['tally'] == {**p['tally'], 'yes': 1, 'no': 1}
    assert p['would_pass'] is False
    status, p = api.post(f'/api/alliances/{REPAIR_CAFE}/proposals/{pid}/vote', who='joe', json={'choice': 'yes'})
    assert p['tally']['yes'] == 2
    # a non-member can't vote; a bad choice is rejected
    assert api.post(f'/api/alliances/{REPAIR_CAFE}/proposals/{pid}/vote', who='elon', json={'choice': 'yes'})[0] in (403, 404)
    assert api.post(f'/api/alliances/{REPAIR_CAFE}/proposals/{pid}/vote', who='joe', json={'choice': 'maybe'})[0] == 400
    # a plain member can't count early; the steward (manager) can
    assert api.post(f'/api/alliances/{REPAIR_CAFE}/proposals/{pid}/close', who='david')[0] == 403
    status, p = api.post(f'/api/alliances/{REPAIR_CAFE}/proposals/{pid}/close', who='marie')
    assert status == 200 and p['status'] == 'passed' and p['result']['yes'] == 2
    # ...and the policy was applied to the alliance
    _, a = api.get(f'/api/alliances/{REPAIR_CAFE}', who='joe')
    assert a['confirm_policy'] == 'any-member'
    # voting on a closed proposal is refused; it shows up as decided
    assert api.post(f'/api/alliances/{REPAIR_CAFE}/proposals/{pid}/vote', who='joe', json={'choice': 'no'})[0] == 409
    _, g = api.get(f'/api/alliances/{REPAIR_CAFE}/governance', who='joe')
    assert g['policies']['confirm_policy']['value'] == 'any-member'
    assert [x['status'] for x in g['proposals']] == ['passed']


def test_motion_and_withdraw(api, clean_alliance_governance):
    status, p = api.post(f'/api/alliances/{REPAIR_CAFE}/proposals', who='marie', json={
        'kind': 'motion', 'title': 'Hold the repair cafe on Sundays in winter', 'description': 'Fewer clashes.'})
    assert status == 201 and p['kind'] == 'motion'
    pid = p['proposal_id']
    assert api.post(f'/api/alliances/{REPAIR_CAFE}/proposals/{pid}/withdraw', who='david')[0] == 403   # not the proposer, not a manager
    status, p = api.post(f'/api/alliances/{REPAIR_CAFE}/proposals/{pid}/withdraw', who='marie')
    assert status == 200 and p['status'] == 'withdrawn'


def test_managers_can_set_policies_directly_and_they_are_validated(api, clean_alliance_governance):
    status, a = api.patch(f'/api/alliances/{REPAIR_CAFE}', who='marie', json={'decision_policy': 'consensus', 'pm_policy': 'board'})
    assert status == 200 and a['decision_policy'] == 'consensus' and a['pm_policy'] == 'board'
    assert api.patch(f'/api/alliances/{REPAIR_CAFE}', who='marie', json={'decision_policy': 'dictatorship'})[0] == 400
    # 'phase' is a project field: on an alliance it's ignored, so there's nothing to update
    assert api.patch(f'/api/alliances/{REPAIR_CAFE}', who='marie', json={'phase': 'closed'})[0] == 400
    # pm_policy='board' lets the Board manage the alliance's projects
    from app.utils.permissions import can_manage_entity, _alliance_by_name_cache
    _alliance_by_name_cache.clear()
    assert can_manage_entity(TOOL_LIBRARY, api.uid('marie')) is True   # steward, not a project manager
    api.patch(f'/api/alliances/{REPAIR_CAFE}', who='marie', json={'pm_policy': 'single-pm'})
    _alliance_by_name_cache.clear()
    # Marie is also a project contributor, never its manager -> no longer manages it
    assert can_manage_entity(TOOL_LIBRARY, api.uid('marie')) is False


@pytest.fixture
def reopen_project(api):
    yield
    api.patch(f'/api/projects/{TOOL_LIBRARY}', who='joe', json={'phase': 'ongoing'})


def test_closed_project_takes_no_openings(api, reopen_project):
    status, p = api.patch(f'/api/projects/{TOOL_LIBRARY}', who='joe', json={'phase': 'closed'})
    assert status == 200 and p['phase'] == 'closed'
    status, body = api.post('/api/openings', who='joe', json={
        'type': 'offer', 'title': 'x', 'project_name': 'Community Tool Library'})
    assert status == 409
    status, body = api.post('/api/openings', who='joe', json={
        'type': 'offer', 'title': 'x', 'acting_as_id': TOOL_LIBRARY})
    assert status == 409
    _, rows = api.get('/api/projects', who='joe')
    assert next(r for r in rows if r['project_id'] == TOOL_LIBRARY)['phase'] == 'closed'
