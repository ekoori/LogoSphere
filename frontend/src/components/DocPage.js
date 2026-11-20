// DocPage — the reading layout for the site's documents (Privacy, Terms,
// Contribute, Donate): an editorial header, an optional "at a glance" box,
// numbered sections with a contents list beside them on wide screens, and
// actions at the end. The words live in the pages; this is only the frame.
import React from 'react';
import PropTypes from 'prop-types';
import '../styles/DocPage.css';

export default function DocPage({ eyebrow, title, lede, updated, glance, glanceTitle = 'At a glance', sections, contents = true, actions }) {
    return (
        <div className="dp-page">
            <header className="dp-hero">
                {eyebrow && <p className="dp-eyebrow">{eyebrow}</p>}
                <h1 className="dp-title">{title}</h1>
                {lede && <p className="dp-lede">{lede}</p>}
                {updated && <p className="dp-updated">Last updated {updated}</p>}
            </header>

            {glance && glance.length > 0 && (
                // Not <aside>: the old sidebar layout styles every aside (sticky, offset).
                <div className="dp-glance" role="note" aria-label={glanceTitle}>
                    <h2>{glanceTitle}</h2>
                    <ul>
                        {glance.map((g) => <li key={g}>{g}</li>)}
                    </ul>
                </div>
            )}

            <div className={`dp-body ${contents ? 'dp-body--contents' : ''}`}>
                {contents && (
                    <nav className="dp-contents" aria-label="On this page">
                        <p>On this page</p>
                        <ol>
                            {sections.map((s) => <li key={s.id}><a href={`#${s.id}`}>{s.title}</a></li>)}
                        </ol>
                    </nav>
                )}
                <div className="dp-sections">
                    {sections.map((s, i) => (
                        <section key={s.id} id={s.id} className="dp-section">
                            <h2>
                                <span className="dp-num" aria-hidden="true">{String(i + 1).padStart(2, '0')}</span>
                                {s.title}
                            </h2>
                            {s.body}
                        </section>
                    ))}
                </div>
            </div>

            {actions && <div className="dp-actions">{actions}</div>}
        </div>
    );
}

DocPage.propTypes = {
    eyebrow: PropTypes.string,
    title: PropTypes.node.isRequired,
    lede: PropTypes.node,
    updated: PropTypes.string,
    glance: PropTypes.arrayOf(PropTypes.string),
    glanceTitle: PropTypes.string,
    sections: PropTypes.arrayOf(PropTypes.shape({
        id: PropTypes.string.isRequired,
        title: PropTypes.string.isRequired,
        body: PropTypes.node.isRequired,
    })).isRequired,
    contents: PropTypes.bool,
    actions: PropTypes.node,
};
