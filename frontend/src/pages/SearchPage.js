// SearchPage — two ways to find things:
//   • Text: names, titles, descriptions and value cards that contain the words.
//   • Near values: people, spheres, alliances, projects and openings ranked by
//     how close their value graph is to yours (or to a text you type, or to
//     another person's / group's graph via ?around=<id>).
// The header search box lands here in text mode; the tabs switch modes.
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import api from '../api';
import { useLogin } from '../App';
import Avatar from '../components/Avatar';
import '../styles/Search.css';

const KIND = {
    user:     { label: 'Person',   plural: 'People' },
    sphere:   { label: 'Sphere',   plural: 'Spheres' },
    alliance: { label: 'Alliance', plural: 'Alliances' },
    project:  { label: 'Project',  plural: 'Projects' },
    opening:  { label: 'Opening',  plural: 'Openings' },
    card:     { label: 'Value card', plural: 'Value cards' },
};
const SCOPES = ['all', 'user', 'sphere', 'alliance', 'project', 'opening', 'card'];

function SearchPage() {
    const [params, setParams] = useSearchParams();
    const { userName } = useLogin();
    const mode = params.get('mode') === 'near' ? 'near' : 'text';
    const q = params.get('q') || '';
    const around = params.get('around') || '';
    const scope = SCOPES.includes(params.get('kind')) ? params.get('kind') : 'all';

    const [draft, setDraft] = useState(q);
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const reqId = useRef(0);

    useEffect(() => { setDraft(q); }, [q]);

    const setQuery = (next) => {
        const p = new URLSearchParams(params);
        Object.entries(next).forEach(([k, v]) => { if (v) p.set(k, v); else p.delete(k); });
        setParams(p, { replace: true });
    };

    // Run the search whenever the URL state changes.
    useEffect(() => {
        const id = ++reqId.current;
        const run = async () => {
            if (mode === 'text' && q.trim().length < 2) { setResult(null); setError(''); return; }
            setLoading(true);
            setError('');
            try {
                const kinds = scope === 'all' ? '' : scope;
                const path = mode === 'near' ? '/api/search/vicinity' : '/api/search';
                const res = await api.get(path, { params: { q: q || undefined, around: (mode === 'near' && !q && around) || undefined, kinds: kinds || undefined, limit: 12 } });
                if (id === reqId.current) setResult(res.data);
            } catch (e) {
                if (id === reqId.current) setError(e.response?.data?.message || 'Search failed. Please try again.');
            } finally {
                if (id === reqId.current) setLoading(false);
            }
        };
        run();
    }, [mode, q, around, scope]);

    const onSubmit = (e) => {
        e.preventDefault();
        setQuery({ q: draft.trim() });
    };

    const groups = result?.groups || [];
    const visibleScopes = useMemo(() => (mode === 'near' ? SCOPES.filter((s) => s !== 'card') : SCOPES), [mode]);
    const firstName = (userName || '').split(/\s+/)[0] || 'you';

    return (
        <div className="search-page">
            <header className="search-head">
                <p className="search-eyebrow">Search</p>
                <div className="search-modes" role="tablist">
                    <button role="tab" aria-selected={mode === 'text'} className={mode === 'text' ? 'is-active' : ''} onClick={() => setQuery({ mode: '', kind: scope === 'card' ? '' : scope })}>
                        Text search
                    </button>
                    <button role="tab" aria-selected={mode === 'near'} className={mode === 'near' ? 'is-active' : ''} onClick={() => setQuery({ mode: 'near', kind: scope === 'card' ? '' : scope })}>
                        Near my values
                    </button>
                </div>
                <form className="search-form" onSubmit={onSubmit}>
                    <input
                        type="search"
                        value={draft}
                        onChange={(e) => setDraft(e.target.value)}
                        placeholder={mode === 'near' ? 'Describe what matters to you — or leave empty to search around your own value graph' : 'Names, titles, descriptions, value cards…'}
                        autoFocus
                    />
                    <button type="submit" className="search-go">{mode === 'near' ? 'Find' : 'Search'}</button>
                </form>
                <p className="search-explainer">
                    {mode === 'near'
                        ? 'Ranks by how close each value graph is to the values you describe (or to your own cards). Similarity is cosine distance between the words on the value cards — shared cards count most.'
                        : 'Matches words in names, titles, descriptions and value cards. Sphere-scoped openings, alliances and projects only show if you are in the sphere.'}
                </p>
                <div className="search-scopes">
                    {visibleScopes.map((s) => (
                        <button key={s} className={`search-scope ${scope === s ? 'is-active' : ''}`} onClick={() => setQuery({ kind: s === 'all' ? '' : s })}>
                            {s === 'all' ? 'Everything' : KIND[s].plural}
                        </button>
                    ))}
                </div>
            </header>

            {mode === 'near' && result?.around && !q && (
                <p className="search-anchor">
                    Around the value graph of <strong>{result.around.id && result.around.kind === 'user' && result.around.name === userName ? firstName : result.around.name}</strong>
                    {' '}({result.around.card_count} card{result.around.card_count === 1 ? '' : 's'})
                    {result.around.kind !== 'user' && <> · <Link to={result.around.link}>open {result.around.kind}</Link></>}
                </p>
            )}

            {error && <p className="search-error" role="alert">{error}</p>}
            {loading && <p className="search-status">Searching…</p>}
            {!loading && !error && mode === 'text' && q.trim().length < 2 && (
                <p className="search-status">Type at least two characters to search.</p>
            )}
            {!loading && !error && result && result.groups.length === 0 && (
                <p className="search-status">{result.note || `Nothing found${q ? ` for “${q}”` : ''}.`}</p>
            )}

            {!loading && groups.map((g) => (
                <section key={g.kind} className="search-group">
                    <h2 className="search-group-title">
                        {g.label} <span className="search-group-count">{g.count}</span>
                    </h2>
                    <ul className="search-results">
                        {g.items.map((item) => <ResultRow key={`${g.kind}-${item.id}`} item={item} mode={mode} />)}
                    </ul>
                    {g.count > g.items.length && (
                        <p className="search-more">Showing the {g.items.length} closest of {g.count}. <button className="search-link-btn" onClick={() => setQuery({ kind: g.kind })}>See only {g.label.toLowerCase()}</button></p>
                    )}
                </section>
            ))}
        </div>
    );
}

function ResultRow({ item, mode }) {
    const kind = item.kind;
    const meta = [];
    if (kind === 'opening') {
        meta.push(item.type === 'need' ? 'Need' : 'Offer');
        if (item.provider) meta.push(item.type === 'need' ? `requested by ${item.provider}` : `by ${item.provider}`);
    }
    if (item.sphere_name && kind !== 'sphere') meta.push(item.sphere_name);
    if (kind !== 'opening' && kind !== 'card' && item.member_count != null && kind !== 'user') meta.push(`${item.member_count} member${item.member_count === 1 ? '' : 's'}`);
    if (kind !== 'opening' && kind !== 'card' && item.card_count != null) meta.push(`${item.card_count} value card${item.card_count === 1 ? '' : 's'}`);
    if (kind === 'card') meta.push(`on ${item.owner_name}'s graph`);

    return (
        <li className={`search-result search-result--${kind}`}>
            <div className="search-result-lead">
                {kind === 'user' ? <Avatar userId={item.id} name={item.name} size={36} /> : <span className={`search-kind-mark search-kind-mark--${kind}`} aria-hidden="true" />}
            </div>
            <div className="search-result-body">
                <div className="search-result-head">
                    <Link className="search-result-name" to={item.link}>{item.name}</Link>
                    <span className={`search-kind search-kind--${kind}`}>{KIND[kind]?.label || kind}</span>
                    {mode === 'near' && item.similarity != null && (
                        <span className="search-sim" title="Cosine similarity of value-graph vectors">
                            <span className="search-sim-bar"><span style={{ width: `${Math.round(Math.min(1, item.similarity) * 100)}%` }} /></span>
                            {Math.round(item.similarity * 100)}%
                        </span>
                    )}
                </div>
                {item.summary && <p className="search-result-summary">{item.summary}</p>}
                {meta.length > 0 && <p className="search-result-meta">{meta.join(' · ')}</p>}
                {mode === 'near' && item.shared_cards?.length > 0 && (
                    <p className="search-cards"><span className="search-cards-label">Shared cards</span>
                        {item.shared_cards.map((c) => <span key={c.card_id} className={`search-chip search-chip--${c.color_key || 'honey'}`}>{c.title}</span>)}
                    </p>
                )}
                {mode === 'near' && !item.shared_cards?.length && item.cards?.length > 0 && (
                    <p className="search-cards"><span className="search-cards-label">Their cards</span>
                        {item.cards.map((c) => <span key={c.card_id} className={`search-chip search-chip--${c.color_key || 'honey'}`}>{c.title}</span>)}
                    </p>
                )}
                {mode === 'near' && item.why?.length > 0 && (
                    <p className="search-why">in common: {item.why.join(', ')}</p>
                )}
                {kind === 'card' && item.color_key && (
                    <p className="search-cards"><span className={`search-chip search-chip--${item.color_key}`}>{item.name}</span></p>
                )}
            </div>
        </li>
    );
}

export default SearchPage;
