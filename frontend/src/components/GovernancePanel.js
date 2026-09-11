// GovernancePanel — liquid democracy for a sphere / alliance / project.
//
// Members see the group's policies, propose changes (a policy switch that is
// applied automatically when it passes, or a free-text motion), vote yes / no
// / abstain, and delegate their vote to another member. Delegation is
// transitive and a direct vote always overrides it; tallies are weighted
// accordingly and shown live. Managers may count a vote early.
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import PropTypes from 'prop-types';
import { useQuery } from '@tanstack/react-query';
import api from '../api';
import { useLogin } from '../App';
import { useInvalidate, KIND_PATH } from '../utils/queries';
import Avatar from './Avatar';
import '../styles/Governance.css';

const DECISION_COPY = {
    majority: 'a simple majority — more weighted yes than no',
    supermajority: 'a two-thirds supermajority of weighted yes and no votes',
    consensus: 'consensus — at least one yes and no weighted no votes',
};
const VALUE_LABELS = {
    open: 'Open — anyone can join', approval: 'Approval required',
    majority: 'Simple majority', supermajority: 'Two-thirds supermajority', consensus: 'Consensus',
    true: 'On', false: 'Off',
    'single-pm': "Each project's own manager", board: 'Lead and Board members',
    lead: 'The Lead only', 'any-member': 'Any member',
    ongoing: 'Ongoing', closed: 'Closed (archived)',
};
const label = (v) => VALUE_LABELS[v] || String(v).replace(/-/g, ' ');
const fmt = (iso) => (iso ? new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : '');

function TallyBar({ tally }) {
    if (!tally) return null;
    const cast = (tally.yes || 0) + (tally.no || 0) + (tally.abstain || 0);
    const total = Math.max(tally.eligible || cast, 1);
    const pct = (n) => `${Math.round(((n || 0) / total) * 100)}%`;
    return (
        <div className="gov-tally">
            <div className="gov-tally-bar" role="img" aria-label={`yes ${tally.yes}, no ${tally.no}, abstain ${tally.abstain} of ${tally.eligible} members`}>
                <span className="gov-tally-yes" style={{ width: pct(tally.yes) }} />
                <span className="gov-tally-no" style={{ width: pct(tally.no) }} />
                <span className="gov-tally-abstain" style={{ width: pct(tally.abstain) }} />
            </div>
            <div className="gov-tally-legend">
                <span><b>{tally.yes}</b> yes</span>
                <span><b>{tally.no}</b> no</span>
                <span><b>{tally.abstain}</b> abstain</span>
                <span className="gov-tally-faint">{tally.unrepresented} of {tally.eligible} not represented</span>
                {tally.direct_votes != null && <span className="gov-tally-faint">{tally.direct_votes} voted directly</span>}
            </div>
        </div>
    );
}

function Proposal({ kind, entityId, p, canManage, userId, onChanged }) {
    const [busy, setBusy] = useState(false);
    const [err, setErr] = useState('');
    const base = `/api/${KIND_PATH[kind]}/${entityId}/proposals/${p.proposal_id}`;
    const act = async (path, body) => {
        setBusy(true); setErr('');
        try { await api.post(`${base}/${path}`, body || {}); await onChanged(); }
        catch (e) { setErr(e.response?.data?.message || 'Could not do that.'); }
        finally { setBusy(false); }
    };
    const open = p.status === 'open';
    const statusCls = { open: 'gov-status--open', passed: 'gov-status--passed', rejected: 'gov-status--rejected', withdrawn: 'gov-status--withdrawn' }[p.status];
    return (
        <article className={`gov-proposal ${open ? '' : 'gov-proposal--closed'}`}>
            <div className="gov-proposal-head">
                <div>
                    <span className={`gov-status ${statusCls}`}>{p.status}</span>
                    <span className="gov-kind">{p.kind === 'policy' ? 'Policy change' : 'Motion'}</span>
                </div>
                <span className="gov-meta">
                    by {p.created_by_name || 'a member'} · {open ? `closes ${fmt(p.closes_at)}` : `closed ${fmt(p.closed_at)}`}
                </span>
            </div>
            <h4 className="gov-proposal-title">{p.title}</h4>
            {p.kind === 'policy' && (
                <p className="gov-proposal-policy">
                    Set <b>{p.policy_label || p.policy_key}</b> to <b>{label(p.policy_value)}</b>
                    {p.status === 'passed' && ' — applied.'}
                </p>
            )}
            {p.description && <p className="gov-proposal-desc">{p.description}</p>}
            <TallyBar tally={p.tally} />
            {open && (
                <div className="gov-proposal-actions">
                    {['yes', 'no', 'abstain'].map((c) => (
                        <button key={c} type="button" disabled={busy}
                                className={`gov-vote-btn gov-vote-btn--${c} ${p.my_vote === c ? 'is-mine' : ''}`}
                                onClick={() => act('vote', { choice: c })}>
                            {p.my_vote === c ? '✓ ' : ''}{c}
                        </button>
                    ))}
                    <span className="gov-would">{p.would_pass ? 'Would pass as it stands' : 'Would not pass as it stands'}</span>
                    {canManage && <button type="button" className="gov-link-btn" disabled={busy} onClick={() => act('close')}>Count now</button>}
                    {p.created_by === userId && <button type="button" className="gov-link-btn" disabled={busy} onClick={() => act('withdraw')}>Withdraw</button>}
                </div>
            )}
            {err && <p className="gov-error">{err}</p>}
        </article>
    );
}

function ProposeForm({ kind, entityId, policies, onCreated }) {
    const [pkind, setPkind] = useState('policy');
    const [policyKey, setPolicyKey] = useState(Object.keys(policies)[0] || '');
    const [policyValue, setPolicyValue] = useState('');
    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [days, setDays] = useState(7);
    const [busy, setBusy] = useState(false);
    const [err, setErr] = useState('');
    const current = policies[policyKey];
    const options = (current?.options || []).filter((o) => String(o) !== String(current?.value));

    const submit = async (e) => {
        e.preventDefault();
        setBusy(true); setErr('');
        try {
            await api.post(`/api/${KIND_PATH[kind]}/${entityId}/proposals`, {
                kind: pkind, title, description, days,
                policy_key: pkind === 'policy' ? policyKey : undefined,
                policy_value: pkind === 'policy' ? policyValue : undefined,
            });
            setTitle(''); setDescription(''); setPolicyValue('');
            await onCreated();
        } catch (ex) {
            setErr(ex.response?.data?.message || 'Could not create the proposal.');
        } finally { setBusy(false); }
    };

    return (
        <form className="gov-propose" onSubmit={submit}>
            <div className="gov-propose-row">
                <label>
                    <input type="radio" name="pkind" checked={pkind === 'policy'} onChange={() => setPkind('policy')} /> Change a policy
                </label>
                <label>
                    <input type="radio" name="pkind" checked={pkind === 'motion'} onChange={() => setPkind('motion')} /> Put a motion to the group
                </label>
            </div>
            {pkind === 'policy' ? (
                <div className="gov-propose-row">
                    <select value={policyKey} onChange={(e) => { setPolicyKey(e.target.value); setPolicyValue(''); }} aria-label="Policy">
                        {Object.entries(policies).map(([k, v]) => <option key={k} value={k}>{v.label} (now: {label(v.value ?? 'open')})</option>)}
                    </select>
                    <select value={policyValue} onChange={(e) => setPolicyValue(e.target.value)} required aria-label="New value">
                        <option value="">— change to —</option>
                        {options.map((o) => <option key={o} value={o}>{label(o)}</option>)}
                    </select>
                </div>
            ) : (
                <input type="text" placeholder="What are you proposing?" value={title} onChange={(e) => setTitle(e.target.value)} required />
            )}
            <textarea rows={2} placeholder={pkind === 'policy' ? 'Why? (optional)' : 'Details (optional)'} value={description} onChange={(e) => setDescription(e.target.value)} />
            <div className="gov-propose-row gov-propose-foot">
                <label>Open for <input type="number" min={1} max={30} value={days} onChange={(e) => setDays(Number(e.target.value))} /> days</label>
                <button type="submit" className="btn btn-accent" disabled={busy || (pkind === 'policy' && !policyValue)}>{busy ? 'Opening…' : 'Open the vote'}</button>
            </div>
            {err && <p className="gov-error">{err}</p>}
        </form>
    );
}

export default function GovernancePanel({ kind, entityId, canManage }) {
    const { userId } = useLogin();
    const invalidate = useInvalidate();
    const q = useQuery({
        queryKey: ['governance', kind, entityId],
        queryFn: () => api.get(`/api/${KIND_PATH[kind]}/${entityId}/governance`).then((r) => r.data),
        enabled: !!entityId && !!userId,
        staleTime: 10_000,
        retry: false,
    });
    const [showPropose, setShowPropose] = useState(false);
    const [delegateBusy, setDelegateBusy] = useState(false);
    const [delegateErr, setDelegateErr] = useState('');

    const refresh = () => Promise.all([q.refetch(), invalidate.entity(kind, entityId)]);

    if (q.isLoading) return <p className="ep-empty">Loading governance…</p>;
    if (q.isError) {
        return <p className="ep-empty">{q.error?.response?.data?.message || 'Governance is only visible to members.'}</p>;
    }
    const g = q.data;
    const openProps = g.proposals.filter((p) => p.status === 'open');
    const closedProps = g.proposals.filter((p) => p.status !== 'open');

    const setDelegate = async (id) => {
        setDelegateBusy(true); setDelegateErr('');
        try { await api.post(`/api/${KIND_PATH[kind]}/${entityId}/delegation`, { delegate_id: id || null }); await q.refetch(); }
        catch (e) { setDelegateErr(e.response?.data?.message || 'Could not save.'); }
        finally { setDelegateBusy(false); }
    };

    return (
        <div className="gov">
            <section className="gov-section">
                <h4 className="gov-h">How this {kind} decides</h4>
                <p className="gov-lead">
                    Any member can propose a change; everyone votes, or lends their vote to someone they trust.
                    Proposals pass by <b>{DECISION_COPY[g.decision_policy] || g.decision_policy}</b>.
                    A delegated vote follows its delegate (even when they delegate on), and voting yourself always overrides it.
                </p>
                <dl className="gov-policies">
                    {Object.entries(g.policies).map(([k, v]) => (
                        <div key={k} className="gov-policy"><dt>{v.label}</dt><dd>{label(v.value ?? (k === 'join_policy' ? 'open' : '—'))}</dd></div>
                    ))}
                </dl>
                {canManage && <p className="gov-faint">As a manager you can also set these directly in <Link to={`/${kind}-management?id=${entityId}`}>management</Link>.</p>}
            </section>

            {g.is_member && (
                <section className="gov-section">
                    <h4 className="gov-h">Your vote</h4>
                    <div className="gov-delegation">
                        <span>Cast by</span>
                        <select value={g.my_delegate?.id || ''} onChange={(e) => setDelegate(e.target.value)} disabled={delegateBusy} aria-label="Delegate your vote">
                            <option value="">— yourself —</option>
                            {g.members.filter((m) => m.id !== userId).map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
                        </select>
                        {g.my_delegate && (
                            <span className="gov-delegate-chip"><Avatar userId={g.my_delegate.id} name={g.my_delegate.name} size={20} /> {g.my_delegate.name} votes for you unless you vote yourself</span>
                        )}
                    </div>
                    {g.delegated_to_me.length > 0 && (
                        <p className="gov-faint">Voting on behalf of {g.delegated_to_me.map((d) => d.name).join(', ')} — your vote carries their weight too.</p>
                    )}
                    {delegateErr && <p className="gov-error">{delegateErr}</p>}
                </section>
            )}

            <section className="gov-section">
                <div className="gov-section-head">
                    <h4 className="gov-h">Open proposals ({openProps.length})</h4>
                    {g.is_member && <button type="button" className="btn btn-accent" onClick={() => setShowPropose((v) => !v)}>{showPropose ? 'Cancel' : '+ Propose'}</button>}
                </div>
                {showPropose && <ProposeForm kind={kind} entityId={entityId} policies={g.policies} onCreated={async () => { setShowPropose(false); await refresh(); }} />}
                {openProps.length === 0 && !showPropose && <p className="ep-empty">Nothing is being voted on right now.</p>}
                {openProps.map((p) => <Proposal key={p.proposal_id} kind={kind} entityId={entityId} p={p} canManage={g.can_manage} userId={userId} onChanged={refresh} />)}
            </section>

            {closedProps.length > 0 && (
                <section className="gov-section">
                    <h4 className="gov-h">Decided ({closedProps.length})</h4>
                    {closedProps.map((p) => <Proposal key={p.proposal_id} kind={kind} entityId={entityId} p={p} canManage={false} userId={userId} onChanged={refresh} />)}
                </section>
            )}
        </div>
    );
}

GovernancePanel.propTypes = {
    kind: PropTypes.oneOf(['sphere', 'alliance', 'project']).isRequired,
    entityId: PropTypes.string,
    canManage: PropTypes.bool,
};
