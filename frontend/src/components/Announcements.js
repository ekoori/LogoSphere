// A group's word to its members, at the top of its page. Its managers write it.
import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import api from '../api';
import { useLogin } from '../App';
import { ReportButton } from './Safety';
import TwoPress from './TwoPress';
import { timeAgo } from '../utils/dates';
import '../styles/Events.css';

const TEXT_MAX = 2000;
const said = (err, fallback) => err.response?.data?.message || fallback;

function Announce({ groupId, onDone }) {
    const [open, setOpen] = useState(false);
    const [text, setText] = useState('');
    const [busy, setBusy] = useState(false);
    const [problem, setProblem] = useState('');

    const send = async (e) => {
        e.preventDefault();
        if (busy || !text.trim()) return;
        setBusy(true);
        setProblem('');
        try {
            await api.post(`/api/announcements/${groupId}`, { text: text.trim() });
            setText('');
            setOpen(false);
            onDone();
        } catch (err) {
            setProblem(said(err, "That didn't send. Please try again."));
        }
        setBusy(false);
    };

    if (!open) return <button type="button" className="evt-btn" onClick={() => setOpen(true)}>Announce to members</button>;
    return (
        <form className="grp-panel" onSubmit={send}>
            <label className="evt-field">
                Announce to its members
                <textarea rows={3} value={text} maxLength={TEXT_MAX} autoFocus onChange={(e) => setText(e.target.value)} />
            </label>
            <p className="evt-soft">They are notified that there is one. The words themselves are read here.</p>
            {problem && <p className="evt-problem" role="alert">{problem}</p>}
            <div className="evt-foot">
                <button type="submit" className="evt-btn evt-btn--main" disabled={busy || !text.trim()}>
                    {busy ? 'Sending…' : 'Announce'}
                </button>
                <button type="button" className="evt-btn" disabled={busy} onClick={() => setOpen(false)}>Cancel</button>
            </div>
        </form>
    );
}

Announce.propTypes = { groupId: PropTypes.string.isRequired, onDone: PropTypes.func.isRequired };

export default function Announcements({ groupId }) {
    const { userId } = useLogin();
    const client = useQueryClient();
    const [all, setAll] = useState(false);
    const [problem, setProblem] = useState('');
    const { data, isError } = useQuery({
        queryKey: ['announcements', groupId],
        queryFn: () => api.get(`/api/announcements/${groupId}`).then((r) => r.data),
        retry: (count, err) => err?.response?.status >= 500 && count < 2,
    });
    if (isError) return <p className="evt-soft">The announcements didn&rsquo;t load.</p>;
    if (!data) return null;

    const reload = () => client.invalidateQueries({ queryKey: ['announcements', groupId] });
    const remove = async (id) => {
        setProblem('');
        try {
            await api.delete(`/api/announcements/${groupId}/${id}`);
            reload();
        } catch (err) {
            setProblem(said(err, "That didn't remove it. Please try again."));
        }
    };
    const list = data.announcements;
    const shown = all ? list : list.slice(0, 1);

    return (
        <>
            {list.length > 0 && (
                <section className="grp-panel grp-word" aria-label="Announcements">
                    <h3>{list.length > 1 ? 'Announcements' : 'Announcement'}</h3>
                    <ul>
                        {shown.map((a) => (
                            <li key={a.id}>
                                <p className="grp-word-text">{a.text}</p>
                                <div className="grp-word-meta">
                                    {a.author && <Link to={`/user?id=${a.author.id}`}>{a.author.name}</Link>}
                                    <span>{timeAgo(a.at)}</span>
                                    {a.can_remove && (
                                        <TwoPress className="evt-link" label="Remove" confirmLabel="Really remove it?"
                                                  onConfirm={() => remove(a.id)} />
                                    )}
                                    {a.author && String(a.author.id) !== String(userId) && (
                                        <ReportButton report={{ kind: 'announcement', id: a.id, group_id: groupId }} />
                                    )}
                                </div>
                            </li>
                        ))}
                    </ul>
                    {problem && <p className="evt-problem" role="alert">{problem}</p>}
                    {list.length > 1 && (
                        <button type="button" className="evt-link" aria-expanded={all} onClick={() => setAll((v) => !v)}>
                            {all ? 'Only the latest' : `Earlier ones (${list.length - 1})`}
                        </button>
                    )}
                </section>
            )}
            {data.can_announce && <Announce groupId={groupId} onDone={reload} />}
        </>
    );
}

Announcements.propTypes = { groupId: PropTypes.string.isRequired };
