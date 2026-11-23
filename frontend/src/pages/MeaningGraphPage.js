// The Meaning Graph: every value card you may see, drawn by closeness, with
// the whole method underneath. The method is public; the graph is for members.
import React, { useEffect, useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import api from '../api';
import { useLogin } from '../App';
import { useTheme } from '../utils/theme';
import { closestTo, kindOf, percent, titleOf, visibleGraph } from '../utils/graph';
import GraphCanvas from '../components/GraphCanvas';
import { GraphDetails, GraphLegend } from '../components/GraphDetails';
import TabSelector from '../components/TabSelector';
import { useSimple } from '../utils/useSimple';
import '../styles/MeaningGraph.css';

const FIELD_NAMES = {
    care_about: 'What you care about',
    looks_like: 'What it looks like',
    title: 'Title',
    because: 'Because',
    never_do: 'What you would never do',
    drift_looks_like: 'What drift looks like',
    in_conflict: 'When in conflict',
};
const GRAPH_KEY = ['meaning-graph'];

function Method({ folded }) {
    const { data } = useQuery({
        queryKey: ['meaning-graph-method'],
        queryFn: () => api.get('/api/meaning_graph/method').then((r) => r.data),
        staleTime: Infinity,
    });
    if (!data) return null;
    const body = (
        <>
            <p className="mg-method-lead">{data.idea}</p>
            <div className="mg-method-grid">
                <div>
                    <h3>The whole formula</h3>
                    <ol className="mg-formula">{data.formula.map((line) => <li key={line}>{line}</li>)}</ol>
                    <h3>What counts</h3>
                    <table className="mg-weights">
                        <tbody>
                            {data.fields.map((f) => (
                                <tr key={f.field}><th scope="row">{FIELD_NAMES[f.field] || f.field}</th><td>{percent(f.weight)}</td></tr>
                            ))}
                        </tbody>
                    </table>
                    <p className="mg-note">
                        Not counted: {data.not_counted.map((f) => (FIELD_NAMES[f] || f).toLowerCase()).join('; ')}.
                        Shared words there often mean disagreement.
                    </p>
                </div>
                <div>
                    <h3>What keeps it fair</h3>
                    <ul>{data.rules.map((r) => <li key={r}>{r}</li>)}</ul>
                    <p>Never counted: {data.never_inputs.join(', ')}.</p>
                    <h3>Where it falls short</h3>
                    <ul>{data.limits.map((r) => <li key={r}>{r}</li>)}</ul>
                </div>
            </div>
            <details>
                <summary>The {Object.keys(data.families).length} word families (words that count as one)</summary>
                <dl className="mg-families">
                    {Object.entries(data.families).map(([name, words]) => (
                        <div key={name}><dt>{name}</dt><dd>{words.join(', ')}</dd></div>
                    ))}
                </dl>
            </details>
            <details>
                <summary>The {data.stop_words.length} words that don&rsquo;t count</summary>
                <p className="mg-note">{data.stop_words.join(', ')}</p>
            </details>
            <p className="mg-note">
                It builds on{' '}
                {data.sources.map((s, i) => (
                    <React.Fragment key={s.url}>
                        {i > 0 && ', '}<a href={s.url} target="_blank" rel="noreferrer">{s.title}</a>
                    </React.Fragment>
                ))}.
                Their moral graph links wiser values and has no measure of distance, so this measure is LogoSphere&rsquo;s own.
            </p>
        </>
    );
    return (
        <section className="mg-method" id="method">
            {folded ? (
                <details>
                    <summary>How closeness is worked out</summary>
                    {body}
                </details>
            ) : (
                <>
                    <h2>How closeness is worked out</h2>
                    {body}
                </>
            )}
        </section>
    );
}

Method.propTypes = { folded: PropTypes.bool };

function GraphList({ nodes, edges, byId, selected, onSelect }) {
    const rows = nodes
        .map((node) => ({ node, close: closestTo(node.id, edges) }))
        .sort((a, b) => b.close.length - a.close.length || titleOf(a.node).localeCompare(titleOf(b.node)));
    return (
        <div className="mg-list">
            <table>
                <thead>
                    <tr><th>Value card</th><th>Whose</th><th>Kind</th><th>Connections</th><th>Closest</th></tr>
                </thead>
                <tbody>
                    {rows.map(({ node, close }) => (
                        <tr key={node.id} className={node.id === selected ? 'is-selected' : ''}>
                            <td><button type="button" className="mg-text-btn" onClick={() => onSelect(node.id)}>{titleOf(node)}</button></td>
                            <td>{node.owner.name}{node.owner.is_agent ? ' (AI)' : ''}</td>
                            <td>{kindOf(node).label}</td>
                            <td>{close.length}</td>
                            <td>{close.length ? `${titleOf(byId.get(close[0].other))}, ${percent(close[0].edge.closeness)}` : 'none'}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

GraphList.propTypes = {
    nodes: PropTypes.array.isRequired,
    edges: PropTypes.array.isRequired,
    byId: PropTypes.instanceOf(Map).isRequired,
    selected: PropTypes.string,
    onSelect: PropTypes.func.isRequired,
};

export default function MeaningGraphPage() {
    const { userId, authChecked } = useLogin();
    const { effective } = useTheme();
    const simple = useSimple();
    const client = useQueryClient();
    const [params, setParams] = useSearchParams();
    const owner = params.get('owner');
    const askedCard = params.get('card');
    const [scope, setScope] = useState('all');
    const [view, setView] = useState('graph');
    const [query, setQuery] = useState('');
    const [demos, setDemos] = useState(true);
    const [chosenFrom, setChosenFrom] = useState(null);
    const [selected, setSelected] = useState(null);
    const [focus, setFocus] = useState(null);

    const { data: graph, isError, refetch } = useQuery({
        queryKey: GRAPH_KEY,
        queryFn: () => api.get('/api/meaning_graph').then((r) => r.data),
        enabled: !!userId,
        staleTime: 15_000,
    });
    // Simple has no slider, so it keeps to the platform's threshold.
    const from = (simple ? null : chosenFrom) ?? graph?.shown_from ?? 0.12;
    const shown = useMemo(
        () => (graph ? visibleGraph(graph, { scope, owner, focus, demos, query, from }) : null),
        [graph, scope, owner, focus, demos, query, from],
    );
    const byId = useMemo(() => new Map((graph?.nodes || []).map((n) => [n.id, n])), [graph]);
    // ?card=<any version of a card>: open on its dot, with what is close to it.
    const { data: cardNode, isError: cardMissing } = useQuery({
        queryKey: ['graph-card', askedCard],
        queryFn: () => api.get(`/api/meaning_graph/card/${askedCard}`).then((r) => r.data.id),
        enabled: !!userId && !!askedCard,
        retry: false,
        staleTime: 60_000,
    });
    useEffect(() => {
        if (cardNode) {
            setSelected(cardNode);
            setFocus(cardNode);
        }
    }, [cardNode]);

    const judged = (edge) => client.setQueryData(GRAPH_KEY, (was) => was && ({
        ...was, edges: was.edges.map((e) => (e.a === edge.a && e.b === edge.b ? edge : e)),
    }));
    const ownerName = owner && (graph?.nodes.find((n) => n.owner.id === owner)?.owner.name || 'one owner');
    const changeScope = (key) => {
        setScope(key);
        setFocus(null);
        if (owner) setParams({}, { replace: true });
    };
    const clearFilters = () => {
        changeScope('all');
        setQuery('');
        setDemos(true);
    };

    return (
        <div className="mg-page">
            <header className="mg-head">
                <p className="mg-eyebrow">Meaning Graph</p>
                <h1>What we care about, and how it connects</h1>
                <p className="mg-lead">
                    Every dot is a value card, joined to the cards that care about the closest things.
                    Nothing is ranked, and <a href="#method">every connection can be explained</a>.
                </p>
            </header>

            {authChecked && !userId && (
                <p className="mg-note mg-signed-out">
                    <Link to="/login">Log in</Link> to see the graph. How it works is below, for anyone to read and check.
                </p>
            )}
            {userId && askedCard && cardMissing && (
                <p className="mg-note" role="status">That card isn&rsquo;t on the graph you can see.</p>
            )}
            {userId && !graph && (
                <p className="mg-note">
                    {isError
                        ? <>The graph didn&rsquo;t load. <button type="button" className="mg-text-btn" onClick={() => refetch()}>Try again</button></>
                        : 'Drawing the Meaning Graph…'}
                </p>
            )}

            {shown && (
                <>
                    <div className="mg-filters">
                        <TabSelector
                            className="mg-scope"
                            tabs={[{ key: 'all', label: 'Everyone' }, { key: 'near', label: 'My spheres' }, { key: 'mine', label: 'My values' }]}
                            active={owner || focus ? '' : scope}
                            onChange={changeScope}
                        />
                        <input type="search" className="mg-search" value={query} placeholder="Find a value or a person…"
                               aria-label="Find a value or a person" onChange={(e) => setQuery(e.target.value)} />
                        <label className="mg-check">
                            <input type="checkbox" checked={demos} onChange={(e) => setDemos(e.target.checked)} />
                            Demo and AI personas
                        </label>
                        {!simple && (
                            <label className="mg-range">
                                Connections from {percent(from)}
                                <input type="range" min="6" max="50" step="1" value={Math.round(from * 100)}
                                       onChange={(e) => setChosenFrom(Number(e.target.value) / 100)} />
                            </label>
                        )}
                        <button type="button" className="mg-text-btn" onClick={() => setView(view === 'graph' ? 'list' : 'graph')}>
                            {view === 'graph' ? 'See it as a list' : 'See it as a graph'}
                        </button>
                    </div>
                    {(owner || focus) && (
                        <p className="mg-narrowed">
                            Showing {focus ? `“${titleOf(byId.get(focus))}”` : `${ownerName}'s cards`} and what they connect to.{' '}
                            <button type="button" className="mg-text-btn" onClick={() => changeScope('all')}>Show everything</button>
                        </p>
                    )}
                    <div className="mg-body">
                        <div className="mg-stage">
                            {shown.nodes.length === 0 ? (
                                <div className="mg-empty">
                                    <p>
                                        {scope === 'mine' && !query
                                            ? <>You haven&rsquo;t written a value card yet. <Link to="/profile">Write your first</Link>.</>
                                            : 'No cards match these filters.'}
                                    </p>
                                    <button type="button" className="mg-text-btn" onClick={clearFilters}>Show everything</button>
                                </div>
                            ) : view === 'list' ? (
                                <GraphList nodes={shown.nodes} edges={shown.edges} byId={byId} selected={selected} onSelect={setSelected} />
                            ) : (
                                <GraphCanvas nodes={shown.nodes} edges={shown.edges} degree={shown.degree} found={shown.found}
                                             selected={selected} onSelect={setSelected} theme={effective} />
                            )}
                            <div className="mg-stage-foot">
                                <GraphLegend />
                                <span className="mg-count">{shown.nodes.length} cards · {shown.edges.length} connections</span>
                            </div>
                        </div>
                        <GraphDetails
                            node={shown.degree.has(selected) ? byId.get(selected) : undefined}
                            edges={shown.edges}
                            byId={byId}
                            focused={!!focus && focus === selected}
                            onSelect={setSelected}
                            onFocus={setFocus}
                            onJudged={judged}
                        />
                    </div>
                </>
            )}
            <Method folded={simple && !!userId} />
        </div>
    );
}
