// OpeningPage — detail view for a single opening (offer or need).
// Mirrors ExchangePage's hero/sidebar structure so the two detail pages feel
// like the same family: title, sphere | project context, full status
// progression (with per-phase dates), description, and the accept/confirm/
// reject/like actions that used to only live on the card.
import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, Link, useNavigate } from 'react-router-dom';
import { useLogin } from '../App';
import api from '../api';
import StatusProgression from '../components/StatusProgression';
import LikeTimestamp from '../components/LikeTimestamp';
import EntityBanner from '../components/EntityBanner';
import Avatar from '../components/Avatar';
import { mapService } from '../utils/mappers';
import { buildOpeningProgress } from '../utils/openingProgress';
import { useManagedEntities } from '../utils/useManagedEntities';
import '../styles/Exchange.css';
import '../styles/Openings.css';
import '../styles/EntityPage.css';

const TYPE_LABEL = { offer: 'Offer', need: 'Need' };
const TYPE_PILL  = { offer: 'pill-clay', need: 'pill-honey' };

function OpeningPage() {
    const [searchParams] = useSearchParams();
    const openingId = searchParams.get('id');
    const { userId } = useLogin();
    const navigate = useNavigate();

    const [service, setService] = useState(null);
    const [loading, setLoading] = useState(true);
    const [fetchError, setFetchError] = useState(null);
    const [liked, setLiked] = useState(false);
    const [likes, setLikes] = useState(0);
    const [busy, setBusy] = useState(false);
    const [acceptAs, setAcceptAs] = useState('');
    const [imgVersion, setImgVersion] = useState(0);
    const [editing, setEditing] = useState(false);
    const [editTitle, setEditTitle] = useState('');
    const [editDesc, setEditDesc] = useState('');
    const [savingEdit, setSavingEdit] = useState(false);
    const [editNote, setEditNote] = useState(null);
    const managed = useManagedEntities(userId);

    const fetchService = useCallback(async () => {
        if (!openingId) { setFetchError('No opening ID provided.'); setLoading(false); return; }
        try {
            const res = await api.get(`/api/openings/${openingId}`);
            const mapped = mapService(res.data);
            setService(mapped);
            setLiked(mapped.likedByCurrentUser);
            setLikes(mapped.likesCount);
        } catch (e) {
            setFetchError(
                e.response?.status === 404 ? 'Opening not found.'
                    : e.response?.status === 403 ? 'Join this sphere to view this opening.'
                        : 'Could not load opening. Please try again.'
            );
        } finally {
            setLoading(false);
        }
    }, [openingId]);

    useEffect(() => { fetchService(); }, [fetchService]);

    const handleLike = async () => {
        const prevLiked = liked, prevLikes = likes;
        setLiked((v) => !v);
        setLikes((n) => (liked ? n - 1 : n + 1));
        try {
            const res = await api.post(`/api/openings/${openingId}/like`);
            setLiked(res.data.liked);
            setLikes(res.data.likes);
        } catch (e) {
            setLiked(prevLiked);
            setLikes(prevLikes);
        }
    };

    const handleAccept = async () => {
        if (busy) return;
        setBusy(true);
        try {
            await api.post(`/api/openings/${openingId}/accept`, acceptAs ? { acting_as_id: acceptAs } : {});
            await fetchService();
        } catch (e) {
            alert(e.response?.data?.message || 'Could not accept this opening.');
        } finally {
            setBusy(false);
        }
    };

    const handleConfirm = async (accepterId) => {
        if (busy) return;
        setBusy(true);
        try {
            const res = await api.post(`/api/openings/${openingId}/confirm`, { accepter_id: accepterId });
            if (res.data?.exchange_id) navigate(`/exchange?id=${res.data.exchange_id}`);
            else await fetchService();
        } catch (e) {
            alert(e.response?.data?.message || 'Could not confirm this acceptance.');
        } finally {
            setBusy(false);
        }
    };

    const startEditing = () => {
        setEditTitle(service.title || '');
        setEditDesc(service.description || '');
        setEditNote(null);
        setEditing(true);
    };

    const handleEditSubmit = async (e) => {
        e.preventDefault();
        if (savingEdit) return;
        const title = editTitle.trim();
        if (!title) { setEditNote({ ok: false, text: 'Title cannot be empty.' }); return; }
        setSavingEdit(true);
        try {
            const res = await api.patch(`/api/openings/${openingId}`, { title, description: editDesc });
            setEditing(false);
            const newId = res.data?.service?.service_id;
            if (res.data?.versioned && newId && newId !== openingId) {
                // A new version was branched (the old one is now frozen because
                // an exchange links to it) — jump to the new current version.
                navigate(`/opening?id=${newId}`);
            } else {
                await fetchService();
                setEditNote({ ok: true, text: 'Opening updated.' });
            }
        } catch (err) {
            setEditNote({ ok: false, text: err.response?.data?.message || 'Could not save changes.' });
        } finally {
            setSavingEdit(false);
        }
    };

    const handleReject = async (accepterId) => {
        if (busy) return;
        setBusy(true);
        try {
            await api.post(`/api/openings/${openingId}/reject`, { accepter_id: accepterId });
            await fetchService();
        } catch (e) {
            alert(e.response?.data?.message || 'Could not decline this acceptance.');
        } finally {
            setBusy(false);
        }
    };

    if (loading) return <div className="xc-loading">Loading opening…</div>;
    if (fetchError || !service) return <div className="xc-error-state">{fetchError || 'Opening not found.'}</div>;

    const isPerpetual = service.cadence === 'perpetual';
    const isOwnOpening = userId && service.providerId && userId === service.providerId;
    const lockedToOther = service.status === 'Accepted' && !isPerpetual && !service.myAcceptance;
    const canAccept = userId && !isOwnOpening && !service.myAcceptance && !lockedToOther
        && service.status !== 'Cancelled' && service.status !== 'Completed';
    // Alliances/projects the viewer manages that may accept this opening: only
    // those within the opening's sphere (or any, if the opening is standalone).
    const acceptAsOptions = managed.filter(
        (m) => m.kind !== 'sphere' && (!service.sphereId || String(m.sphere_id) === String(service.sphereId))
    );

    const { steps, currentIndex: stepIdx } = buildOpeningProgress({
        status: service.status,
        cadence: service.cadence,
        postedAt: service.postedAt,
        acceptedAt: service.acceptedAt,
        inProgressAt: service.inProgressAt,
        completedAt: service.completedAt,
        activity: service.activity,
    });

    const pillClass = TYPE_PILL[service.type] || 'pill-clay';
    const typeLabel = TYPE_LABEL[service.type] || service.type;
    const sphere = service.spheres?.[0];

    const handleImageUpload = async (file) => {
        const fd = new FormData();
        fd.append('image', file);
        await api.post(`/api/openings/${openingId}/image`, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
        await fetchService();
        setImgVersion((v) => v + 1);
    };

    return (
        <div className="xc-page xc-page--banner">
            {/* ── Banner ───────────────────────────────────────────────── */}
            <EntityBanner kind="opening" imageUrl={service.hasImage ? `/api/openings/${openingId}/image?v=${imgVersion}` : undefined} onUpload={isOwnOpening ? handleImageUpload : undefined}>
                <div className="xc-page-breadcrumb">
                    <Link to="/openings">Openings</Link>
                    <span>›</span>
                    <span>{service.title}</span>
                </div>

                <div className="xc-page-header">
                    <span className={`pill ${pillClass} type-pill`}>{typeLabel}</span>
                    {isPerpetual && (
                        <span className="cadence-badge cadence-badge--perpetual" title="Ongoing — can be accepted repeatedly">
                            ↻ Ongoing
                        </span>
                    )}
                    <h1 className="xc-page-title">{service.title}</h1>
                </div>

                <div className="xc-page-meta">
                    {sphere && (
                        <Link to={sphere.id ? `/sphere?id=${sphere.id}` : '#'}>{sphere.name}</Link>
                    )}
                    {service.project && (
                        <>
                            <span>|</span>
                            <Link to={service.projectId ? `/project?id=${service.projectId}` : `/project?name=${encodeURIComponent(service.project)}`}>
                                {service.project}
                            </Link>
                        </>
                    )}
                    {service.postedAt && (
                        <>
                            <span>·</span>
                            <span>Posted {service.postedAt}</span>
                        </>
                    )}
                </div>
            </EntityBanner>

            {/* ── Status timeline ───────────────────────────────────────── */}
            <div className="xc-page-timeline">
                <StatusProgression steps={steps} currentIndex={stepIdx} cancelled={service.status === 'Cancelled'} />
            </div>

            {/* ── Body ─────────────────────────────────────────────────── */}
            <div className="xc-page-body">
                <div className="xc-page-main">
                    <div className="xc-page-section">
                        <div className="xc-section-head-row">
                            <p className="xc-page-section-heading">About this opening</p>
                            {isOwnOpening && service.isCurrent && !editing && (
                                <button className="xc-inline-edit-btn" onClick={startEditing}>✎ Edit</button>
                            )}
                        </div>
                        {!service.isCurrent && (
                            <p className="xc-version-note">
                                This is version {service.version} — a past version kept because an exchange was created from it.
                            </p>
                        )}
                        {editing ? (
                            <form className="xc-edit-form" onSubmit={handleEditSubmit}>
                                <label className="xc-edit-label">Title</label>
                                <input
                                    className="xc-edit-input"
                                    value={editTitle}
                                    onChange={(e) => setEditTitle(e.target.value)}
                                    autoFocus
                                />
                                <label className="xc-edit-label">Description</label>
                                <textarea
                                    className="xc-edit-textarea"
                                    rows={5}
                                    value={editDesc}
                                    onChange={(e) => setEditDesc(e.target.value)}
                                />
                                <p className="xc-edit-hint">
                                    If an exchange has already started from this opening, saving keeps the
                                    current version and creates a new one, so those exchanges stay unchanged.
                                </p>
                                <div className="xc-edit-actions">
                                    <button type="submit" className="xc-action-btn xc-action-advance" disabled={savingEdit}>
                                        {savingEdit ? 'Saving…' : 'Save changes'}
                                    </button>
                                    <button type="button" className="xc-action-btn" onClick={() => setEditing(false)} disabled={savingEdit}>
                                        Cancel
                                    </button>
                                </div>
                            </form>
                        ) : (
                            <p className="xc-about-text">{service.description}</p>
                        )}
                        {editNote && (
                            <p className={editNote.ok ? 'xc-edit-ok' : 'xc-edit-err'}>{editNote.text}</p>
                        )}
                    </div>

                    {/* Provider view: pending acceptances awaiting confirmation. */}
                    {isOwnOpening && service.pendingAcceptances?.length > 0 && (
                        <div className="xc-page-section">
                            <p className="xc-page-section-heading">Awaiting your confirmation</p>
                            <div className="service-pending" style={{ marginTop: 0 }}>
                                {service.pendingAcceptances.map((p) => (
                                    <div key={p.accepter_id} className="service-pending-row">
                                        <span className="service-pending-name">
                                            👤{' '}
                                            {p.acting_user_id ? (
                                                <>
                                                    {p.accepter_name}
                                                    <span className="service-pending-via">
                                                        {' · via '}
                                                        <Link to={`/user?id=${p.acting_user_id}`}>{p.acting_user_name}</Link>
                                                    </span>
                                                </>
                                            ) : (
                                                <Link to={`/user?id=${p.accepter_id}`}>{p.accepter_name}</Link>
                                            )}
                                        </span>
                                        <span className="service-pending-actions">
                                            <button className="service-confirm-btn" disabled={busy} onClick={() => handleConfirm(p.accepter_id)}>✓ Confirm</button>
                                            <button className="service-reject-btn" disabled={busy} onClick={() => handleReject(p.accepter_id)}>Decline</button>
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* ── Sidebar ───────────────────────────────────────────── */}
                <div className="xc-page-sidebar">
                    <div className="xc-sidebar-card">
                        <p className="xc-sidebar-heading">Actions</p>
                        <LikeTimestamp likedByCurrentUser={liked} likesCount={likes} time="" onLike={handleLike} />
                        {canAccept && acceptAsOptions.length > 0 && (
                            <label className="service-accept-as" style={{ marginTop: '0.8em' }}>
                                <span className="service-accept-as-label">Accept as</span>
                                <select value={acceptAs} onChange={(e) => setAcceptAs(e.target.value)} disabled={busy}>
                                    <option value="">Myself</option>
                                    {acceptAsOptions.map((m) => (
                                        <option key={m.id} value={m.id}>{m.name} ({m.kind})</option>
                                    ))}
                                </select>
                            </label>
                        )}
                        {canAccept && (
                            <button className="xc-action-btn xc-action-advance" style={{ marginTop: '0.8em' }} disabled={busy} onClick={handleAccept}>
                                {service.type === 'offer' ? '✓ Accept this Offer' : '✓ Fulfil this Need'}
                            </button>
                        )}
                        {!isOwnOpening && service.myAcceptance?.status === 'pending' && (
                            <p style={{ fontSize: '0.85rem', color: 'var(--ink-faint)', marginTop: '0.8em' }}>
                                ⏳ Awaiting confirmation from {service.provider}
                            </p>
                        )}
                        {!isOwnOpening && service.myAcceptance?.status === 'confirmed' && service.myAcceptance.exchange_id && (
                            <button
                                className="xc-action-btn xc-action-advance"
                                style={{ marginTop: '0.8em' }}
                                onClick={() => navigate(`/exchange?id=${service.myAcceptance.exchange_id}`)}
                            >
                                → View your exchange
                            </button>
                        )}
                    </div>

                    <div className="xc-sidebar-card">
                        <p className="xc-sidebar-heading">Provided by</p>
                        <div className="xc-participants-list">
                            <div className="xc-participant">
                                <span>👤</span>
                                {service.actingUser ? (
                                    <span>
                                        <Link to={service.actingUserId ? `/user?id=${service.actingUserId}` : '/user'}>{service.actingUser}</Link>
                                        <span className="on-behalf-of"> on behalf of </span>
                                        <strong>{service.provider}</strong>
                                    </span>
                                ) : (
                                    <Link to={service.providerId ? `/user?id=${service.providerId}` : '/user'}>{service.provider}</Link>
                                )}
                            </div>
                        </div>
                    </div>

                    <div className="xc-sidebar-card">
                        <p className="xc-sidebar-heading">Details</p>
                        <div className="xc-detail-rows">
                            <div className="xc-detail-row">
                                <span className="xc-detail-label">Status</span>
                                <span className="xc-detail-value xc-status-value">{service.status}</span>
                            </div>
                            <div className="xc-detail-row">
                                <span className="xc-detail-label">Cadence</span>
                                <span className="xc-detail-value">{isPerpetual ? 'Ongoing' : 'One-time'}</span>
                            </div>
                            {sphere && (
                                <div className="xc-detail-row">
                                    <span className="xc-detail-label">Sphere</span>
                                    <span className="xc-detail-value"><Link to={`/sphere?id=${sphere.id}`}>{sphere.name}</Link></span>
                                </div>
                            )}
                        </div>
                    </div>

                    {service.exchanges && service.exchanges.length > 0 && (
                        <div className="xc-sidebar-card">
                            <p className="xc-sidebar-heading">
                                Exchanges from this opening ({service.exchanges.length})
                            </p>
                            <div className="xc-participants-list">
                                {service.exchanges.map((x) => (
                                    <div key={x.exchangeId} className="xc-participant xc-opening-exchange">
                                        <Avatar userId={x.accepterId} name={x.accepterName} size={22} />
                                        <Link to={`/exchange?id=${x.exchangeId}`}>{x.accepterName || 'A member'}</Link>
                                        {x.createdAt && <span className="xc-exchange-date">{x.createdAt}</span>}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Previous versions — only those a version-branching edit kept
                        because an exchange was created from them. */}
                    {service.history && service.history.length > 0 && (
                        <div className="xc-sidebar-card">
                            <p className="xc-sidebar-heading">
                                Previous versions ({service.history.length})
                            </p>
                            <div className="xc-version-list">
                                {service.history.map((h) => (
                                    <div key={h.serviceId} className="xc-version-item">
                                        <div className="xc-version-head">
                                            <Link to={`/opening?id=${h.serviceId}`} className="xc-version-title">
                                                v{h.version}: {h.title}
                                            </Link>
                                            {h.createdAt && <span className="xc-exchange-date">{h.createdAt}</span>}
                                        </div>
                                        {h.exchanges.length > 0 && (
                                            <div className="xc-version-exchanges">
                                                {h.exchanges.map((x) => (
                                                    <Link key={x.exchangeId} to={`/exchange?id=${x.exchangeId}`} className="xc-version-exchange-link">
                                                        ↳ exchange with {x.accepterName || 'a member'}
                                                    </Link>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default OpeningPage;
