// The side of the Meaning Graph that explains: the chosen card, what it is
// close to, why (every part of the score), and the viewer's say on it.
import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import api from '../api';
import { useLogin } from '../App';
import ValueCardChip from './ValueCardChip';
import { useSimple } from '../utils/useSimple';
import { DemoTag, PersonaTag } from './DemoTags';
import { KINDS, closestTo, kindOf, percent, titleOf } from '../utils/graph';

const ownerHref = (owner) => `/${owner.kind === 'user' ? 'user' : owner.kind}?id=${owner.id}`;

export function GraphLegend() {
    return (
        <div className="mg-legend" aria-label="Legend">
            {KINDS.map((k) => (
                <span key={k.key} className="mg-key" title={k.gloss}>
                    <i className={`mg-swatch mg-swatch--${k.key}`} aria-hidden="true" />{k.glyph} {k.label}
                </span>
            ))}
            <span className="mg-key"><i className="mg-swatch mg-swatch--person" aria-hidden="true" />A person&rsquo;s</span>
            <span className="mg-key"><i className="mg-swatch mg-swatch--group" aria-hidden="true" />A group&rsquo;s</span>
            <span className="mg-key">Bigger: more connections</span>
            <span className="mg-key">Thicker line: closer</span>
        </div>
    );
}

function Part({ label, value, children }) {
    return (
        <li className="mg-part">
            <span className="mg-part-label">{label}</span>
            <span className="mg-part-value">{value}</span>
            {children}
        </li>
    );
}

Part.propTypes = { label: PropTypes.string.isRequired, value: PropTypes.string.isRequired, children: PropTypes.node };

function Why({ edge, node, other, onJudged }) {
    const simple = useSimple();
    const [busy, setBusy] = useState(false);
    const [problem, setProblem] = useState('');
    const thisIsA = edge.a === node.id;
    const mayJudge = node.can_judge && other.can_judge;

    const judge = async (close) => {
        if (busy) return;
        setBusy(true);
        setProblem('');
        try {
            const res = await api.post('/api/meaning_graph/judgement', {
                a: edge.a, b: edge.b, close: edge.my_judgement === close ? null : close,
            });
            onJudged(res.data.edge);
        } catch (e) {
            setProblem(e.response?.data?.message || "That didn't save. Try again.");
        }
        setBusy(false);
    };

    return (
        <div className="mg-why">
            <ul className="mg-parts">
                <Part label="Same words" value={percent(edge.words)}>
                    {edge.shared.length > 0 && (
                        <ul className="mg-shared">
                            {edge.shared.map((w) => {
                                const [here, there] = thisIsA ? [w.here, w.there] : [w.there, w.here];
                                return (
                                    <li key={w.counts_as}>
                                        <b>{here.join(', ')}</b> ↔ <b>{there.join(', ')}</b>
                                        {w.family && <span> (counted as {w.counts_as})</span>}
                                    </li>
                                );
                            })}
                        </ul>
                    )}
                </Part>
                {(!simple || edge.people > 0) && (
                    <Part label="Lived together" value={edge.people ? `${edge.people} people` : 'not yet'} />
                )}
                {edge.lineage && <Part label="One was made from the other" value="yes" />}
                {(!simple || edge.judges > 0) && (
                    <Part label="People's judgement"
                          value={edge.judges ? `${edge.said_close} of ${edge.judges} say close` : 'fewer than 2 so far'} />
                )}
            </ul>
            {simple ? null : mayJudge ? (
                <div className="mg-judge">
                    <span>Do these two feel close to you?</span>
                    <button type="button" className={edge.my_judgement === true ? 'is-on' : ''} aria-pressed={edge.my_judgement === true}
                            onClick={() => judge(true)} disabled={busy}>Close</button>
                    <button type="button" className={edge.my_judgement === false ? 'is-on' : ''} aria-pressed={edge.my_judgement === false}
                            onClick={() => judge(false)} disabled={busy}>Not close</button>
                    {edge.my_judgement !== null && !edge.judges && (
                        <span>Saved. It counts once a second person has judged this pair.</span>
                    )}
                </div>
            ) : (
                <p className="mg-note">One of these is yours, so others judge this pair.</p>
            )}
            {problem && <p className="mg-problem" role="alert">{problem}</p>}
        </div>
    );
}

Why.propTypes = {
    edge: PropTypes.object.isRequired,
    node: PropTypes.object.isRequired,
    other: PropTypes.object.isRequired,
    onJudged: PropTypes.func.isRequired,
};

export function GraphDetails({ node, edges, byId, focused, onSelect, onFocus, onJudged }) {
    const { userId } = useLogin();
    const [openFor, setOpenFor] = useState(null);
    if (!node) {
        return (
            <div className="mg-details">
                <h2 className="mg-details-title">Pick a card</h2>
                <p className="mg-note">
                    Each dot is a value card, and cards that care about close things are drawn near each other.
                    A flat picture can only be roughly right about that, so pick a card for the exact figures
                    and why it is close to others.
                </p>
            </div>
        );
    }
    const card = node.card;
    const kind = kindOf(node);
    const closest = closestTo(node.id, edges).filter((c) => byId.has(c.other));

    return (
        <div className="mg-details">
            <p className="mg-details-kind">
                <i className={`mg-swatch mg-swatch--${kind.key}`} aria-hidden="true" />{kind.glyph} {kind.label}
            </p>
            <h2 className="mg-details-title">{titleOf(node)}</h2>
            <p className="mg-owner">
                <Link to={ownerHref(node.owner)}>{node.owner.name}</Link>
                {node.owner.is_agent && <PersonaTag compact />}
                {node.is_demo && !node.owner.is_agent && <DemoTag />}
            </p>
            {card.title && <p className="mg-care">{card.care_about}</p>}
            <div className="mg-actions">
                <ValueCardChip card={{ ...card, title: titleOf(node) }} subjectLabel="Cares about" currentUserId={userId} />
                <button type="button" className="mg-text-btn" onClick={() => onFocus(focused ? null : node.id)}>
                    {focused ? 'Show everything' : 'Only this and its neighbours'}
                </button>
            </div>

            <h3 className="mg-subhead">Closest</h3>
            {closest.length === 0 && <p className="mg-note">Nothing is this close to it yet.</p>}
            <ul className="mg-closest">
                {closest.map(({ edge, other }) => {
                    const otherNode = byId.get(other);
                    const key = `${node.id}-${other}`;
                    const open = openFor === key;
                    return (
                        <li key={other}>
                            <div className="mg-close-row">
                                <button type="button" className="mg-close-name" onClick={() => onSelect(other)}>
                                    <i className={`mg-swatch mg-swatch--${kindOf(otherNode).key}`} aria-hidden="true" />
                                    <span>{titleOf(otherNode)}<small>{otherNode.owner.name}</small></span>
                                </button>
                                <span className="mg-score">{percent(edge.closeness)}</span>
                                <button type="button" className="mg-text-btn" aria-expanded={open}
                                        onClick={() => setOpenFor(open ? null : key)}>
                                    {open ? 'Hide' : 'Why?'}
                                </button>
                            </div>
                            {open && <Why edge={edge} node={node} other={otherNode} onJudged={onJudged} />}
                        </li>
                    );
                })}
            </ul>
        </div>
    );
}

GraphDetails.propTypes = {
    node: PropTypes.object,
    edges: PropTypes.array.isRequired,
    byId: PropTypes.instanceOf(Map).isRequired,
    focused: PropTypes.bool,
    onSelect: PropTypes.func.isRequired,
    onFocus: PropTypes.func.isRequired,
    onJudged: PropTypes.func.isRequired,
};
