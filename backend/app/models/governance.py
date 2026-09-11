# File: ./backend/app/models/governance.py
# Description: Liquid democracy for spheres, alliances and projects.
#
# Members put *proposals* to their group - either a change to one of the
# group's policies (applied automatically when it passes) or a free-text
# motion - and vote yes / no / abstain. Each member may *delegate* their vote
# for a group to another member; delegation is transitive (A -> B -> C means C
# carries A's and B's weight) and a direct vote always overrides delegation.
# Tallies are weighted accordingly. Whether a proposal passes is decided by the
# group's decision policy: simple majority, 2/3 supermajority, or consensus.
#
# Tables (all raw CQL):
#   governance_proposals   (entity_id, proposal_id)      one row per proposal
#   governance_votes       (proposal_id, user_id)        one row per direct vote
#   governance_delegations (entity_id, delegator_id)     one delegate per member per group
import json
import logging
import uuid
from datetime import datetime, timedelta

from app.db import session

logger = logging.getLogger(__name__)

CHOICES = ('yes', 'no', 'abstain')
DECISION_POLICIES = ('majority', 'supermajority', 'consensus')
PROPOSAL_KINDS = ('policy', 'motion')
DEFAULT_DAYS = 7
MAX_DAYS = 30

# The policies a group may vote on, per kind: key -> allowed values.
# (Sandbox status is a platform-wide decision and isn't votable.)
VOTABLE_POLICIES = {
    'sphere': {
        'join_policy': ('open', 'approval'),
        'decision_policy': DECISION_POLICIES,
        'is_public': ('true', 'false'),
    },
    'alliance': {
        'join_policy': ('open', 'approval'),
        'decision_policy': DECISION_POLICIES,
        'pm_policy': ('single-pm', 'board'),
        'confirm_policy': ('lead', 'board', 'any-member'),
    },
    'project': {
        'join_policy': ('open', 'approval'),
        'decision_policy': DECISION_POLICIES,
        'phase': ('ongoing', 'closed'),
    },
}

POLICY_LABELS = {
    'join_policy': 'Membership join policy',
    'decision_policy': 'How decisions pass',
    'is_public': 'Public activity',
    'pm_policy': 'Projects managed by',
    'confirm_policy': 'Acceptances confirmed by',
    'phase': 'Project phase',
}


def ensure_tables():
    """Idempotent schema for the three governance tables."""
    session.execute("""
        CREATE TABLE IF NOT EXISTS governance_proposals (
            entity_id uuid, proposal_id uuid, kind text, title text, description text,
            policy_key text, policy_value text, status text, created_by uuid,
            created_at timestamp, closes_at timestamp, closed_at timestamp,
            decision_policy text, result text,
            PRIMARY KEY (entity_id, proposal_id))""")
    session.execute("""
        CREATE TABLE IF NOT EXISTS governance_votes (
            proposal_id uuid, user_id uuid, choice text, created_at timestamp,
            PRIMARY KEY (proposal_id, user_id))""")
    session.execute("""
        CREATE TABLE IF NOT EXISTS governance_delegations (
            entity_id uuid, delegator_id uuid, delegate_id uuid, created_at timestamp,
            PRIMARY KEY (entity_id, delegator_id))""")


# ── Tally ───────────────────────────────────────────────────────────────────
def tally(members, direct_votes, delegations):
    """Weighted liquid-democracy count.

    members:      iterable of member ids (only members carry weight)
    direct_votes: {user_id: choice}
    delegations:  {delegator_id: delegate_id}

    Every member has weight 1. A member who voted directly casts their own
    weight plus the weight of everyone whose delegation chain ends at them
    without passing through another direct voter. A member who neither voted
    nor (transitively) reaches a direct voter is *unrepresented*. Cycles and
    delegations to non-members simply stop the chain.
    """
    members = set(members)
    votes = {u: c for u, c in direct_votes.items() if u in members and c in CHOICES}
    weight = {u: 0 for u in votes}
    unrepresented = 0
    for uid in members:
        if uid in votes:
            weight[uid] += 1
            continue
        cur, seen, target = uid, {uid}, None
        while cur in delegations:
            cur = delegations[cur]
            if cur in seen or cur not in members:
                break
            if cur in votes:
                target = cur
                break
            seen.add(cur)
        if target is not None:
            weight[target] += 1
        else:
            unrepresented += 1
    counts = {'yes': 0, 'no': 0, 'abstain': 0}
    for voter, w in weight.items():
        counts[votes[voter]] += w
    counts['eligible'] = len(members)
    counts['unrepresented'] = unrepresented
    counts['direct_votes'] = len(votes)
    return counts


def passes(counts, decision_policy):
    """Apply the group's decision policy to a tally. Abstentions never count
    for or against; a proposal nobody voted 'yes' on cannot pass."""
    yes, no = counts.get('yes', 0), counts.get('no', 0)
    if yes == 0:
        return False
    if decision_policy == 'consensus':
        return no == 0
    if decision_policy == 'supermajority':
        return yes * 3 >= (yes + no) * 2
    return yes > no  # majority


# ── Rows ────────────────────────────────────────────────────────────────────
def _row_to_dict(r):
    return {
        'proposal_id': str(r.proposal_id),
        'entity_id': str(r.entity_id),
        'kind': r.kind,
        'title': r.title,
        'description': r.description,
        'policy_key': r.policy_key,
        'policy_value': r.policy_value,
        'policy_label': POLICY_LABELS.get(r.policy_key) if r.policy_key else None,
        'status': r.status,
        'created_by': str(r.created_by) if r.created_by else None,
        'created_at': r.created_at.isoformat() if r.created_at else None,
        'closes_at': r.closes_at.isoformat() if r.closes_at else None,
        'closed_at': r.closed_at.isoformat() if r.closed_at else None,
        'decision_policy': r.decision_policy,
        'result': json.loads(r.result) if r.result else None,
    }


class Governance:
    @staticmethod
    def proposals(entity_id):
        rows = session.execute(
            "SELECT * FROM governance_proposals WHERE entity_id = %s", [entity_id])
        out = [_row_to_dict(r) for r in rows]
        out.sort(key=lambda p: p['created_at'] or '', reverse=True)
        return out

    @staticmethod
    def proposal(entity_id, proposal_id):
        r = session.execute(
            "SELECT * FROM governance_proposals WHERE entity_id = %s AND proposal_id = %s",
            [entity_id, proposal_id]).one()
        return _row_to_dict(r) if r else None

    @staticmethod
    def create_proposal(entity_id, created_by, kind, title, description,
                        policy_key=None, policy_value=None, days=DEFAULT_DAYS, decision_policy='majority'):
        pid = uuid.uuid4()
        now = datetime.utcnow()
        session.execute(
            """INSERT INTO governance_proposals (entity_id, proposal_id, kind, title, description,
               policy_key, policy_value, status, created_by, created_at, closes_at, decision_policy)
               VALUES (%s,%s,%s,%s,%s,%s,%s,'open',%s,%s,%s,%s)""",
            [entity_id, pid, kind, title, description, policy_key, policy_value,
             created_by, now, now + timedelta(days=days), decision_policy])
        return Governance.proposal(entity_id, pid)

    @staticmethod
    def votes(proposal_id):
        rows = session.execute(
            "SELECT user_id, choice FROM governance_votes WHERE proposal_id = %s", [proposal_id])
        return {r.user_id: r.choice for r in rows}

    @staticmethod
    def cast_vote(proposal_id, user_id, choice):
        session.execute(
            "INSERT INTO governance_votes (proposal_id, user_id, choice, created_at) VALUES (%s,%s,%s,%s)",
            [proposal_id, user_id, choice, datetime.utcnow()])

    @staticmethod
    def delegations(entity_id):
        rows = session.execute(
            "SELECT delegator_id, delegate_id FROM governance_delegations WHERE entity_id = %s", [entity_id])
        return {r.delegator_id: r.delegate_id for r in rows}

    @staticmethod
    def set_delegation(entity_id, delegator_id, delegate_id):
        if delegate_id is None:
            session.execute(
                "DELETE FROM governance_delegations WHERE entity_id = %s AND delegator_id = %s",
                [entity_id, delegator_id])
        else:
            session.execute(
                "INSERT INTO governance_delegations (entity_id, delegator_id, delegate_id, created_at) "
                "VALUES (%s,%s,%s,%s)", [entity_id, delegator_id, delegate_id, datetime.utcnow()])

    @staticmethod
    def close_proposal(entity_id, proposal_id, status, result):
        session.execute(
            "UPDATE governance_proposals SET status = %s, closed_at = %s, result = %s "
            "WHERE entity_id = %s AND proposal_id = %s",
            [status, datetime.utcnow(), json.dumps(result), entity_id, proposal_id])

    @staticmethod
    def withdraw(entity_id, proposal_id):
        session.execute(
            "UPDATE governance_proposals SET status = 'withdrawn', closed_at = %s "
            "WHERE entity_id = %s AND proposal_id = %s", [datetime.utcnow(), entity_id, proposal_id])
