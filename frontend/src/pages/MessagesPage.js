// Messages: always between two people. The list, and the conversation
// ?with=<person> names; &opening= says what it's about.
import React, { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import PropTypes from 'prop-types';
import api from '../api';
import Avatar from '../components/Avatar';
import { BlockButton, ReportButton } from '../components/Safety';
import { PersonaTag } from '../components/DemoTags';
import { timeAgo } from '../utils/dates';
import { lastOfTheirs, mergeMessages, messagesHref, subjectOf } from '../utils/thread';
import '../styles/Messages.css';

const TEXT_MAX = 2000;

function Conversations({ selected }) {
    const { data, isError } = useQuery({
        queryKey: ['messages'],
        queryFn: () => api.get('/api/messages').then((r) => r.data),
        refetchInterval: 30_000,
    });
    return (
        <div className="msg-list">
            <h1>Messages</h1>
            {isError && !data && <p className="msg-note">Your messages didn&rsquo;t load.</p>}
            {data?.conversations.length === 0 && (
                <p className="msg-note">
                    No messages yet. Press Message on someone&rsquo;s profile, or on an opening to ask about it.
                </p>
            )}
            <ul>
                {(data?.conversations || []).map((c) => (
                    <li key={c.person.id}>
                        <Link to={messagesHref(c.person.id)} aria-current={selected === c.person.id ? 'page' : undefined}
                              className={`msg-row ${selected === c.person.id ? 'is-selected' : ''} ${c.unread ? 'is-unread' : ''}`}>
                            <Avatar userId={c.person.id} name={c.person.name} size={40} />
                            <span className="msg-row-words">
                                <strong>{c.person.name}</strong>
                                <span>{c.last.mine ? 'You: ' : ''}{c.last.text}</span>
                            </span>
                            <span className="msg-when">
                                {timeAgo(c.last.at)}
                                {c.unread && <em className="msg-new">New</em>}
                            </span>
                        </Link>
                    </li>
                ))}
            </ul>
        </div>
    );
}

Conversations.propTypes = { selected: PropTypes.string };

function Thread({ personId, openingId, about }) {
    const client = useQueryClient();
    const base = `/api/messages/${personId}`;
    const key = ['thread', personId, about || openingId];
    const asked = about ? { about } : openingId ? { opening: openingId } : {};
    const { data, error, refetch } = useQuery({
        queryKey: key,
        queryFn: () => api.get(base, { params: asked }).then((r) => r.data),
        refetchInterval: 15_000,
        retry: false,
    });
    const [messages, setMessages] = useState([]);
    const [more, setMore] = useState(null);         // null until an older page was asked for
    const [text, setText] = useState('');
    const [named, setNamed] = useState(false);      // what it's about goes with the first message only
    const [busy, setBusy] = useState(false);
    const [problem, setProblem] = useState('');
    const log = useRef(null);

    useEffect(() => {
        if (data) setMessages((kept) => mergeMessages(kept, data.messages));
    }, [data]);

    const newest = messages[messages.length - 1]?.id;
    useEffect(() => {
        if (log.current) log.current.scrollTop = log.current.scrollHeight;
    }, [newest]);

    const theirs = lastOfTheirs(messages);
    useEffect(() => {
        if (!theirs) return;
        api.post(`${base}/read`, { up_to: theirs })
            .then(() => client.invalidateQueries({ queryKey: ['messages'] }))
            .catch(() => { /* read next time */ });
    }, [base, theirs, client]);

    const earlier = async () => {
        try {
            const r = await api.get(base, { params: { before: messages[0].id } });
            setMessages((kept) => mergeMessages(kept, r.data.messages));
            setMore(r.data.more);
        } catch (err) {
            setProblem("The earlier ones didn't load.");
        }
    };

    const send = async (e) => {
        e.preventDefault();
        const words = text.trim();
        if (!words || busy) return;
        setBusy(true);
        setProblem('');
        try {
            const body = { text: words, ...(data?.about && !named && { about: { kind: data.about.kind || 'opening', id: data.about.id } }) };
            const r = await api.post(base, body);
            setMessages((kept) => mergeMessages(kept, [r.data.sent]));
            setText('');
            setNamed(true);
            client.invalidateQueries({ queryKey: ['messages'] });
        } catch (err) {
            setProblem(err.response?.data?.message || "That didn't send. Please try again.");
        }
        setBusy(false);
    };

    if (!data) {
        return (
            <div className="msg-thread">
                <p className="msg-note">{error ? 'This conversation isn’t there.' : 'Loading…'}</p>
            </div>
        );
    }

    return (
        <div className="msg-thread">
            <div className="msg-head">
                <Link className="msg-back" to="/messages" aria-label="All messages">&larr;</Link>
                <Avatar userId={personId} name={data.person.name} size={36} />
                <h2><Link to={`/user?id=${personId}`}>{data.person.name}</Link></h2>
                {data.person.is_agent && <PersonaTag compact />}
                <div className="msg-head-actions">
                    <BlockButton personId={personId} blocked={data.blocked} onChanged={refetch} />
                    <ReportButton report={{ kind: 'person', id: personId }} noteRequired />
                </div>
            </div>
            {data.about && !named && (
                <p className="msg-about">About <Link to={data.about.link || `/opening?id=${data.about.id}`}>{data.about.title}</Link></p>
            )}
            <div className="msg-log" ref={log} role="log" aria-label={`Conversation with ${data.person.name}`}>
                {(more ?? data.more) && messages.length > 0 && (
                    <button type="button" className="safe-link msg-earlier" onClick={earlier}>Show earlier messages</button>
                )}
                {messages.length === 0 && <p className="msg-note">Only the two of you can read what you write here.</p>}
                {messages.map((m) => (
                    <div key={m.id} className={`msg-item ${m.mine ? 'is-mine' : ''}`}>
                        {subjectOf(m) && <Link className="msg-subject" to={subjectOf(m).link}>{subjectOf(m).title}</Link>}
                        <p className="msg-bubble">{m.text}</p>
                        <span className="msg-meta">
                            {timeAgo(m.at)}
                            {!m.mine && <ReportButton report={{ kind: 'message', id: m.id, person_id: personId }} />}
                        </span>
                    </div>
                ))}
            </div>
            {problem && <p className="safe-error" role="alert">{problem}</p>}
            {data.can_send ? (
                <form className="msg-write" onSubmit={send}>
                    <textarea rows={2} maxLength={TEXT_MAX} value={text} onChange={(e) => setText(e.target.value)}
                              aria-label={`Message to ${data.person.name}`} placeholder="Write a message…"
                              onKeyDown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) send(e); }} />
                    <button type="submit" disabled={busy || !text.trim()}>{busy ? 'Sending…' : 'Send'}</button>
                </form>
            ) : (
                <p className="msg-note msg-cant">{data.why_not}</p>
            )}
        </div>
    );
}

Thread.propTypes = { personId: PropTypes.string.isRequired, openingId: PropTypes.string, about: PropTypes.string };

export default function MessagesPage() {
    const [params] = useSearchParams();
    const personId = params.get('with');
    const openingId = params.get('opening');
    const about = params.get('about');
    return (
        <div className={`msg-page ${personId ? 'has-thread' : ''}`}>
            <Conversations selected={personId} />
            {personId
                ? <Thread key={`${personId}:${about || openingId}`} personId={personId} openingId={openingId} about={about} />
                : <div className="msg-thread msg-thread--none"><p className="msg-note">Choose a conversation.</p></div>}
        </div>
    );
}
