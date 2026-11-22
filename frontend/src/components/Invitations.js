// Invitation links: made on request, shared by you however you like.
// LogoSphere sends nothing to the people you invite.
import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import api from '../api';
import TwoPress from './TwoPress';
import { formatServerDate } from '../utils/dates';
import { groupHref } from '../utils/returnTo';
import '../styles/Events.css';

const said = (err, fallback) => err.response?.data?.message || fallback;

/** "Invite someone": makes a link, then offers to copy or share it. */
export function InviteLink({ groupId, label = 'Invite someone' }) {
    const client = useQueryClient();
    const [made, setMade] = useState(null);
    const [busy, setBusy] = useState(false);
    const [problem, setProblem] = useState('');
    const [copied, setCopied] = useState(false);

    const make = async () => {
        setBusy(true);
        setProblem('');
        try {
            const { data } = await api.post('/api/invites', groupId ? { group_id: groupId } : {});
            setMade({ ...data, link: `${window.location.origin}${data.path}` });
            setCopied(false);
            client.invalidateQueries({ queryKey: ['invites'] });
        } catch (err) {
            setProblem(said(err, "That didn't make a link. Please try again."));
        }
        setBusy(false);
    };
    const copy = async () => {
        setProblem('');
        try {
            await navigator.clipboard.writeText(made.link);
            setCopied(true);
        } catch (_) {
            setProblem("Your browser didn't allow copying. Select the link and copy it.");
        }
    };
    const share = () => navigator.share({ title: 'An invitation to LogoSphere', url: made.link }).catch(() => {});

    if (!made) {
        return (
            <>
                <button type="button" className="evt-btn" onClick={make} disabled={busy}>{busy ? 'Making a link…' : label}</button>
                {problem && <p className="evt-problem" role="alert">{problem}</p>}
            </>
        );
    }
    return (
        <div className="grp-panel">
            <label className="evt-field">
                {made.group ? `A link into ${made.group.name}` : 'A link to LogoSphere'}
                <input type="text" readOnly value={made.link} onFocus={(e) => e.target.select()} />
            </label>
            <p className="evt-soft">
                It works for up to {made.most_uses} people until {formatServerDate(made.expires_at)}, and it isn&rsquo;t shown
                again. Whoever holds it can use it and sees your name. Revoke it in <Link to="/settings#invitations">Settings</Link>.
            </p>
            {problem && <p className="evt-problem" role="alert">{problem}</p>}
            <div className="evt-foot">
                <button type="button" className="evt-btn evt-btn--main" onClick={copy}>{copied ? 'Copied' : 'Copy the link'}</button>
                {typeof navigator.share === 'function' && <button type="button" className="evt-btn" onClick={share}>Share</button>}
                <button type="button" className="evt-btn" onClick={() => setMade(null)}>Close</button>
            </div>
        </div>
    );
}

InviteLink.propTypes = { groupId: PropTypes.string, label: PropTypes.string };

/** Settings: the links out, and stopping them. */
export function MyInvitations() {
    const client = useQueryClient();
    const [problem, setProblem] = useState('');
    const { data, isError } = useQuery({ queryKey: ['invites'], queryFn: () => api.get('/api/invites').then((r) => r.data) });

    const revoke = async (id) => {
        setProblem('');
        try {
            await api.post(`/api/invites/${id}/revoke`);
            client.invalidateQueries({ queryKey: ['invites'] });
        } catch (err) {
            setProblem(said(err, "That didn't revoke it. Please try again."));
        }
    };

    return (
        <section id="invitations" className="settings-card place-anchor">
            <h3>Invitations</h3>
            <p className="settings-sub">
                A link to share yourself. Each works for two weeks, or until you revoke it. To invite into a group, use
                &ldquo;Invite someone&rdquo; on its page.
            </p>
            <div className="grp-top"><InviteLink label="Make a link to LogoSphere" /></div>
            {isError && <p className="settings-msg settings-msg--err">Your invitations didn&rsquo;t load.</p>}
            {problem && <p className="settings-msg settings-msg--err" role="alert">{problem}</p>}
            {data?.length > 0 && (
                <ul className="inv-list">
                    {data.map((invite) => (
                        <li key={invite.id}>
                            <span>
                                {invite.group ? <Link to={groupHref(invite.group)}>{invite.group.name}</Link> : 'LogoSphere'}
                                <small>
                                    {invite.works
                                        ? `${invite.joined} joined · until ${formatServerDate(invite.expires_at)}`
                                        : `${invite.joined} joined · doesn't work any more`}
                                </small>
                            </span>
                            <TwoPress className="evt-link" label="Revoke" confirmLabel="Really revoke it?" onConfirm={() => revoke(invite.id)} />
                        </li>
                    ))}
                </ul>
            )}
        </section>
    );
}
