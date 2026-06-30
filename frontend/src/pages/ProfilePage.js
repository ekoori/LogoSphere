// ProfilePage — the logged-in user's own profile.
// Shows: hero banner, Value Cards (Meaning Graph), connections (spheres /
// alliances / projects), and an inline edit form.
// Value Cards are fetched from GET /api/value_cards/<user_id>.

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/Profile.css';
import { useLogin } from '../App';
import api from '../api';

// ── Frankl mode labels & card accent mappings ─────────────────────────────
const FRANKL_META = {
    creative:     { label: 'Creative',     glyph: '✶', desc: 'what you make & give' },
    experiential: { label: 'Experiential', glyph: '❍', desc: 'what you receive & encounter' },
    attitudinal:  { label: 'Attitudinal',  glyph: '△', desc: 'the stance you take under constraint' },
};

const COLOR_CSS = {
    honey:     '--honey',
    leaf:      '--leaf',
    terracotta:'--terracotta',
    sage:      '--sage',
    moss:      '--moss',
};

// ── Inline Value Card display ─────────────────────────────────────────────
function ValueCardDisplay({ card, onDelete, canDelete, idx }) {
    const [expanded, setExpanded] = useState(false);
    const [confirmDelete, setConfirmDelete] = useState(false);
    const meta = FRANKL_META[card.frankl_mode] || FRANKL_META.creative;
    const accentVar = COLOR_CSS[card.color_key] || '--honey';
    const rotation = (idx % 2 === 0) ? '-0.8deg' : '0.6deg';

    return (
        <article
            className={`vc-card ${expanded ? 'vc-card--expanded' : ''}`}
            style={{ '--vc-accent': `var(${accentVar})`, '--vc-rot': rotation }}
            onClick={() => { if (!confirmDelete) setExpanded(v => !v); }}
        >
            <span className="vc-punch" aria-hidden="true" />

            <div className="vc-top">
                <span className="vc-mode-badge">
                    <span className="vc-mode-glyph" aria-hidden="true">{meta.glyph}</span>
                    {meta.label}
                </span>
                {canDelete && !confirmDelete && (
                    <button
                        className="vc-delete"
                        title="Remove this card"
                        onClick={(e) => { e.stopPropagation(); setConfirmDelete(true); }}
                        aria-label="Delete value card"
                    >×</button>
                )}
                {canDelete && confirmDelete && (
                    <span className="vc-delete-confirm" onClick={e => e.stopPropagation()}>
                        <span className="vc-delete-prompt">Remove this card?</span>
                        <button className="vc-delete-yes" onClick={(e) => { e.stopPropagation(); onDelete(card.card_id); }}>Remove</button>
                        <button className="vc-delete-no" onClick={(e) => { e.stopPropagation(); setConfirmDelete(false); }}>Keep</button>
                    </span>
                )}
            </div>

            <h3 className="vc-title">{card.title}</h3>

            <div className="vc-field">
                <span className="vc-label">I care about</span>
                <p>{card.care_about}</p>
            </div>

            {expanded && (
                <>
                    {card.because && (
                        <div className="vc-field">
                            <span className="vc-label">Because</span>
                            <p>{card.because}</p>
                        </div>
                    )}
                    {card.looks_like && card.looks_like.length > 0 && (
                        <div className="vc-field">
                            <span className="vc-label">Looks like</span>
                            <ul className="vc-list">
                                {card.looks_like.map((item, i) => <li key={i}>{item}</li>)}
                            </ul>
                        </div>
                    )}
                    {card.drift_looks_like && (
                        <div className="vc-field vc-field--drift">
                            <span className="vc-label">Drift looks like</span>
                            <p>{card.drift_looks_like}</p>
                        </div>
                    )}
                    {card.in_conflict && (
                        <div className="vc-field">
                            <span className="vc-label">In conflict, I prioritise</span>
                            <p>{card.in_conflict}</p>
                        </div>
                    )}
                    {card.never_do && (
                        <div className="vc-field vc-field--never">
                            <span className="vc-label">Never</span>
                            <p>{card.never_do}</p>
                        </div>
                    )}
                </>
            )}

            <button className="vc-toggle" aria-label={expanded ? 'Collapse' : 'Expand'}>
                {expanded ? '▲ Less' : '▼ More'}
            </button>
        </article>
    );
}

// ── New Value Card form ───────────────────────────────────────────────────
function NewValueCardForm({ onSaved, onCancel }) {
    const [form, setForm] = useState({
        title: '', care_about: '', because: '',
        looks_like_raw: '', drift_looks_like: '', in_conflict: '', never_do: '',
        frankl_mode: 'creative', color_key: 'honey',
    });
    const [saving, setSaving] = useState(false);
    const [err, setErr] = useState('');

    const set = (k) => (e) => setForm(p => ({ ...p, [k]: e.target.value }));

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!form.care_about.trim()) { setErr('What you care about is required.'); return; }
        setSaving(true); setErr('');
        try {
            const payload = {
                ...form,
                looks_like: form.looks_like_raw.split('\n').map(s => s.trim()).filter(Boolean),
            };
            delete payload.looks_like_raw;
            const res = await api.post('/api/value_cards', payload);
            onSaved(res.data);
        } catch (e) {
            setErr(e.response?.data?.message || 'Failed to save.');
        } finally {
            setSaving(false);
        }
    };

    return (
        <form className="vc-new-form" onSubmit={handleSubmit} onClick={e => e.stopPropagation()}>
            <h4 className="vc-new-heading">New Value Card</h4>
            {err && <p className="vc-error">{err}</p>}

            <div className="vc-form-row">
                <label>Title (short name for this value)</label>
                <input type="text" value={form.title} onChange={set('title')} placeholder="e.g. Honest dialogue" />
            </div>
            <div className="vc-form-row">
                <label>I care about *</label>
                <textarea rows={2} value={form.care_about} onChange={set('care_about')} placeholder="What specifically do you care about?" required />
            </div>
            <div className="vc-form-row">
                <label>Because</label>
                <textarea rows={2} value={form.because} onChange={set('because')} placeholder="The reason underneath it" />
            </div>
            <div className="vc-form-row">
                <label>Looks like (one behaviour per line)</label>
                <textarea rows={3} value={form.looks_like_raw} onChange={set('looks_like_raw')} placeholder="Observable actions that express this value" />
            </div>
            <div className="vc-form-row">
                <label>Drift looks like</label>
                <input type="text" value={form.drift_looks_like} onChange={set('drift_looks_like')} placeholder="Anti-signals — how you'd know you've drifted" />
            </div>
            <div className="vc-form-row">
                <label>In conflict, I prioritise</label>
                <input type="text" value={form.in_conflict} onChange={set('in_conflict')} placeholder="The trade-off you make" />
            </div>
            <div className="vc-form-row">
                <label>Never</label>
                <input type="text" value={form.never_do} onChange={set('never_do')} placeholder="A hard boundary" />
            </div>
            <div className="vc-form-two-col">
                <div className="vc-form-row">
                    <label>Frankl mode</label>
                    <select value={form.frankl_mode} onChange={set('frankl_mode')}>
                        <option value="creative">✶ Creative — what you make & give</option>
                        <option value="experiential">❍ Experiential — what you receive</option>
                        <option value="attitudinal">△ Attitudinal — your stance under constraint</option>
                    </select>
                </div>
                <div className="vc-form-row">
                    <label>Card colour</label>
                    <select value={form.color_key} onChange={set('color_key')}>
                        <option value="honey">Honey</option>
                        <option value="leaf">Leaf</option>
                        <option value="terracotta">Terracotta</option>
                        <option value="sage">Sage</option>
                        <option value="moss">Moss</option>
                    </select>
                </div>
            </div>

            <div className="vc-form-actions">
                <button type="submit" className="btn btn-accent" disabled={saving}>
                    {saving ? 'Saving…' : 'Add to Meaning Graph'}
                </button>
                <button type="button" className="btn btn-ghost" onClick={onCancel}>Cancel</button>
            </div>
        </form>
    );
}

// ── Main ProfilePage ──────────────────────────────────────────────────────
const ProfilePage = () => {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [profileData, setProfileData] = useState(null);
    const [valueCards, setValueCards] = useState([]);
    const [isEditing, setIsEditing] = useState(false);
    const [showNewCard, setShowNewCard] = useState(false);
    const [imageFile, setImageFile] = useState(null);
    const [editForm, setEditForm] = useState({ name: '', location: '' });
    const [saving, setSaving] = useState(false);
    const [spheres, setSpheres] = useState([]);
    const [alliances, setAlliances] = useState([]);
    const [projects, setProjects] = useState([]);

    const { isLoggedIn } = useLogin();
    const navigate = useNavigate();

    const fetchProfile = useCallback(async () => {
        try {
            const res = await api.get('/api/user/profile');
            const data = res.data;
            setProfileData(data);
            setEditForm({ name: data.name || '', location: data.location || '' });
            if (data.user_id) {
                try {
                    const vcRes = await api.get(`/api/value_cards/${data.user_id}`);
                    setValueCards(vcRes.data || []);
                } catch (_) {}
            }
        } catch (e) {
            if (e.response?.status === 401) {
                navigate('/login', { replace: true });
            } else {
                setError('Could not load profile.');
            }
        } finally {
            setLoading(false);
        }
    }, [navigate]);

    useEffect(() => { fetchProfile(); }, [fetchProfile]);

    useEffect(() => {
        api.get('/api/spheres').then(r => setSpheres(r.data || [])).catch(() => {});
        api.get('/api/alliances').then(r => setAlliances(r.data || [])).catch(() => {});
        api.get('/api/projects').then(r => setProjects(r.data || [])).catch(() => {});
    }, []);

    const handleSave = async (e) => {
        e.preventDefault();
        setSaving(true);
        try {
            const fd = new FormData();
            fd.append('name', editForm.name);
            fd.append('location', editForm.location);
            if (imageFile) fd.append('profile_picture', imageFile);
            const res = await api.post('/api/updateuser', fd, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            setProfileData(prev => ({
                ...prev,
                ...res.data,
                profile_picture: res.data.profile_picture || prev?.profile_picture,
            }));
            setIsEditing(false);
        } catch (_) {
            setError('Failed to save changes.');
        } finally {
            setSaving(false);
        }
    };

    const handleCardSaved = (newCard) => {
        setValueCards(prev => [...prev, newCard]);
        setShowNewCard(false);
    };

    const handleCardDelete = async (cardId) => {
        try {
            await api.delete(`/api/value_cards/${cardId}`);
            setValueCards(prev => prev.filter(c => c.card_id !== cardId));
        } catch (_) {}
    };

    if (loading) return <div className="pf-loading">Loading profile…</div>;

    const avatar = profileData?.profile_picture
        ? `data:image/jpeg;base64,${profileData.profile_picture}`
        : '/static/user-image.jpg';
    const fullName = [profileData?.name, profileData?.surname].filter(Boolean).join(' ') || 'Your Profile';
    const initials = fullName.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase();


    return (
        <div className="pf-page">
            {/* ── Hero banner ─────────────────────────────────────────── */}
            <header className="pf-hero">
                <div className="pf-hero-inner">
                    <div className="pf-avatar-wrap">
                        {profileData?.profile_picture
                            ? <img src={avatar} alt={fullName} className="pf-avatar" />
                            : <div className="pf-avatar pf-avatar--initials">{initials}</div>
                        }
                    </div>
                    <div className="pf-hero-text">
                        <p className="pf-eyebrow">Your profile</p>
                        <h1 className="pf-name">{fullName}</h1>
                        {profileData?.location && (
                            <p className="pf-location">📍 {profileData.location}</p>
                        )}
                    </div>
                    <div className="pf-hero-actions">
                        <button
                            className="btn btn-ghost pf-edit-btn"
                            onClick={() => setIsEditing(v => !v)}
                        >
                            {isEditing ? 'Cancel edit' : 'Edit profile'}
                        </button>
                    </div>
                </div>
                {error && <p className="pf-error-banner">{error}</p>}
            </header>

            {/* ── Edit form (inline, slides in) ───────────────────────── */}
            {isEditing && (
                <section className="pf-edit-section">
                    <form className="pf-edit-form" onSubmit={handleSave}>
                        <h3>Edit profile</h3>
                        <div className="pf-edit-row">
                            <label>Name</label>
                            <input type="text" value={editForm.name}
                                onChange={e => setEditForm(p => ({ ...p, name: e.target.value }))} />
                        </div>
                        <div className="pf-edit-row">
                            <label>Location</label>
                            <input type="text" value={editForm.location}
                                onChange={e => setEditForm(p => ({ ...p, location: e.target.value }))}
                                placeholder="City, Country" />
                        </div>
                        <div className="pf-edit-row">
                            <label>Profile image</label>
                            <input type="file" accept="image/*"
                                onChange={e => {
                                    if (e.target.files?.[0]) setImageFile(e.target.files[0]);
                                }} />
                        </div>
                        <div className="pf-edit-actions">
                            <button type="submit" className="btn btn-primary" disabled={saving}>
                                {saving ? 'Saving…' : 'Save changes'}
                            </button>
                            <button type="button" className="btn btn-ghost" onClick={() => setIsEditing(false)}>
                                Cancel
                            </button>
                        </div>
                    </form>
                </section>
            )}

            <div className="pf-body">
                {/* ── Sidebar: connections ────────────────────────────── */}
                <div className="pf-sidebar">
                    {spheres.length > 0 && (
                        <div className="pf-sidebar-section">
                            <h4>Spheres</h4>
                            <ul className="pf-conn-list">
                                {spheres.map((s) => (
                                    <li key={s.sphere_id || s.name}>
                                        <a href={s.sphere_id ? `/sphere?id=${s.sphere_id}` : '#'} className="pf-conn-pill">
                                            {s.name}
                                        </a>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                    {alliances.length > 0 && (
                        <div className="pf-sidebar-section">
                            <h4>Alliances</h4>
                            <ul className="pf-conn-list">
                                {alliances.map((a) => (
                                    <li key={a.alliance_id || a.name}>
                                        <a href={a.alliance_id ? `/alliance?id=${a.alliance_id}` : '#'} className="pf-conn-pill">
                                            {a.name}
                                        </a>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                    {projects.length > 0 && (
                        <div className="pf-sidebar-section">
                            <h4>Active projects</h4>
                            <ul className="pf-conn-list">
                                {projects.map((p) => (
                                    <li key={p.project_id || p.name}>
                                        <a href={p.project_id ? `/project?id=${p.project_id}` : '#'} className="pf-conn-pill">
                                            {p.name}
                                        </a>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    <div className="pf-sidebar-section pf-sidebar-section--muted">
                        <p className="pf-sidebar-hint">
                            Your connections, projects, and spheres will appear here as you participate in the community.
                        </p>
                    </div>
                </div>

                {/* ── Main: Meaning Graph (Value Cards) ───────────────── */}
                <div className="pf-main">
                    <div className="pf-section-head">
                        <div>
                            <h2 className="pf-section-title">Meaning Graph</h2>
                            <p className="pf-section-sub">
                                Your endorsed values — what you care about and why, in a form that can't easily be optimised away.
                            </p>
                        </div>
                        {!showNewCard && (
                            <button className="btn btn-accent pf-add-card-btn" onClick={() => setShowNewCard(true)}>
                                + Add card
                            </button>
                        )}
                    </div>

                    {showNewCard && (
                        <NewValueCardForm
                            onSaved={handleCardSaved}
                            onCancel={() => setShowNewCard(false)}
                        />
                    )}

                    {valueCards.length === 0 && !showNewCard ? (
                        <div className="pf-empty-cards">
                            <p className="pf-empty-heading">No value cards yet.</p>
                            <p className="pf-empty-body">
                                A Value Card captures one thing you genuinely care about — not a hashtag,
                                but a reason, a behaviour, and a drift signal. Start with one value
                                you'd recognise yourself by.
                            </p>
                            <button className="btn btn-accent" onClick={() => setShowNewCard(true)}>
                                Write your first card
                            </button>
                        </div>
                    ) : (
                        <div className="pf-cards-grid">
                            {valueCards.map((card, i) => (
                                <ValueCardDisplay
                                    key={card.card_id}
                                    card={card}
                                    idx={i}
                                    canDelete={true}
                                    onDelete={handleCardDelete}
                                />
                            ))}
                        </div>
                    )}

                    {/* ── Frankl legend ─────────────────────────────── */}
                    {valueCards.length > 0 && (
                        <div className="pf-frankl-legend">
                            {Object.entries(FRANKL_META).map(([k, m]) => (
                                <span key={k} className={`pf-legend-item pf-legend--${k}`}>
                                    <span aria-hidden="true">{m.glyph}</span> {m.label} — {m.desc}
                                </span>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ProfilePage;
