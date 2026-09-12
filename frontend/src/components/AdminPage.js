// AdminPage — platform administration for users flagged is_platform_admin.
// One console for everything on the platform: users (admin flag, profile
// fixes, account removal), spheres / alliances / projects (policies, flags,
// name + description, deletion with dependency checks) and openings
// (withdraw, delete). Every destructive action is two-step (click, confirm)
// rather than a modal dialog, like the rest of the app.
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import api from '../api';
import { useLogin } from '../App';
import '../styles/Admin.css';

const TABS = [
    ['overview', 'Overview'], ['users', 'Users'], ['spheres', 'Spheres'],
    ['alliances', 'Alliances'], ['projects', 'Projects'], ['openings', 'Openings'],
];
const KIND_OF = { spheres: 'sphere', alliances: 'alliance', projects: 'project' };
const PAGE_OF = { sphere: '/sphere', alliance: '/alliance', project: '/project' };
const POLICY_OPTIONS = {
    join_policy: ['open', 'approval'],
    decision_policy: ['majority', 'supermajority', 'consensus'],
    pm_policy: ['single-pm', 'board'],
    confirm_policy: ['lead', 'board', 'any-member'],
    phase: ['ongoing', 'closed'],
};
const POLICIES_BY_KIND = {
    sphere: ['join_policy', 'decision_policy'],
    alliance: ['join_policy', 'decision_policy', 'pm_policy', 'confirm_policy'],
    project: ['join_policy', 'decision_policy', 'phase'],
};

const fmtDate = (v) => {
    if (!v) return '—';
    const d = new Date(v);
    return isNaN(d.getTime()) ? '—' : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
};

// Fetch one admin list; `reload` re-fetches after an action.
function useAdminData(path) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const load = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const res = await api.get(path);
            setData(res.data);
        } catch (e) {
            setError(e.response?.data?.message || 'Could not load.');
        } finally {
            setLoading(false);
        }
    }, [path]);
    useEffect(() => { load(); }, [load]);
    return { data, loading, error, reload: load };
}

// Click once to arm, again to fire; disarms itself after a few seconds.
function TwoStep({ label, confirmLabel, onConfirm, disabled, className = '' }) {
    const [armed, setArmed] = useState(false);
    useEffect(() => {
        if (!armed) return undefined;
        const t = setTimeout(() => setArmed(false), 5000);
        return () => clearTimeout(t);
    }, [armed]);
    return (
        <button
            type="button"
            className={`adm-btn ${armed ? 'adm-btn--armed' : ''} ${className}`}
            disabled={disabled}
            onClick={() => { if (!armed) { setArmed(true); return; } setArmed(false); onConfirm(); }}
        >
            {armed ? confirmLabel : label}
        </button>
    );
}

function Filter({ value, onChange, placeholder }) {
    return (
        <div className="adm-filter">
            <input type="search" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} />
        </div>
    );
}

const matches = (needle, ...hay) => {
    const n = needle.trim().toLowerCase();
    return !n || hay.some((h) => (h || '').toString().toLowerCase().includes(n));
};

// ── Overview ─────────────────────────────────────────────────────────────────
function Overview() {
    const { data, loading, error } = useAdminData('/api/admin/overview');
    if (loading) return <p className="adm-status">Loading…</p>;
    if (error) return <p className="adm-error">{error}</p>;
    const c = data.counts;
    const cards = [
        ['Users', c.users, `${c.platform_admins} platform admin${c.platform_admins === 1 ? '' : 's'}`],
        ['Spheres', c.spheres, `${c.public_spheres} public · ${c.sandbox_spheres} sandbox`],
        ['Alliances', c.alliances, ''],
        ['Projects', c.projects, ''],
        ['Openings', c.openings, `${c.openings_open} open now`],
        ['Exchanges', c.exchanges, ''],
    ];
    return (
        <div>
            <div className="adm-stats">
                {cards.map(([label, n, sub]) => (
                    <div key={label} className="adm-stat">
                        <span className="adm-stat-n">{n}</span>
                        <span className="adm-stat-label">{label}</span>
                        {sub && <span className="adm-stat-sub">{sub}</span>}
                    </div>
                ))}
            </div>
            <h2 className="adm-h2">Platform administrators</h2>
            <ul className="adm-plain-list">
                {data.platform_admins.map((a) => (
                    <li key={a.id}><Link to={`/user?id=${a.id}`}>{a.name}</Link> <span className="adm-muted">{a.email}</span></li>
                ))}
            </ul>
            <p className="adm-muted adm-note">
                Grant or revoke the flag from the Users tab. There must always be at least one administrator,
                and nobody can change their own flag.
            </p>
        </div>
    );
}

// ── Users ────────────────────────────────────────────────────────────────────
function UsersTab({ notify }) {
    const { data, loading, error, reload } = useAdminData('/api/admin/users');
    const [filter, setFilter] = useState('');
    const [editing, setEditing] = useState(null);   // {id, name, surname, location}
    const [busyId, setBusyId] = useState(null);

    const act = async (id, fn, okMsg) => {
        setBusyId(id);
        try {
            await fn();
            notify({ ok: true, text: okMsg });
            await reload();
        } catch (e) {
            notify({ ok: false, text: e.response?.data?.message || 'Action failed.' });
        } finally {
            setBusyId(null);
        }
    };

    const rows = useMemo(() => (data?.users || []).filter((u) => matches(filter, u.full_name, u.email, u.location)), [data, filter]);
    if (loading) return <p className="adm-status">Loading…</p>;
    if (error) return <p className="adm-error">{error}</p>;

    return (
        <div>
            <div className="adm-toolbar">
                <Filter value={filter} onChange={setFilter} placeholder="Filter by name, email or location…" />
                <span className="adm-muted">{rows.length} of {data.users.length}</span>
            </div>
            <div className="adm-table-wrap">
                <table className="adm-table">
                    <thead>
                        <tr><th>Name</th><th>Email</th><th>Joined</th><th className="num">Spheres</th><th className="num">Cards</th><th>Role</th><th className="actions">Actions</th></tr>
                    </thead>
                    <tbody>
                        {rows.map((u) => (
                            <React.Fragment key={u.id}>
                                <tr className={u.is_you ? 'is-you' : ''}>
                                    <td><Link to={`/user?id=${u.id}`}>{u.full_name}</Link>{u.is_you && <span className="adm-you">you</span>}</td>
                                    <td className="adm-muted">{u.email}</td>
                                    <td className="adm-muted">{fmtDate(u.joined_at)}</td>
                                    <td className="num">{u.sphere_count}</td>
                                    <td className="num">{u.card_count}</td>
                                    <td>{u.is_platform_admin ? <span className="adm-badge adm-badge--admin">admin</span> : <span className="adm-muted">member</span>}</td>
                                    <td className="actions">
                                        <button className="adm-btn" disabled={busyId === u.id} onClick={() => setEditing(editing?.id === u.id ? null : { id: u.id, name: u.name || '', surname: u.surname || '', location: u.location || '' })}>
                                            {editing?.id === u.id ? 'Close' : 'Edit'}
                                        </button>
                                        {!u.is_you && (
                                            <TwoStep
                                                label={u.is_platform_admin ? 'Revoke admin' : 'Make admin'}
                                                confirmLabel={u.is_platform_admin ? 'Confirm revoke' : 'Confirm grant'}
                                                disabled={busyId === u.id}
                                                onConfirm={() => act(u.id, () => api.patch(`/api/admin/users/${u.id}`, { is_platform_admin: !u.is_platform_admin }),
                                                    u.is_platform_admin ? `${u.full_name} is no longer an administrator.` : `${u.full_name} is now a platform administrator.`)}
                                            />
                                        )}
                                        {!u.is_you && !u.is_platform_admin && (
                                            <TwoStep
                                                className="adm-btn--danger"
                                                label="Delete"
                                                confirmLabel="Really delete account"
                                                disabled={busyId === u.id}
                                                onConfirm={() => act(u.id, () => api.delete(`/api/admin/users/${u.id}`), `Deleted ${u.full_name}'s account.`)}
                                            />
                                        )}
                                    </td>
                                </tr>
                                {editing?.id === u.id && (
                                    <tr className="adm-editor-row">
                                        <td colSpan={7}>
                                            <form className="adm-editor" onSubmit={(e) => { e.preventDefault(); act(u.id, () => api.patch(`/api/admin/users/${u.id}`, editing), 'Profile updated.').then(() => setEditing(null)); }}>
                                                <label>Name<input value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} required /></label>
                                                <label>Surname<input value={editing.surname} onChange={(e) => setEditing({ ...editing, surname: e.target.value })} /></label>
                                                <label>Location<input value={editing.location} onChange={(e) => setEditing({ ...editing, location: e.target.value })} /></label>
                                                <button type="submit" className="adm-btn adm-btn--primary" disabled={busyId === u.id}>Save</button>
                                            </form>
                                        </td>
                                    </tr>
                                )}
                            </React.Fragment>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

// ── Spheres / alliances / projects ───────────────────────────────────────────
function EntitiesTab({ table, notify }) {
    const kind = KIND_OF[table];
    const { data, loading, error, reload } = useAdminData(`/api/admin/${table}`);
    const [filter, setFilter] = useState('');
    const [editing, setEditing] = useState(null);   // {id, name, description}
    const [busyId, setBusyId] = useState(null);

    const act = async (id, fn, okMsg) => {
        setBusyId(id);
        try {
            await fn();
            if (okMsg) notify({ ok: true, text: okMsg });
            await reload();
        } catch (e) {
            notify({ ok: false, text: e.response?.data?.message || 'Action failed.' });
        } finally {
            setBusyId(null);
        }
    };

    const rows = useMemo(() => (data?.items || []).filter((e) => matches(filter, e.name, e.description, e.sphere_name, e.owner_alliance, e.owner_name)), [data, filter]);
    if (loading) return <p className="adm-status">Loading…</p>;
    if (error) return <p className="adm-error">{error}</p>;

    const policies = POLICIES_BY_KIND[kind];
    return (
        <div>
            <div className="adm-toolbar">
                <Filter value={filter} onChange={setFilter} placeholder={`Filter ${table}…`} />
                <span className="adm-muted">{rows.length} of {data.items.length}</span>
            </div>
            <div className="adm-table-wrap">
                <table className="adm-table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            {kind !== 'sphere' && <th>Sphere</th>}
                            {kind === 'project' && <th>Run by</th>}
                            <th className="num">Members</th>
                            {kind === 'sphere' && <th className="num">Alliances / projects</th>}
                            <th className="num">Cards</th>
                            <th>Policies</th>
                            {kind === 'sphere' && <th>Flags</th>}
                            <th className="actions">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((e) => (
                            <React.Fragment key={e.id}>
                                <tr>
                                    <td>
                                        <Link to={`${PAGE_OF[kind]}?id=${e.id}`}>{e.name}</Link>
                                        {e.pending_count > 0 && <span className="adm-badge">{e.pending_count} pending</span>}
                                    </td>
                                    {kind !== 'sphere' && <td className="adm-muted">{e.sphere_name || '—'}</td>}
                                    {kind === 'project' && <td className="adm-muted">{e.owner_alliance || e.owner_name || '—'}</td>}
                                    <td className="num">{e.member_count}</td>
                                    {kind === 'sphere' && <td className="num">{e.alliance_count} / {e.project_count}</td>}
                                    <td className="num">{e.card_count}</td>
                                    <td className="adm-policies">
                                        {policies.map((p) => (
                                            <label key={p} className="adm-policy">
                                                <span>{p.replace('_policy', '').replace('pm', 'PM')}</span>
                                                <select
                                                    value={e[p] || POLICY_OPTIONS[p][0]}
                                                    disabled={busyId === e.id}
                                                    onChange={(ev) => act(e.id, () => api.patch(`/api/${table}/${e.id}`, { [p]: ev.target.value }), `${e.name}: ${p.replace('_', ' ')} set to ${ev.target.value}.`)}
                                                >
                                                    {POLICY_OPTIONS[p].map((o) => <option key={o} value={o}>{o}</option>)}
                                                </select>
                                            </label>
                                        ))}
                                    </td>
                                    {kind === 'sphere' && (
                                        <td className="adm-flags">
                                            <label><input type="checkbox" checked={!!e.is_public} disabled={busyId === e.id} onChange={(ev) => act(e.id, () => api.post(`/api/spheres/${e.id}/governance`, { is_public: ev.target.checked }), `${e.name} is ${ev.target.checked ? 'now' : 'no longer'} public.`)} /> public</label>
                                            <label><input type="checkbox" checked={!!e.is_sandbox} disabled={busyId === e.id} onChange={(ev) => act(e.id, () => api.post(`/api/spheres/${e.id}/governance`, { is_sandbox: ev.target.checked }), `${e.name} is ${ev.target.checked ? 'now' : 'no longer'} a sandbox.`)} /> sandbox</label>
                                        </td>
                                    )}
                                    <td className="actions">
                                        <button className="adm-btn" disabled={busyId === e.id} onClick={() => setEditing(editing?.id === e.id ? null : { id: e.id, name: e.name || '', description: e.description || '' })}>
                                            {editing?.id === e.id ? 'Close' : 'Edit'}
                                        </button>
                                        <TwoStep
                                            className="adm-btn--danger"
                                            label="Delete"
                                            confirmLabel={`Really delete ${kind}`}
                                            disabled={busyId === e.id}
                                            onConfirm={() => act(e.id, () => api.delete(`/api/admin/${table}/${e.id}`), `Deleted ${e.name}.`)}
                                        />
                                    </td>
                                </tr>
                                {editing?.id === e.id && (
                                    <tr className="adm-editor-row">
                                        <td colSpan={9}>
                                            <form className="adm-editor adm-editor--wide" onSubmit={(ev) => { ev.preventDefault(); act(e.id, () => api.patch(`/api/${table}/${e.id}`, { name: editing.name, description: editing.description }), `${editing.name} updated.`).then(() => setEditing(null)); }}>
                                                <label>Name<input value={editing.name} onChange={(ev) => setEditing({ ...editing, name: ev.target.value })} required /></label>
                                                <label className="grow">Description<textarea rows={3} value={editing.description} onChange={(ev) => setEditing({ ...editing, description: ev.target.value })} /></label>
                                                <button type="submit" className="adm-btn adm-btn--primary" disabled={busyId === e.id}>Save</button>
                                            </form>
                                        </td>
                                    </tr>
                                )}
                            </React.Fragment>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

// ── Openings ─────────────────────────────────────────────────────────────────
function OpeningsTab({ notify }) {
    const { data, loading, error, reload } = useAdminData('/api/admin/openings');
    const [filter, setFilter] = useState('');
    const [onlyOpen, setOnlyOpen] = useState(true);
    const [busyId, setBusyId] = useState(null);

    const act = async (id, fn, okMsg) => {
        setBusyId(id);
        try {
            await fn();
            notify({ ok: true, text: okMsg });
            await reload();
        } catch (e) {
            notify({ ok: false, text: e.response?.data?.message || 'Action failed.' });
        } finally {
            setBusyId(null);
        }
    };

    const rows = useMemo(() => (data?.items || [])
        .filter((o) => !onlyOpen || o.is_open)
        .filter((o) => matches(filter, o.title, o.description, o.provider, o.spheres?.[0], o.project_name, o.status)), [data, filter, onlyOpen]);
    if (loading) return <p className="adm-status">Loading…</p>;
    if (error) return <p className="adm-error">{error}</p>;

    return (
        <div>
            <div className="adm-toolbar">
                <Filter value={filter} onChange={setFilter} placeholder="Filter by title, provider, sphere, status…" />
                <label className="adm-check"><input type="checkbox" checked={onlyOpen} onChange={(e) => setOnlyOpen(e.target.checked)} /> open only</label>
                <span className="adm-muted">{rows.length} of {data.items.length}</span>
            </div>
            <div className="adm-table-wrap">
                <table className="adm-table">
                    <thead>
                        <tr><th>Title</th><th>Type</th><th>Provider</th><th>Sphere</th><th>Status</th><th>Cadence</th><th className="num">v</th><th className="num">Pending / confirmed</th><th className="actions">Actions</th></tr>
                    </thead>
                    <tbody>
                        {rows.map((o) => (
                            <tr key={o.service_id} className={o.is_open ? '' : 'is-closed'}>
                                <td><Link to={`/opening?id=${o.service_id}`}>{o.title}</Link></td>
                                <td><span className={`pill ${o.type === 'need' ? 'pill-honey' : 'pill-clay'}`}>{o.type}</span></td>
                                <td className="adm-muted">{o.acting_user ? `${o.acting_user} for ${o.provider}` : o.provider}</td>
                                <td className="adm-muted">{o.spheres?.[0] || '—'}</td>
                                <td>{o.status}</td>
                                <td className="adm-muted">{o.cadence === 'perpetual' ? 'ongoing' : 'one-time'}</td>
                                <td className="num">{o.version}</td>
                                <td className="num">{o.pending_count} / {o.confirmed_count}</td>
                                <td className="actions">
                                    {o.is_open && (
                                        <TwoStep label="Withdraw" confirmLabel="Confirm withdraw" disabled={busyId === o.service_id}
                                            onConfirm={() => act(o.service_id, () => api.post(`/api/openings/${o.service_id}/cancel`, {}), `Withdrew “${o.title}”.`)} />
                                    )}
                                    {o.confirmed_count === 0 && (
                                        <TwoStep className="adm-btn--danger" label="Delete" confirmLabel="Really delete" disabled={busyId === o.service_id}
                                            onConfirm={() => act(o.service_id, () => api.delete(`/api/admin/openings/${o.service_id}`), `Deleted “${o.title}”.`)} />
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

// ── Page ─────────────────────────────────────────────────────────────────────
const AdminPage = () => {
    const { isPlatformAdmin, authChecked } = useLogin();
    const [params, setParams] = useSearchParams();
    const tab = TABS.some(([t]) => t === params.get('tab')) ? params.get('tab') : 'overview';
    const [notice, setNotice] = useState(null);

    const notify = useCallback((n) => {
        setNotice(n);
    }, []);
    useEffect(() => {
        if (!notice) return undefined;
        const t = setTimeout(() => setNotice(null), 6000);
        return () => clearTimeout(t);
    }, [notice]);

    if (!authChecked) return <div className="adm-page"><p className="adm-status">Loading…</p></div>;
    if (!isPlatformAdmin) {
        return (
            <div className="adm-page">
                <h1 className="adm-title">Platform administration</h1>
                <p className="adm-error">This page is for platform administrators only.</p>
            </div>
        );
    }

    return (
        <div className="adm-page">
            <div className="adm-head">
                <p className="adm-eyebrow">LogoSphere</p>
                <h1 className="adm-title">Platform administration</h1>
                <p className="adm-lede">Everything on the platform, in one place. Changes apply immediately; destructive actions ask twice.</p>
            </div>
            <nav className="adm-tabs" role="tablist">
                {TABS.map(([key, label]) => (
                    <button key={key} role="tab" aria-selected={tab === key} className={tab === key ? 'is-active' : ''} onClick={() => setParams({ tab: key })}>
                        {label}
                    </button>
                ))}
            </nav>
            {notice && <p className={`adm-notice ${notice.ok ? 'adm-notice--ok' : 'adm-notice--err'}`} role="status">{notice.text}</p>}
            <section className="adm-panel">
                {tab === 'overview' && <Overview />}
                {tab === 'users' && <UsersTab notify={notify} />}
                {(tab === 'spheres' || tab === 'alliances' || tab === 'projects') && <EntitiesTab key={tab} table={tab} notify={notify} />}
                {tab === 'openings' && <OpeningsTab notify={notify} />}
            </section>
        </div>
    );
};

export default AdminPage;
