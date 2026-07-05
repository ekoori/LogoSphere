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
    };

    return (
        <div className="xc-page xc-page--banner">
            {/* ── Banner ───────────────────────────────────────────────── */}
            <EntityBanner kind="opening" image={service.rawImage} onUpload={isOwnOpening ? handleImageUpload : undefined}>
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
                        <p className="xc-page-section-heading">About this opening</p>
                        <p className="xc-about-text">{service.description}</p>
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
                </div>
            </div>
        </div>
    );
}

export default OpeningPage;
