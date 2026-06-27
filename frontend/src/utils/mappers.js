// Shared mappers from API shapes to card props (used by Home & MarketplacePage).

// Map a service's image_key (or title) to a bundled static asset.
const IMAGE_BY_KEY = {
    gpu: '/static/h100_cpus.webp',
    garden: '/static/garden_old.webp',
    podcast: '/static/yoga_classes.webp',
    seeds: '/static/garden_new.webp',
    tools: '/static/trustifacts.png',
    solar: '/static/projects_spheres.png',
};

export function imageForService(imageKey, title = '') {
    if (imageKey && IMAGE_BY_KEY[imageKey]) return IMAGE_BY_KEY[imageKey];
    const t = title.toLowerCase();
    if (t.includes('gpu') || t.includes('h100') || t.includes('compute') || t.includes('dataset')) return IMAGE_BY_KEY.gpu;
    if (t.includes('garden') || t.includes('fence')) return IMAGE_BY_KEY.garden;
    if (t.includes('seed')) return IMAGE_BY_KEY.seeds;
    if (t.includes('tool') || t.includes('repair')) return IMAGE_BY_KEY.tools;
    return '/static/gift_economy.png'; // default
}

// Map a marketplace service from the API into ServiceCard props.
export function mapService(s) {
    return {
        id: s.service_id,
        type: s.type || 'offer',
        title: s.title,
        spheres: s.spheres || [],
        provider: s.provider || 'A member',
        providerId: s.provider_id || null,
        description: s.description || '',
        project: s.project_name || null,
        imageUrl: imageForService(s.image_key, s.title),
        time: 'recently',
        status: s.status || 'Posted',
        likesCount: s.likes || 0,
        likedByCurrentUser: false,
        relatedTransactions: [],
        canModify: false,
    };
}
