// What's on, soonest first: everywhere you may look, or in one group.
import React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import api from '../api';
import { DemoTag } from './DemoTags';
import { Picture } from './AiTag';
import { WhereLine } from './WhereLine';
import { ANSWERS, comingText, repeatText, tileOf, whenText } from '../utils/events';
import '../styles/Events.css';

const ANSWER_WORD = Object.fromEntries(ANSWERS);

function EventRow({ event, inGroup }) {
    const { upcoming } = event;
    const tile = tileOf(upcoming.day);
    const { text, zoneNote } = whenText(upcoming, event.tz);
    const about = [
        !inGroup || inGroup !== event.host?.id ? (event.host?.name || 'For everyone') : null,
        event.repeats !== 'never' ? repeatText(event.repeats, event.starts.slice(0, 10)) : null,
    ].filter(Boolean).join(' · ');
    const coming = comingText(upcoming);

    return (
        <li>
            <Link className="evt-row" to={`/event?id=${event.id}`}>
                <span className="evt-tile" aria-hidden="true"><b>{tile.date}</b><small>{tile.month}</small></span>
                <span className="evt-row-words">
                    <span className="evt-row-title">{event.title}{event.is_demo && <DemoTag />}</span>
                    <span className="evt-row-when">{text}{zoneNote && ` (${zoneNote})`}</span>
                    {about && <span className="evt-soft">{about}</span>}
                    <WhereLine location={event.location} distance={event.distance} />
                    {(coming || upcoming.my_answer) && (
                        <span className="evt-soft">
                            {coming}
                            {upcoming.my_answer && <strong className="evt-mine"> You: {ANSWER_WORD[upcoming.my_answer]}</strong>}
                        </span>
                    )}
                </span>
                {event.has_image && (
                    <span className="evt-thumb">
                        <Picture isAi={event.image_is_ai} short src={`/api/events/${event.id}/image?size=320`} alt="" loading="lazy" />
                    </span>
                )}
            </Link>
        </li>
    );
}

EventRow.propTypes = { event: PropTypes.object.isRequired, inGroup: PropTypes.string };

export default function EventList({ groupId, empty = 'Nothing is on yet.' }) {
    const { data, isError, refetch } = useQuery({
        queryKey: ['events', groupId || null],
        queryFn: () => api.get('/api/events', { params: groupId ? { group: groupId } : {} }).then((r) => r.data.events),
        staleTime: 15_000,
    });

    if (!data) {
        return (
            <p className="evt-soft" role="status">
                {isError
                    ? <>The events didn&rsquo;t load. <button type="button" className="evt-btn" onClick={() => refetch()}>Try again</button></>
                    : 'Loading…'}
            </p>
        );
    }
    if (!data.length) return <p className="empty-state">{empty}</p>;
    return (
        <ul className="evt-list">
            {data.map((event) => <EventRow key={event.id} event={event} inGroup={groupId} />)}
        </ul>
    );
}

EventList.propTypes = { groupId: PropTypes.string, empty: PropTypes.string };
