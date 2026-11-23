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

/** Where to write to someone: about nothing, an opening (its id) or anything ({kind, id}). */
export function messagesHref(personId, about = null) {
    if (!about) return `/messages?with=${personId}`;
    if (typeof about === 'string') return `/messages?with=${personId}&opening=${about}`;
    return `/messages?with=${personId}&about=${about.kind}:${about.id}`;
}

/** What a message is about, as {title, link}: older ones name only an opening. */
export function subjectOf(message) {
    if (message?.about) return message.about;
    if (message?.opening) return { ...message.opening, kind: 'opening', link: `/opening?id=${message.opening.id}` };
    return null;
}
