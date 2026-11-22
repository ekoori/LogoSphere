// Shared mappers from API shapes to card props.
// Used by Home, OpeningsPage, and UserPage.
import { formatServerDate } from './dates';

const IMAGE_BY_KEY = {
    gpu: '/static/h100_cpus.webp',
    garden: '/static/garden_old.webp',
    podcast: '/static/yoga_classes.webp',
    seeds: '/static/garden_new.webp',
    tools: '/static/receipts.png',
    solar: '/static/projects_spheres.png',
};

export function imageForService(imageKey, title = '') {
    if (imageKey && IMAGE_BY_KEY[imageKey]) return IMAGE_BY_KEY[imageKey];
    const t = title.toLowerCase();
    if (t.includes('gpu') || t.includes('h100') || t.includes('compute') || t.includes('dataset')) return IMAGE_BY_KEY.gpu;
    if (t.includes('garden') || t.includes('fence')) return IMAGE_BY_KEY.garden;
    if (t.includes('seed')) return IMAGE_BY_KEY.seeds;
    if (t.includes('tool') || t.includes('repair')) return IMAGE_BY_KEY.tools;
    return '/static/gift_economy.png';
}

// Map a openings service from the API into ServiceCard props.
// Spheres are returned as {id, name} pairs so links use UUID not name.
export function mapService(s) {
    // API returns sphere_id (UUID string) and spheres (array of names) separately.
    const spheres = s.sphere_id && s.spheres && s.spheres.length > 0
        ? [{ id: s.sphere_id, name: s.spheres[0] }]
        : (s.spheres || []).map((name) => ({ id: null, name }));
    return {
        id: s.service_id,
        type: s.type || 'offer',
        title: s.title,
        spheres,
        // The opening's sphere id (if scoped) — used to offer only entities that
        // belong to that sphere when accepting on behalf of one.
        sphereId: s.sphere_id || null,
        provider: s.provider || 'A member',
        providerId: s.provider_id || null,
        // When posted on behalf of an entity, the human who acted.
        actingUser: s.acting_user || null,
        actingUserId: s.acting_user_id || null,
        description: s.description || '',
        project: s.project_name || null,
        projectId: s.project_id || null,
        // A real uploaded photo (served lazily from the opening's /image
        // endpoint) always wins. The bundled keyword-matched illustrations are
        // the demo's only: in a real sphere one would pass for the thing on offer.
        imageUrl: s.has_image ? `/api/openings/${s.service_id}/image`
            : s.is_demo ? imageForService(s.image_key, s.title) : null,
        // The demo's illustrations are AI-drawn too.
        imageIsAi: s.has_image ? !!s.image_is_ai : !!s.is_demo,
        // Whether the opening has a real uploaded banner (vs the fallback).
        hasImage: !!s.has_image,
        // Where, as others may know it: words, a banded distance, and the spot
        // only where it was shown exactly (on the opening's own page).
        location: s.location || null,
        distance: s.distance || null,
        point: s.point || null,
        // Who to write to about it (the opening's own page): a group's is its poster.
        contactId: s.contact_id || null,
        time: fmtDate(s.created_at) || 'recently',
        status: s.status || 'Posted',
        likesCount: s.likes || 0,
        likedBy: s.liked_by || [],
        likedByCurrentUser: s.liked_by_current_user || false,
        canModify: false,
        cadence: s.cadence || 'single',
        acceptedBy: s.accepted_by || null,
        acceptedByName: s.accepted_by_name || null,
        pendingAcceptances: s.pending_acceptances || [],
        myAcceptance: s.my_acceptance || null,
        // Viewer-relative flags from the API: "one of mine" (provider, the
        // human who posted for an entity, or a manager of the providing
        // entity) vs "may manage" (also platform admins). A platform admin can
        // manage any opening without it being their own — so they can still
        // accept it.
        isProvider: !!s.is_provider,
        canManage: !!s.can_manage,
        // The demonstration: from a demo sphere / posted by an AI persona.
        isDemo: !!s.is_demo,
        providerIsAgent: !!s.provider_is_agent,
        // Confirmed exchanges spawned from this opening (single-opening page).
        exchanges: (s.exchanges || []).map((x) => ({
            exchangeId: x.exchange_id,
            accepterId: x.accepter_id,
            accepterName: x.accepter_name,
            createdAt: fmtDate(x.created_at),
        })),
        // Versioning: which version this is, and the previous versions (each
        // frozen because it had a related exchange) with their exchanges.
        version: s.version || 1,
        isCurrent: s.is_current !== false,
        history: (s.history || []).map((h) => ({
            serviceId: h.service_id,
            version: h.version || 1,
            title: h.title,
            description: h.description,
            createdAt: fmtDate(h.created_at),
            exchanges: (h.exchanges || []).map((x) => ({
                exchangeId: x.exchange_id,
                accepterId: x.accepter_id,
                accepterName: x.accepter_name,
                createdAt: fmtDate(x.created_at),
            })),
        })),
        // Per-phase activation dates for the progress bar (single cadence).
        postedAt: fmtDate(s.created_at),
        acceptedAt: fmtDate(s.accepted_at),
        inProgressAt: fmtDate(s.in_progress_at),
        completedAt: fmtDate(s.completed_at),
        // Perpetual openings aggregate many acceptances into one date per phase.
        activity: s.activity ? {
            acceptedCount: s.activity.accepted_count,
            acceptedLastAt: fmtDate(s.activity.accepted_last_at),
            inProgressCount: s.activity.in_progress_count,
            inProgressLastAt: fmtDate(s.activity.in_progress_last_at),
            completedLastAt: fmtDate(s.activity.completed_last_at),
        } : null,
    };
}

// Format an RFC-1123 / ISO datetime into a short readable date (zone-less
// API datetimes are UTC - see utils/dates.js).
export function fmtDate(value) {
    return formatServerDate(value);
}

// Pick a fitting illustration from the bundled static assets based on description keywords.
function imageFor(text = '') {
    const t = text.toLowerCase();
    if (t.includes('fence') || t.includes('garden')) return '/static/garden_old.webp';
    if (t.includes('gpu') || t.includes('h100') || t.includes('compute')) return '/static/h100_cpus.webp';
    if (t.includes('podcast') || t.includes('workshop') || t.includes('class')) return '/static/yoga_classes.webp';
    if (t.includes('solar') || t.includes('microgrid') || t.includes('energy')) return '/static/projects_spheres.png';
    return null;
}

// Map a flat MeaningTrail row from the API into a ExchangeCard item.
// `ownerLabel` names the person this trail belongs to — defaults to 'You' for
// a user's own feed (Home). UserPage passes the profile owner's real name (and
// id, for the participant link) when the person actually viewing the page is
// someone else, so the trail doesn't misleadingly call another person's
// exchange "You".
export function mapExchange(row, { ownerLabel = 'You', ownerId = null } = {}) {
    const completed = ['Finished', 'Completed', 'Receipted', 'Additional Comments Added']
        .includes(row.exchange_status);

    // Like counts arrive keyed by comment_type: {exchange, gratitude, user, other}.
    const likes = row.likes || {};
    const likeOf = (ct) => ({
        likesCount: likes[ct]?.count || 0,
        likedBy: likes[ct]?.by || [],
        likedByCurrentUser: likes[ct]?.liked || false,
        // The server marks what the viewer made: not theirs to appreciate.
        canLike: !likes[ct]?.own,
    });

    // Perspective: an exchange appears in both parties' trails. viewer_is_initiator
    // (relative to the trail owner) tells us who ownerLabel refers to. Receipts
    // are always from the recipient; the personal note is always from the initiator.
    const iAmInitiator = row.viewer_is_initiator !== false;
    const initiatorName = row.initiator_name || 'Initiator';
    const recipientName = row.other_user_name || 'A neighbour';
    // Each side may be a person or a group (alliance/project) — link accordingly.
    const initiatorKind = row.initiator_kind || 'user';
    const recipientKind = row.other_kind || 'user';

    // When the initiator is an entity acted for by a human, show
    // "Joe on behalf of <Entity>". The chip links to the entity's own page when
    // it's a group, else to the person.
    const initiatorActing = row.initiator_acting_user_name || null;
    const initiatorLabel = initiatorActing ? `${initiatorActing} on behalf of ${initiatorName}` : initiatorName;
    const initiatorLinkId = initiatorKind !== 'user' ? (row.initiator_id || null)
        : (initiatorActing ? (row.initiator_acting_user_id || null) : (row.initiator_id || null));

    // Symmetric for the recipient.
    const recipientActing = row.recipient_acting_user_name || null;
    const recipientLabel = recipientActing ? `${recipientActing} on behalf of ${recipientName}` : recipientName;
    const recipientLinkId = recipientKind !== 'user' ? (row.other_user_id || null)
        : (recipientActing ? (row.recipient_acting_user_id || null) : (row.other_user_id || null));

    // The trail-owner side's kind: "You" (a person) unless it's actually a group
    // whose trail this is (an entity page), in which case link to the group.
    const ownerKind = ownerLabel === 'You' ? 'user' : (iAmInitiator ? initiatorKind : recipientKind);
    const ownerLinkId = (ownerKind !== 'user' && ownerLabel !== 'You')
        ? (iAmInitiator ? (row.initiator_id || null) : (row.other_user_id || null))
        : ownerId;

    const receipts = [];
    if (row.gratitude_comment) {
        // The receipt (gratitude) is always authored by the recipient.
        receipts.push({
            author: iAmInitiator ? recipientLabel : ownerLabel,
            authorId: iAmInitiator ? recipientLinkId : (ownerId || null),
            text: row.gratitude_comment,
            time: fmtDate(row.gratitude_comment_timestamp),
            commentType: 'gratitude', ...likeOf('gratitude'), imageUrl: null,
            cards: row.gratitude_comment_cards || [],
        });
    }
    if (row.user_comment) {
        // The personal note is always authored by the initiator.
        receipts.push({
            author: iAmInitiator ? ownerLabel : initiatorName,
            authorId: iAmInitiator ? (ownerId || null) : (row.initiator_id || null),
            text: row.user_comment,
            time: fmtDate(row.user_comment_timestamp),
            commentType: 'user', ...likeOf('user'), imageUrl: null,
            cards: row.user_comment_cards || [],
        });
    }

    // Any number, newest first, as the server gives them.
    const acknowledgements = row.acknowledgements || [];

    return {
        id: row.exchange_id,
        type: completed ? 'completed' : 'offer',
        title: row.exchange_description || 'An exchange of trust',
        // meaning_trail rows have no sphere FK — project shown separately
        spheres: [],
        participants: iAmInitiator
            ? [
                { name: ownerLabel, id: ownerLinkId, kind: ownerKind, isAgent: !!row.initiator_is_agent },
                ...(row.other_user_name ? [{ name: recipientLabel, id: recipientLinkId, kind: recipientKind, isAgent: !!row.other_is_agent }] : []),
            ]
            : [
                { name: initiatorLabel, id: initiatorLinkId, kind: initiatorKind, isAgent: !!row.initiator_is_agent },
                { name: ownerLabel, id: ownerLinkId, kind: ownerKind, isAgent: !!row.other_is_agent },
            ],
        isDemo: !!row.is_demo,
        // Only what the people wrote - no generated stand-in.
        description: row.exchange_long_description || '',
        project: row.project_name || null,
        projectId: row.project_id || null,
        // A trail is evidence. Demo spheres may have AI-made evidence, so they keep
        // their illustrations; a real exchange shows only its own picture.
        imageUrl: row.has_image ? `/api/exchange/${row.exchange_id}/image`
            : row.is_demo ? imageFor(row.exchange_description) : null,
        imageIsAi: row.has_image ? !!row.image_is_ai : !!(row.is_demo && imageFor(row.exchange_description)),
        time: fmtDate(row.project_start_timestamp) || 'recently',
        status: row.exchange_status || 'Initiated',
        ...likeOf('exchange'),
        initiatedTime: fmtDate(row.project_start_timestamp),
        inProgressTime: '',
        finishedTime: '',
        receiptedTime: '',
        additionalCommentsTime: fmtDate(row.initiator_comment_timestamp || row.recipient_comment_timestamp),
        // Presence of either follow-up note is what reveals the 5th progress-bar
        // step — it's only offered once both sides have receipted.
        hasFollowupComment: !!(row.initiator_comment || row.recipient_comment),
        receipts,
        acknowledgements,
        // Whether each side has written theirs (ExchangeCard offers the viewer their own).
        hasNote: !!row.user_comment,
        hasReceipt: !!row.gratitude_comment,
    };
}
