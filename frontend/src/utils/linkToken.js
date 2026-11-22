// The token an emailed link carries in its fragment ("#token=…", or bare, as
// the unsubscribe link has it). A fragment never reaches a server's log.
export function tokenFromHash(hash) {
    const text = (hash || '').replace(/^#/, '');
    const named = /(?:^|&)token=([\w.-]+)/.exec(text);
    if (named) return named[1];
    return /^[\w.-]+$/.test(text) ? text : '';
}
