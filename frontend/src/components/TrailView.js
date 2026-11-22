// A Meaning Trail: exchanges and acknowledgements as one timeline, drawn from
// GET /api/trails/<id> - a person's, a sphere's, an alliance's or a project's.
import React from 'react';
import PropTypes from 'prop-types';
import { useLogin } from '../App';
import { useTrail } from '../utils/queries';
import { mapExchange } from '../utils/mappers';
import { sideOf } from '../utils/exchangeRules';
import ExchangeCard from './ExchangeCard';
import { Acknowledge, AcknowledgementRun } from './Acknowledgements';
import '../styles/MeaningTrail.css';

// Whose side a row is told from: a person's trail from theirs, a group's from
// each initiator's. The viewer is always "You".
function perspective(trail, row, viewerId) {
    const id = trail.kind === 'user' ? trail.trail_id : row.initiator_id;
    const mine = String(id) === String(viewerId);
    const name = trail.kind === 'user' ? trail.name : (row.initiator_name || 'Initiator');
    return { ownerLabel: mine ? 'You' : name, ownerId: id };
}

export default function TrailView({ trailId, empty }) {
    const { userId } = useLogin();
    const { data, isLoading, error, refetch } = useTrail(trailId, { enabled: !!userId });

    if (isLoading) return <p className="empty-state">Loading the Meaning Trail…</p>;
    if (!data) {
        return (
            <p className="empty-state">
                {error?.response?.status === 404
                    ? 'This Meaning Trail is for the members of its sphere.'
                    : "The Meaning Trail didn't load. Refresh the page to try again."}
            </p>
        );
    }
    const isMine = String(data.trail_id) === String(userId);
    const whose = isMine ? [] : [{ id: data.trail_id, label: `${data.name}'s values` }];

    return (
        <section id="meaning-trail" className="user-meaning-trail">
            {data.can_acknowledge && <Acknowledge trailId={data.trail_id} counterparts={whose} onChanged={refetch} />}
            {data.entries.length === 0 && <p className="empty-state">{empty}</p>}
            {data.entries.map((entry) => (entry.type === 'exchange' ? (
                <ExchangeCard
                    key={entry.id}
                    {...mapExchange(entry.exchange, perspective(data, entry.exchange, userId))}
                    ownSide={sideOf(entry.exchange, userId)}
                    onChanged={refetch}
                />
            ) : (
                <AcknowledgementRun key={`run-${entry.id}`} trailId={data.trail_id} items={entry.items} onChanged={refetch} />
            )))}
        </section>
    );
}

TrailView.propTypes = {
    trailId: PropTypes.string.isRequired,
    empty: PropTypes.node.isRequired,
};
