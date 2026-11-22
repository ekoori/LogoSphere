// The people you follow, what they did lately, and whom you both know
// (backend app/utils/activity.py). Newest first, never ranked.
import React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import api from '../api';
import Avatar from './Avatar';
import { DemoTag, PersonaTag } from './DemoTags';
import { timeAgo } from '../utils/dates';
import '../styles/Sharing.css';

export function FollowedActivity() {
    const { data, isError, refetch } = useQuery({
        queryKey: ['activity'],
        queryFn: () => api.get('/api/activity').then((r) => r.data.activity),
        staleTime: 15_000,
    });

    if (!data) {
        return (
            <p className="share-note" role="status">
                {isError
                    ? <>That didn&rsquo;t load. <button type="button" className="share-btn" onClick={() => refetch()}>Try again</button></>
                    : 'Loading…'}
            </p>
        );
    }
    if (!data.length) return <p className="share-note">Nothing lately that you can see.</p>;
    return (
        <ul className="act-list">
            {data.map((item, i) => (
                <li key={`${item.kind}-${item.link}-${item.at}-${i}`}>
                    <Link className="act-row" to={item.link}>
                        <Avatar userId={item.who.id} name={item.who.name} size={36} />
                        <span className="act-words">
                            <span>
                                <strong>{item.who.name}</strong>
                                {item.who.is_agent && <PersonaTag compact />}
                                {' '}{item.says}
                                {item.title && <> <span className="act-title">{item.title}</span></>}
                            </span>
                            {item.text && <span className="act-quote">{item.text}</span>}
                            <span className="act-when">{timeAgo(item.at)}{item.is_demo && <DemoTag />}</span>
                        </span>
                    </Link>
                </li>
            ))}
        </ul>
    );
}

/** On someone's page. */
export function BothKnow({ personId }) {
    const { data } = useQuery({
        queryKey: ['known', personId],
        queryFn: () => api.get(`/api/users/${personId}/known`).then((r) => r.data.people),
        staleTime: 30_000,
        retry: false,
    });
    if (!data?.length) return null;
    return (
        <section className="known" aria-label="You both know">
            <h4>You both know</h4>
            <ul>
                {data.map((p) => (
                    <li key={p.id}>
                        <Link to={`/user?id=${p.id}`}>
                            <Avatar userId={p.id} name={p.name} size={26} />
                            <span>{p.name}</span>
                            {p.is_agent && <PersonaTag compact />}
                        </Link>
                    </li>
                ))}
            </ul>
            <p className="share-note">
                People you follow or had an exchange with, who had one with them. Only exchanges you can see count.
            </p>
        </section>
    );
}

BothKnow.propTypes = { personId: PropTypes.string.isRequired };
