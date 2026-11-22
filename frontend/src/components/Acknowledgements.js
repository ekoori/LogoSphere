// Acknowledgements on a Meaning Trail (a person's, a group's, an exchange's):
// text with value cards, appreciated by others, highlighted by the trail's
// owner. A run of three or more folds to the ones the server marks `shown`.
import React, { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import api from '../api';
import { useLogin } from '../App';
import Avatar from './Avatar';
import LikeTimestamp from './LikeTimestamp';
import ValueCardChip from './ValueCardChip';
import WordsForm from './WordsForm';
import { PersonaTag } from './DemoTags';
import { fmtDate } from '../utils/mappers';
import '../styles/Acknowledgements.css';
import '../styles/ValueCardChip.css';

function AcknowledgementItem({ trailId, item, onChanged }) {
    const { userId } = useLogin();
    const [likes, setLikes] = useState(item.likes);
    const [busy, setBusy] = useState(false);
    const [armed, setArmed] = useState(false);
    const [problem, setProblem] = useState('');
    useEffect(() => { setLikes(item.likes); }, [item.likes]);

    const base = `/api/trails/${trailId}/acknowledgements/${item.ack_id}`;
    const run = async (work) => {
        if (busy) return;
        setBusy(true);
        setProblem('');
        try {
            await work();
        } catch (err) {
            setProblem(err.response?.data?.message || "That didn't work. Try again.");
        }
        setBusy(false);
    };
    const like = () => run(async () => {
        const res = await api.post(`${base}/like`, { liked: !likes.liked });
        setLikes((was) => ({ ...was, ...res.data }));
    });
    const highlight = () => run(async () => {
        await api.post(`${base}/highlight`, { highlighted: !item.highlighted });
        await onChanged();
    });
    const remove = () => {
        if (!armed) { setArmed(true); return; }
        run(async () => {
            await api.delete(base);
            await onChanged();
        });
    };
    const mine = String(item.author_id) === String(userId);

    return (
        <div className={`ack-item ${item.highlighted ? 'is-highlighted' : ''}`}>
            <Avatar userId={item.author_id} name={item.author_name} size={30} />
            <div className="ack-body">
                <div className="ack-head">
                    {item.author_id
                        ? <Link className="ack-author" to={mine ? '/profile' : `/user?id=${item.author_id}`}>{mine ? 'You' : item.author_name}</Link>
                        : <span className="ack-author">{item.author_name}</span>}
                    {item.author_is_agent && <PersonaTag compact />}
                    <span className="ack-date">{fmtDate(item.created_at)}</span>
                    {item.highlighted && <span className="ack-flag">★ Highlighted</span>}
                </div>
                <p className="ack-text">{item.text}</p>
                {item.cards?.length > 0 && (
                    <div className="comment-value-chips comment-value-chips--ack">
                        {item.cards.map((card, i) => (
                            <ValueCardChip key={card.card_id || i} card={card} subjectLabel="Cares about" currentUserId={userId} />
                        ))}
                    </div>
                )}
                <div className="ack-controls">
                    <LikeTimestamp
                        likedByCurrentUser={!!likes.liked}
                        likesCount={likes.count}
                        likedBy={likes.by}
                        time=""
                        onLike={(e) => { e.stopPropagation(); like(); }}
                        canLike={!likes.own}
                    />
                    {item.can_highlight && (
                        <button type="button" className="ack-link" onClick={highlight} disabled={busy}>
                            {item.highlighted ? 'Remove highlight' : '☆ Highlight'}
                        </button>
                    )}
                    {item.can_remove && (
                        <button type="button" className={`ack-link ${armed ? 'is-danger' : ''}`} onClick={remove}
                                onBlur={() => setArmed(false)} disabled={busy}>
                            {armed ? 'Really remove it?' : 'Remove'}
                        </button>
                    )}
                </div>
                {problem && <p className="ack-problem" role="alert">{problem}</p>}
            </div>
        </div>
    );
}

AcknowledgementItem.propTypes = {
    trailId: PropTypes.string.isRequired,
    item: PropTypes.object.isRequired,
    onChanged: PropTypes.func.isRequired,
};

/** Consecutive acknowledgements, newest first. */
export function AcknowledgementRun({ trailId, items, onChanged }) {
    const [open, setOpen] = useState(false);
    if (!items.length) return null;
    const kept = items.filter((i) => i.shown !== false);
    const hidden = items.length - kept.length;
    return (
        <div className="ack-run" onClick={(e) => e.stopPropagation()}>
            {(open ? items : kept).map((item) => (
                <AcknowledgementItem key={item.ack_id} trailId={trailId} item={item} onChanged={onChanged} />
            ))}
            {hidden > 0 && (
                <button type="button" className="ack-more" aria-expanded={open} onClick={() => setOpen(!open)}>
                    {open ? 'Show fewer' : `${hidden} more acknowledgement${hidden === 1 ? '' : 's'}`}
                </button>
            )}
        </div>
    );
}

AcknowledgementRun.propTypes = {
    trailId: PropTypes.string.isRequired,
    items: PropTypes.array.isRequired,
    onChanged: PropTypes.func.isRequired,
};

/** The button that opens the form. */
export function Acknowledge({ trailId, onChanged, counterparts = [], label = '+ Add acknowledgement' }) {
    const [open, setOpen] = useState(false);
    const save = async ({ text, cardIds }) => {
        await api.post(`/api/trails/${trailId}/acknowledgements`, { text, card_ids: cardIds });
        setOpen(false);
        await onChanged();
    };
    return (
        <div className="ack-add">
            {open ? (
                <WordsForm
                    placeholder="What do you want to acknowledge?"
                    submitLabel="Acknowledge"
                    counterparts={counterparts}
                    onSave={save}
                    onCancel={() => setOpen(false)}
                />
            ) : (
                <button type="button" className="xc-add-btn xc-add-acknowledgement"
                        onClick={(e) => { e.stopPropagation(); setOpen(true); }}>
                    {label}
                </button>
            )}
        </div>
    );
}

Acknowledge.propTypes = {
    trailId: PropTypes.string.isRequired,
    onChanged: PropTypes.func.isRequired,
    counterparts: PropTypes.array,
    label: PropTypes.string,
};
