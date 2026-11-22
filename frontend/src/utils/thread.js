// A conversation as it piles up on the page: pages of older messages and each
// poll of the newest merged into one list, oldest first, each message once.
export function mergeMessages(kept, fresh) {
    const byId = new Map(kept.map((m) => [m.id, m]));
    fresh.forEach((m) => byId.set(m.id, m));
    // The server's times are all one format, so they sort as text.
    return [...byId.values()].sort((a, b) => (a.at < b.at ? -1 : a.at > b.at ? 1 : 0));
}

/** The newest of theirs: how far a visit has read. */
export function lastOfTheirs(messages) {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
        if (!messages[i].mine) return messages[i].id;
    }
    return null;
}

/** Where to write to someone, about an opening or not. */
export function messagesHref(personId, openingId = null) {
    return `/messages?with=${personId}${openingId ? `&opening=${openingId}` : ''}`;
}
