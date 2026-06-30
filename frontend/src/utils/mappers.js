// Shared mappers from API shapes to card props.
// Used by Home, MarketplacePage, and UserPage.

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

// Map a marketplace service from the API into ServiceCard props.
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
        provider: s.provider || 'A member',
        providerId: s.provider_id || null,
        description: s.description || '',
        project: s.project_name || null,
        imageUrl: imageForService(s.image_key, s.title),
        time: 'recently',
        status: s.status || 'Posted',
        likesCount: s.likes || 0,
        likedByCurrentUser: false,
        canModify: false,
    };
}

// Format an RFC-1123 / ISO datetime into a short readable date.
export function fmtDate(value) {
    if (!value) return '';
    const d = new Date(value);
    if (isNaN(d.getTime())) return '';
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
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

// Map a flat MeaningTrail row from the API into a InteractionCard item.
export function mapInteraction(row) {
    const completed = ['Finished', 'Completed', 'Receipted', 'Additional Comments Added']
        .includes(row.interaction_status);

    const receipts = [];
    if (row.gratitude_comment) {
        receipts.push({
            author: row.other_user_name || 'A neighbour',
            text: row.gratitude_comment,
            time: fmtDate(row.gratitude_comment_timestamp),
            likesCount: 0, likedByCurrentUser: false, imageUrl: null,
        });
    }
    if (row.user_comment) {
        receipts.push({
            author: 'You',
            text: row.user_comment,
            time: fmtDate(row.user_comment_timestamp),
            likesCount: 0, likedByCurrentUser: false, imageUrl: null,
        });
    }

    const shoutouts = [];
    if (row.other_comment) {
        shoutouts.push({
            author: row.other_comment_author_name || 'A neighbour',
            text: row.other_comment,
            time: fmtDate(row.other_comment_timestamp),
            likesCount: 0, likedByCurrentUser: false,
        });
    }

    return {
        id: row.interaction_id,
        type: completed ? 'completed' : 'offer',
        title: row.interaction_description || 'An exchange of trust',
        // meaning_trail rows have no sphere FK — project shown separately
        spheres: [],
        participants: [
            { name: 'You', id: null },
            ...(row.other_user_name ? [{ name: row.other_user_name, id: row.other_user_id }] : []),
        ],
        description: row.project_name
            ? `An act of giving within the "${row.project_name}" project.`
            : 'A moment of trust shared in the community.',
        project: row.project_name || null,
        projectId: row.project_id || null,
        imageUrl: imageFor(row.interaction_description),
        time: fmtDate(row.project_start_timestamp) || 'recently',
        status: row.interaction_status || 'Initiated',
        likesCount: 0,
        likedByCurrentUser: false,
        initiatedTime: fmtDate(row.project_start_timestamp),
        inProgressTime: '',
        finishedTime: '',
        receiptedTime: '',
        additionalCommentsTime: '',
        receipts,
        shoutouts,
        canModify: false,
        onAddReceipt: () => {},
        onAddShoutout: () => {},
        onModifyInteraction: () => {},
    };
}
