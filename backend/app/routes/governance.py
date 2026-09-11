# File: ./backend/app/routes/governance.py
# Description: Liquid-democracy endpoints, mounted for every entity kind:
#
#   GET  /api/<kind>s/<id>/governance                     policies, proposals (with live tallies), my delegation
#   POST /api/<kind>s/<id>/proposals                      propose a policy change or a motion (members)
#   POST /api/<kind>s/<id>/proposals/<pid>/vote           {choice: yes|no|abstain} (members)
#   POST /api/<kind>s/<id>/proposals/<pid>/close          count now (managers; also happens at the deadline)
#   POST /api/<kind>s/<id>/proposals/<pid>/withdraw       proposer takes it back
#   POST /api/<kind>s/<id>/delegation                     {delegate_id | null} (members)
import logging
import uuid
from datetime import datetime

from flask import request, jsonify, current_app as app

from app.db import session
from app.models.governance import (Governance, tally, passes, CHOICES, PROPOSAL_KINDS,
                                   VOTABLE_POLICIES, POLICY_LABELS, DECISION_POLICIES, DEFAULT_DAYS, MAX_DAYS)
from app.models.notification import Notification
from app.models.user import User
from app.routes.entities import KINDS, _members, _kind
from app.utils.names import resolve_user_names
from app.utils.permissions import can_manage_entity, is_platform_admin
from app.middleware.session_middleware import validate_session

logger = logging.getLogger(__name__)


def _load(kind, entity_id, user_id):
    """(k, entity, viewer, members) or an error response tuple."""
    k = _kind(kind)
    eid = uuid.UUID(str(entity_id))
    viewer = uuid.UUID(str(user_id))
    entity = k['model'].get_by_id(eid)
    if not entity:
        return None, (jsonify({'message': f'{k["noun"].capitalize()} not found'}), 404)
    members = _members(entity, k)
    if viewer not in members and not is_platform_admin(viewer):
        return None, (jsonify({'message': f'Only members take part in this {k["noun"]}\'s governance'}), 403)
    return (k, entity, viewer, members), None


def _policies(entity, kind):
    keys = VOTABLE_POLICIES[kind]
    out = {}
    for key in keys:
        val = getattr(entity, key, None)
        if isinstance(val, bool):
            val = 'true' if val else 'false'
        out[key] = {'value': val, 'label': POLICY_LABELS[key], 'options': list(keys[key])}
    return out


def _apply_policy(k, entity, key, value):
    """Write a passed policy proposal onto the entity row."""
    eid = getattr(entity, k['id_col'])
    if key == 'is_public':
        session.execute(f"UPDATE {k['table']} SET is_public = %s WHERE {k['id_col']} = %s", [value == 'true', eid])
    else:
        session.execute(f"UPDATE {k['table']} SET {key} = %s WHERE {k['id_col']} = %s", [value, eid])


def _settle(k, entity, members, p):
    """Count a proposal now (deadline reached or manager closed it). Applies a
    passed policy change. Returns the updated proposal dict."""
    eid = getattr(entity, k['id_col'])
    pid = uuid.UUID(p['proposal_id'])
    counts = tally(members, Governance.votes(pid), Governance.delegations(eid))
    ok = passes(counts, p.get('decision_policy') or 'majority')
    Governance.close_proposal(eid, pid, 'passed' if ok else 'rejected', counts)
    if ok and p['kind'] == 'policy' and p.get('policy_key'):
        _apply_policy(k, entity, p['policy_key'], p['policy_value'])
    return Governance.proposal(eid, pid)


def _with_tally(k, entity, members, viewer, p):
    eid = getattr(entity, k['id_col'])
    pid = uuid.UUID(p['proposal_id'])
    votes = Governance.votes(pid)
    if p['status'] == 'open' and p.get('closes_at') and datetime.fromisoformat(p['closes_at']) <= datetime.utcnow():
        p = _settle(k, entity, members, p)
    if p['status'] == 'open':
        p['tally'] = tally(members, votes, Governance.delegations(eid))
        p['would_pass'] = passes(p['tally'], p.get('decision_policy') or 'majority')
    else:
        p['tally'] = p.get('result')
    p['my_vote'] = votes.get(viewer)
    return p


@validate_session
def get_governance(kind, entity_id, user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        loaded, err = _load(kind, entity_id, user_id)
        if err:
            return err
        k, entity, viewer, members = loaded
        eid = getattr(entity, k['id_col'])
        delegations = Governance.delegations(eid)
        names = resolve_user_names(set(members) | set(delegations.values()) | set(delegations.keys()))
        proposals = [_with_tally(k, entity, members, viewer, p) for p in Governance.proposals(eid)]
        for p in proposals:
            p['created_by_name'] = names.get(uuid.UUID(p['created_by']), 'Member') if p.get('created_by') else None
        my_delegate = delegations.get(viewer)
        return jsonify({
            'kind': kind,
            'entity_id': str(eid),
            'decision_policy': getattr(entity, 'decision_policy', None) or 'majority',
            'policies': _policies(entity, kind),
            'can_manage': can_manage_entity(eid, viewer),
            'is_member': viewer in members,
            'members': [{'id': str(m), 'name': names.get(m, 'Member')} for m in members],
            'my_delegate': {'id': str(my_delegate), 'name': names.get(my_delegate, 'Member')} if my_delegate else None,
            'delegated_to_me': [{'id': str(d), 'name': names.get(d, 'Member')}
                                for d, t in delegations.items() if t == viewer],
            'proposals': proposals,
        }), 200
    except (KeyError, ValueError):
        return jsonify({'message': 'Not found'}), 404
    except Exception as e:
        logger.error(f"Error in get_governance({kind}): {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def create_proposal(kind, entity_id, user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        loaded, err = _load(kind, entity_id, user_id)
        if err:
            return err
        k, entity, viewer, members = loaded
        if viewer not in members:
            return jsonify({'message': 'Only members can make proposals'}), 403
        data = request.get_json(silent=True) or {}
        pkind = data.get('kind', 'motion')
        if pkind not in PROPOSAL_KINDS:
            return jsonify({'message': 'kind must be "policy" or "motion"'}), 400
        title = (data.get('title') or '').strip()
        description = (data.get('description') or '').strip()
        key = value = None
        if pkind == 'policy':
            key, value = data.get('policy_key'), data.get('policy_value')
            allowed = VOTABLE_POLICIES[kind]
            if key not in allowed:
                return jsonify({'message': f'Unknown policy for a {k["noun"]}'}), 400
            if str(value) not in allowed[key]:
                return jsonify({'message': f'{POLICY_LABELS[key]} must be one of: {", ".join(allowed[key])}'}), 400
            value = str(value)
            current = getattr(entity, key, None)
            if isinstance(current, bool):
                current = 'true' if current else 'false'
            if (current or ('open' if key == 'join_policy' else None)) == value:
                return jsonify({'message': 'That is already the current setting'}), 400
            if not title:
                title = f'{POLICY_LABELS[key]}: {value.replace("-", " ")}'
        if not title:
            return jsonify({'message': 'A title is required'}), 400
        try:
            days = int(data.get('days') or DEFAULT_DAYS)
        except (TypeError, ValueError):
            days = DEFAULT_DAYS
        days = max(1, min(MAX_DAYS, days))
        p = Governance.create_proposal(
            getattr(entity, k['id_col']), viewer, pkind, title, description,
            policy_key=key, policy_value=value, days=days,
            decision_policy=getattr(entity, 'decision_policy', None) or 'majority')
        # Let every other member know there's something to vote on (best effort).
        try:
            actor = User.get(str(viewer))
            actor_name = (f"{actor.name or ''} {actor.surname or ''}".strip() or actor.email) if actor else 'A member'
            for m in members:
                if m != viewer:
                    Notification.create(
                        user_id=m, actor_id=viewer, actor_name=actor_name, type_='proposal_opened',
                        message=f'New proposal in {entity.name}: "{title}"',
                        link=f'/{kind}?id={getattr(entity, k["id_col"])}&tab=governance')
        except Exception as e:
            logger.warning(f'proposal notifications failed: {e}')
        p = _with_tally(k, entity, members, viewer, p)
        return jsonify(p), 201
    except (KeyError, ValueError):
        return jsonify({'message': 'Not found'}), 404
    except Exception as e:
        logger.error(f"Error in create_proposal({kind}): {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def vote_on_proposal(kind, entity_id, proposal_id, user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        loaded, err = _load(kind, entity_id, user_id)
        if err:
            return err
        k, entity, viewer, members = loaded
        if viewer not in members:
            return jsonify({'message': 'Only members can vote'}), 403
        eid = getattr(entity, k['id_col'])
        pid = uuid.UUID(str(proposal_id))
        p = Governance.proposal(eid, pid)
        if not p:
            return jsonify({'message': 'Proposal not found'}), 404
        p = _with_tally(k, entity, members, viewer, p)   # settles it if the deadline passed
        if p['status'] != 'open':
            return jsonify({'message': 'This proposal is closed'}), 409
        choice = (request.get_json(silent=True) or {}).get('choice')
        if choice not in CHOICES:
            return jsonify({'message': 'choice must be yes, no or abstain'}), 400
        Governance.cast_vote(pid, viewer, choice)
        return jsonify(_with_tally(k, entity, members, viewer, Governance.proposal(eid, pid))), 200
    except (KeyError, ValueError):
        return jsonify({'message': 'Not found'}), 404
    except Exception as e:
        logger.error(f"Error in vote_on_proposal({kind}): {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def close_proposal(kind, entity_id, proposal_id, user_id=None):
    """A manager counts the votes now rather than waiting for the deadline."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        loaded, err = _load(kind, entity_id, user_id)
        if err:
            return err
        k, entity, viewer, members = loaded
        eid = getattr(entity, k['id_col'])
        if not can_manage_entity(eid, viewer):
            return jsonify({'message': f'Only a {k["noun"]} manager can close a proposal early'}), 403
        pid = uuid.UUID(str(proposal_id))
        p = Governance.proposal(eid, pid)
        if not p:
            return jsonify({'message': 'Proposal not found'}), 404
        if p['status'] != 'open':
            return jsonify({'message': 'This proposal is already closed'}), 409
        p = _settle(k, entity, members, p)
        return jsonify(_with_tally(k, entity, members, viewer, p)), 200
    except (KeyError, ValueError):
        return jsonify({'message': 'Not found'}), 404
    except Exception as e:
        logger.error(f"Error in close_proposal({kind}): {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def withdraw_proposal(kind, entity_id, proposal_id, user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        loaded, err = _load(kind, entity_id, user_id)
        if err:
            return err
        k, entity, viewer, members = loaded
        eid = getattr(entity, k['id_col'])
        pid = uuid.UUID(str(proposal_id))
        p = Governance.proposal(eid, pid)
        if not p:
            return jsonify({'message': 'Proposal not found'}), 404
        if p['status'] != 'open':
            return jsonify({'message': 'This proposal is already closed'}), 409
        if p['created_by'] != str(viewer) and not can_manage_entity(eid, viewer):
            return jsonify({'message': 'Only the proposer can withdraw it'}), 403
        Governance.withdraw(eid, pid)
        return jsonify(_with_tally(k, entity, members, viewer, Governance.proposal(eid, pid))), 200
    except (KeyError, ValueError):
        return jsonify({'message': 'Not found'}), 404
    except Exception as e:
        logger.error(f"Error in withdraw_proposal({kind}): {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def set_delegation(kind, entity_id, user_id=None):
    """Delegate your vote in this group to another member (or clear it with
    delegate_id: null). Delegation is transitive; a direct vote overrides it."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        loaded, err = _load(kind, entity_id, user_id)
        if err:
            return err
        k, entity, viewer, members = loaded
        if viewer not in members:
            return jsonify({'message': 'Only members can delegate'}), 403
        eid = getattr(entity, k['id_col'])
        raw = (request.get_json(silent=True) or {}).get('delegate_id')
        if raw in (None, '', 'null'):
            Governance.set_delegation(eid, viewer, None)
            return jsonify({'message': 'You now vote for yourself', 'my_delegate': None}), 200
        delegate = uuid.UUID(str(raw))
        if delegate == viewer:
            return jsonify({'message': 'You cannot delegate to yourself'}), 400
        if delegate not in members:
            return jsonify({'message': 'You can only delegate to a member of this group'}), 400
        Governance.set_delegation(eid, viewer, delegate)
        names = resolve_user_names([delegate])
        return jsonify({'message': 'Delegation saved',
                        'my_delegate': {'id': str(delegate), 'name': names.get(delegate, 'Member')}}), 200
    except (KeyError, ValueError):
        return jsonify({'message': 'Not found'}), 404
    except Exception as e:
        logger.error(f"Error in set_delegation({kind}): {e}")
        return jsonify({'message': 'Internal server error'}), 500


def register(app_):
    for kind, k in KINDS.items():
        p = f"/api/{k['table']}"
        d = {'kind': kind}
        app_.add_url_rule(f'{p}/<entity_id>/governance', endpoint=f'gov_get_{kind}', view_func=get_governance, defaults=d, methods=['GET', 'OPTIONS'])
        app_.add_url_rule(f'{p}/<entity_id>/proposals', endpoint=f'gov_propose_{kind}', view_func=create_proposal, defaults=d, methods=['POST', 'OPTIONS'])
        app_.add_url_rule(f'{p}/<entity_id>/proposals/<proposal_id>/vote', endpoint=f'gov_vote_{kind}', view_func=vote_on_proposal, defaults=d, methods=['POST', 'OPTIONS'])
        app_.add_url_rule(f'{p}/<entity_id>/proposals/<proposal_id>/close', endpoint=f'gov_close_{kind}', view_func=close_proposal, defaults=d, methods=['POST', 'OPTIONS'])
        app_.add_url_rule(f'{p}/<entity_id>/proposals/<proposal_id>/withdraw', endpoint=f'gov_withdraw_{kind}', view_func=withdraw_proposal, defaults=d, methods=['POST', 'OPTIONS'])
        app_.add_url_rule(f'{p}/<entity_id>/delegation', endpoint=f'gov_delegate_{kind}', view_func=set_delegation, defaults=d, methods=['POST', 'OPTIONS'])
