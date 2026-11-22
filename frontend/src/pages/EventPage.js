// One event: when, where, and who's coming to which date.
import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import api from '../api';
import { useLogin } from '../App';
import Avatar from '../components/Avatar';
import EntityBanner from '../components/EntityBanner';
import TwoPress from '../components/TwoPress';
import { DemoTag } from '../components/DemoTags';
import { ReportButton } from '../components/Safety';
import { ExactSpot } from '../components/WhereLine';
import { ANSWERS, comingText, hasEnded, repeatText, whenText } from '../utils/events';
import { groupHref } from '../utils/returnTo';
import '../styles/EntityPage.css';
import '../styles/Events.css';

const ANSWER_WORD = Object.fromEntries(ANSWERS);

function EventDate({ event, time, send, busy, first }) {
    const { text, zoneNote } = whenText(time, event.tz);
    const on = !event.cancelled && !time.skipped && !hasEnded(time);
    const coming = comingText(time);

    return (
        <li className={`evt-date${time.skipped ? ' is-skipped' : ''}${first ? ' is-first' : ''}`}>
            <p className="evt-date-when">
                <strong>{text}</strong>
                {zoneNote && <span className="evt-soft"> ({zoneNote})</span>}
                {time.skipped && <span className="evt-flag">Not on</span>}
            </p>
            {on && (
                <div className="evt-answers" role="group" aria-label={`Are you coming, ${text}?`}>
                    {ANSWERS.map(([key, label]) => {
                        const mine = time.my_answer === key;
                        return (
                            <button key={key} type="button" className={`evt-answer${mine ? ' is-on' : ''}`} aria-pressed={mine}
                                    disabled={busy} onClick={() => send('reply', { day: time.day, answer: mine ? null : key })}>
                                {label}
                            </button>
                        );
                    })}
                </div>
            )}
            {coming && (
                <details className="evt-people" open={first || undefined}>
                    <summary>{coming}</summary>
                    <ul>
                        {time.people.map((person) => (
                            <li key={person.id}>
                                <Link to={`/user?id=${person.id}`}>
                                    <Avatar userId={person.id} name={person.name} size={26} />
                                    {person.name}
                                </Link>
                                {person.answer === 'maybe' && <span className="evt-soft"> {ANSWER_WORD.maybe.toLowerCase()}</span>}
                            </li>
                        ))}
                    </ul>
                </details>
            )}
            {event.can_manage && !event.cancelled && event.repeats !== 'never' && !hasEnded(time) && (
                time.skipped ? (
                    <button type="button" className="evt-link" disabled={busy}
                            onClick={() => send('cancel', { day: time.day, cancelled: false })}>
                        It&rsquo;s on after all
                    </button>
                ) : (
                    <TwoPress className="evt-link" label="Cancel this date" confirmLabel="Really cancel this date?" disabled={busy}
                              onConfirm={() => send('cancel', { day: time.day })} />
                )
            )}
        </li>
    );
}

EventDate.propTypes = {
    event: PropTypes.object.isRequired,
    time: PropTypes.object.isRequired,
    send: PropTypes.func.isRequired,
    busy: PropTypes.bool,
    first: PropTypes.bool,
};

export default function EventPage() {
    const [params] = useSearchParams();
    const id = params.get('id');
    const { state } = useLocation();
    const { userId } = useLogin();
    const client = useQueryClient();
    const [busy, setBusy] = useState(false);
    const [problem, setProblem] = useState('');

    const { data: event, error, refetch } = useQuery({
        queryKey: ['event', id],
        queryFn: () => api.get(`/api/events/${id}`).then((r) => r.data),
        enabled: !!id,
        retry: (count, err) => err?.response?.status >= 500 && count < 2,
    });

    if (!event) {
        const missing = !id || error?.response?.status === 404;
        return (
            <div className="evt-page">
                {!error && id ? <p className="evt-soft" role="status">Loading…</p> : (
                    <p className="empty-state">
                        {missing
                            ? <>That event isn&rsquo;t there, or is only for a sphere you aren&rsquo;t in. <Link to="/events">See what&rsquo;s on</Link></>
                            : <>The event didn&rsquo;t load. <button type="button" className="evt-btn" onClick={() => refetch()}>Try again</button></>}
                    </p>
                )}
            </div>
        );
    }

    const send = async (action, body) => {
        setBusy(true);
        setProblem('');
        try {
            const { data } = await api.post(`/api/events/${event.id}/${action}`, body);
            client.setQueryData(['event', id], data);
            client.invalidateQueries({ queryKey: ['events'] });
        } catch (err) {
            setProblem(err.response?.data?.message || "That didn't save. Please try again.");
        }
        setBusy(false);
    };

    // A picture just changed mustn't be the browser's older copy.
    const picture = event.has_image
        ? `/api/events/${event.id}/image${state?.pictureAt ? `?v=${state.pictureAt}` : ''}`
        : undefined;

    return (
        <div className="evt-page evt-page--one">
            <EntityBanner kind="event" imageUrl={picture} isAi={!!event.image_is_ai}>
                <div className="ep-meta-row">
                    <span className="ep-eyebrow">Event</span>
                    {event.is_demo && <DemoTag />}
                    {event.cancelled && <span className="ep-status-badge">Cancelled</span>}
                    {!event.cancelled && event.over && <span className="ep-status-badge">It&rsquo;s over</span>}
                    {event.host
                        ? <Link className="ep-sphere-chip" to={groupHref(event.host)}>{event.host.name}</Link>
                        : <span className="ep-location-chip">For everyone</span>}
                    {event.location && <span className="ep-location-chip">{event.location}</span>}
                    {event.distance && <span className="ep-location-chip">{event.distance.text}</span>}
                </div>
                <h1 className="ep-title">{event.title}</h1>
                {event.repeats !== 'never' && (
                    <p className="ep-description">
                        {repeatText(event.repeats, event.starts.slice(0, 10))}
                        {event.until && `, until ${event.until}`}
                    </p>
                )}
            </EntityBanner>

            {state?.note && <p className="evt-problem" role="status">{state.note}</p>}
            {event.description && <p className="evt-about">{event.description}</p>}
            <ExactSpot point={event.point} />

            <h2>{event.repeats === 'never' ? 'When' : 'The next dates'}</h2>
            {problem && <p className="evt-problem" role="alert">{problem}</p>}
            <ul className="evt-dates">
                {event.times.map((time, i) => (
                    <EventDate key={time.day} event={event} time={time} send={send} busy={busy} first={i === 0} />
                ))}
            </ul>
            {!event.cancelled && !event.over && (
                <p className="evt-soft">
                    {event.host ? 'Whoever can see this event sees who’s coming.' : 'Every signed-in member can see this event, and who’s coming.'}
                </p>
            )}

            <div className="evt-foot">
                {event.creator && (
                    <span className="evt-soft">Put on by <Link to={`/user?id=${event.creator.id}`}>{event.creator.name}</Link></span>
                )}
                {event.can_manage && !event.cancelled && (
                    <>
                        <Link className="evt-btn" to={`/event-edit?id=${event.id}`}>Change it</Link>
                        <TwoPress className="evt-btn" label={event.repeats === 'never' ? 'Cancel the event' : 'Cancel all dates'}
                                  confirmLabel="Really cancel it? Those coming are told." disabled={busy}
                                  onConfirm={() => send('cancel', {})} />
                    </>
                )}
                {event.creator && String(event.creator.id) !== String(userId) && (
                    <ReportButton report={{ kind: 'event', id: event.id }} label="Report this event" />
                )}
            </div>
        </div>
    );
}
