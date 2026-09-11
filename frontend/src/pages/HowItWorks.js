// HowItWorks — the plain-language companion to About.
// About argues the philosophy (why meaning collapses, Thick Models of Value).
// This page skips the philosophy and just shows the mechanism: what you post,
// what happens, what you get. Written for someone hearing about LogoSphere
// for the first time in a community meeting, not someone reading a manifesto.

import React from 'react';
import { Link } from 'react-router-dom';
import '../styles/HowItWorks.css';

const TODAY = [
    {
        glyph: '💬',
        title: 'The group chat',
        note: 'Someone asks for a hand. Three people reply. By tomorrow it’s buried under forty other messages.',
    },
    {
        glyph: '📋',
        title: 'The spreadsheet',
        note: 'Somebody’s job to update it. They get busy. Six months later nobody trusts the numbers in it.',
    },
    {
        glyph: '🤝',
        title: 'A word of thanks',
        note: 'Real, and it matters in the moment — but by dinner, there’s no trace it happened at all.',
    },
];

const STEPS = [
    {
        title: 'Post it',
        desc: 'Need a hand, or got one to give? Say so in a sentence — an Offer or a Need. It shows up on your group’s board, not the whole internet.',
    },
    {
        title: 'Someone says yes',
        desc: 'A member of your group accepts. You work out the when and where together, same as you always would.',
    },
    {
        title: 'You do the thing',
        desc: 'Fix the fence, watch the kids, lend the drill, drive someone to an appointment — whatever it actually is, in real life, off the app.',
    },
    {
        title: 'Say thanks, both ways',
        desc: 'The person who was helped writes a Receipt — a real thank-you, not a star rating: what happened, what it meant, maybe a photo. The helper can leave a short note back.',
    },
    {
        title: 'It joins the trail',
        desc: 'That receipt becomes part of both people’s Meaning Trail — a running, visible record of what they’ve given and received in your group.',
    },
];

const TERMS = [
    { term: 'Offers & Needs', gloss: 'The board. Say what you can give, or what you’re looking for.' },
    { term: 'Sphere', gloss: 'Your group’s own space — the neighbourhood, the club, the congregation. Private to it unless you say otherwise.' },
    { term: 'Exchange', gloss: 'The record of one specific act of help, start to finish.' },
    { term: 'Receipt', gloss: 'A real thank-you with substance — what happened and what it meant. Not a star rating.' },
    { term: 'Meaning Trail', gloss: 'Your history — everything you’ve given and received, in order, visible to your group.' },
    { term: 'Value Card', gloss: 'Optional. A short note on what you personally care about, so people find kindred spirits, not just favours.' },
];

const COMPARE = [
    { name: 'Group chat', note: 'Fast to post. Gone by tomorrow. No record of what actually happened.' },
    { name: 'Nextdoor / Marketplace', note: 'Built for selling things and airing complaints — not for organised giving.' },
    { name: 'A spreadsheet', note: 'Someone has to maintain it by hand. Just numbers — no story behind them.' },
    { name: 'LogoSphere', note: 'Builds itself as help actually happens. The story stays attached to the record.', highlight: true },
];

const FAQ = [
    {
        q: 'Does money change hands?',
        a: 'No. LogoSphere is for help freely given — a fence fixed, a ride offered, an afternoon of childcare. If people sometimes call this a “gift economy,” that’s the plain meaning of the term: helping, no money involved.',
    },
    {
        q: 'Do I have to write a receipt every single time?',
        a: 'No — but it’s the whole mechanism. It’s how the person who helped actually gets seen, and how your group’s trail grows into something worth looking at.',
    },
    {
        q: 'Is any of this visible outside our group?',
        a: 'Not unless your group chooses it. A Sphere is private to the people in it, and nothing you post is searchable by strangers on the open internet — unless the sphere’s admin explicitly switches on “public activity”, in which case its projects, alliances and openings become viewable by anyone.',
    },
    {
        q: 'What if I just want to watch for now?',
        a: 'That’s completely fine. You can see what’s being offered and needed before you ever post anything yourself.',
    },
    {
        q: 'Isn’t this just one more app to manage?',
        a: 'It’s meant to replace the digging-through-the-group-chat step, not add to it — one place where who-needs-what and who’s-already-helping actually lives.',
    },
];

const HowItWorks = () => {
    return (
        <div className="hiw-page">
            {/* ── Hero ─────────────────────────────────────────────────────── */}
            <header className="hiw-hero ts-rise">
                <div className="hiw-hero-trail" aria-hidden="true">
                    <svg viewBox="0 0 560 320" preserveAspectRatio="xMidYMid slice">
                        <path
                            className="hiw-trail-path"
                            d="M40 280 C 140 260, 120 190, 210 175 S 340 120, 320 70 S 460 30, 520 45"
                            fill="none"
                        />
                        <circle className="hiw-trail-dot" cx="40" cy="280" r="6" />
                        <circle className="hiw-trail-dot" cx="210" cy="175" r="6" style={{ animationDelay: '0.6s' }} />
                        <circle className="hiw-trail-dot" cx="320" cy="70" r="6" style={{ animationDelay: '1.2s' }} />
                        <circle className="hiw-trail-dot" cx="520" cy="45" r="6" style={{ animationDelay: '1.8s' }} />
                    </svg>
                </div>

                <p className="hiw-eyebrow">LogoSphere · in plain terms</p>
                <h1 className="hiw-hero-title">
                    Favors, <em>remembered</em> — <br />not lost in a chat thread.
                </h1>
                <p className="hiw-lead">
                    Every week your group asks for help, offers help, and says thanks — and then it
                    vanishes into a scroll of messages nobody will find again. LogoSphere gives that a
                    home: a simple way to ask, to offer, to say a real thank-you, and to keep a record
                    of it that your whole group can see growing.
                </p>
                <div className="hiw-hero-actions">
                    <a href="#trail" className="btn btn-accent">See how it works ↓</a>
                    <Link to="/about" className="hiw-hero-link">Want the bigger idea behind it? →</Link>
                </div>
            </header>

            {/* ── The gap ──────────────────────────────────────────────────── */}
            <section className="hiw-section ts-rise" style={{ '--i': 1 }}>
                <div className="hiw-section-head">
                    <span className="hiw-kicker">The real problem</span>
                    <h2>It isn’t the people. It’s the memory.</h2>
                </div>
                <p className="hiw-prose">
                    Most communities are already generous — help happens all the time. What’s missing
                    isn’t willingness, it’s a place for it to live afterward. Here’s where it usually
                    goes to die:
                </p>

                <div className="hiw-today-grid">
                    {TODAY.map((t) => (
                        <div key={t.title} className="hiw-today-card">
                            <span className="hiw-today-glyph" aria-hidden="true">{t.glyph}</span>
                            <h3>{t.title}</h3>
                            <p>{t.note}</p>
                        </div>
                    ))}
                </div>

                <div className="hiw-gap-fix">
                    <span className="hiw-gap-fix-arrow" aria-hidden="true">↓</span>
                    <p>One shared trail your whole group can actually see, that builds itself as help happens.</p>
                </div>
            </section>

            {/* ── The five steps ───────────────────────────────────────────── */}
            <section id="trail" className="hiw-section ts-rise" style={{ '--i': 2 }}>
                <div className="hiw-section-head">
                    <span className="hiw-kicker">How it actually works</span>
                    <h2>Five steps, start to finish</h2>
                </div>

                <ol className="hiw-steps">
                    {STEPS.map((s, i) => (
                        <li key={s.title} className="hiw-step" style={{ '--i': i }}>
                            <span className="hiw-step-marker">{i + 1}</span>
                            <div className="hiw-step-body">
                                <h3>{s.title}</h3>
                                <p>{s.desc}</p>
                            </div>
                        </li>
                    ))}
                </ol>
            </section>

            {/* ── Concrete walkthrough ─────────────────────────────────────── */}
            <section className="hiw-section ts-rise" style={{ '--i': 3 }}>
                <div className="hiw-section-head">
                    <span className="hiw-kicker">A real example</span>
                    <h2>Maria’s fence</h2>
                </div>
                <p className="hiw-prose">
                    Maria’s back fence has a hole a dog could get through. Tom, three doors down, is a
                    retired carpenter who’s handy with exactly this. Here’s what that looks like, start
                    to finish.
                </p>

                <div className="hiw-mock-row">
                    <div className="hiw-mock-card">
                        <span className="hiw-mock-label">1 · Maria posts a Need</span>
                        <div className="hiw-mock-inner">
                            <span className="hiw-mock-pill hiw-mock-pill--need">Need</span>
                            <p className="hiw-mock-title">Fence repair, west side</p>
                            <p className="hiw-mock-body">“One panel’s broken through — dog-sized hole. Any help this week appreciated!”</p>
                            <div className="hiw-mock-avatar-row">
                                <span className="hiw-mock-avatar" data-name="M">M</span>
                                <span className="hiw-mock-name">Maria · Oakview Neighbours</span>
                            </div>
                        </div>
                    </div>

                    <div className="hiw-mock-arrow" aria-hidden="true">→</div>

                    <div className="hiw-mock-card">
                        <span className="hiw-mock-label">2 · Tom accepts</span>
                        <div className="hiw-mock-inner">
                            <span className="hiw-mock-pill hiw-mock-pill--accept">Accepted</span>
                            <p className="hiw-mock-title">Tom can help</p>
                            <p className="hiw-mock-body">“Got a spare panel in the garage actually. Saturday morning work?”</p>
                            <div className="hiw-mock-avatar-row">
                                <span className="hiw-mock-avatar" data-name="T">T</span>
                                <span className="hiw-mock-name">Tom · confirmed</span>
                            </div>
                        </div>
                    </div>

                    <div className="hiw-mock-arrow" aria-hidden="true">→</div>

                    <div className="hiw-mock-card hiw-mock-card--receipt">
                        <span className="hiw-mock-label">3 · Maria’s Receipt</span>
                        <div className="hiw-mock-inner">
                            <span className="hiw-mock-pill hiw-mock-pill--receipt">✓ Receipt</span>
                            <p className="hiw-mock-body hiw-mock-quote">
                                “Fixed it in under two hours — and showed me how to do the next repair myself.
                                That’s the kind of neighbour I hope to be too.”
                            </p>
                            <div className="hiw-mock-avatar-row">
                                <span className="hiw-mock-avatar" data-name="M">M</span>
                                <span className="hiw-mock-name">Maria, about Tom</span>
                            </div>
                        </div>
                    </div>
                </div>

                <p className="hiw-story-outcome">
                    That’s it. Two neighbours, one fence, one honest thank-you — and now it’s a permanent
                    part of both of their trails, visible to everyone in Oakview Neighbours.
                </p>
            </section>

            {/* ── Glossary of mechanisms ───────────────────────────────────── */}
            <section className="hiw-section ts-rise" style={{ '--i': 4 }}>
                <div className="hiw-section-head">
                    <span className="hiw-kicker">The moving parts</span>
                    <h2>Six words you’ll see in the app</h2>
                </div>

                <ul className="hiw-terms">
                    {TERMS.map((t) => (
                        <li key={t.term} className="hiw-term">
                            <h3>{t.term}</h3>
                            <p>{t.gloss}</p>
                        </li>
                    ))}
                </ul>
            </section>

            {/* ── Benefits: members / organizers ───────────────────────────── */}
            <section className="hiw-section ts-rise" style={{ '--i': 5 }}>
                <div className="hiw-section-head">
                    <span className="hiw-kicker">Why bother</span>
                    <h2>What you actually get out of it</h2>
                </div>

                <div className="hiw-benefit-columns">
                    <div className="hiw-benefit-col">
                        <h3>If you’re a member</h3>
                        <ul>
                            <li>Get recognised for what you actually did — not just a “like.”</li>
                            <li>Build a track record people in your group can see and trust.</li>
                            <li>No awkward conversation about money — it was never on the table.</li>
                            <li>Find people who care about the same things you do, not just favours.</li>
                        </ul>
                    </div>
                    <div className="hiw-benefit-col">
                        <h3>If you help run the group</h3>
                        <ul>
                            <li>Replace the WhatsApp archaeology with a place things actually live.</li>
                            <li>New members can see what your group does just by scrolling.</li>
                            <li>Ready-made evidence when you need to show real impact — a grant form, an annual report, a volunteer thank-you night.</li>
                            <li>Nobody has to be the one maintaining a spreadsheet by hand.</li>
                        </ul>
                    </div>
                </div>
            </section>

            {/* ── Comparison ────────────────────────────────────────────────── */}
            <section className="hiw-section ts-rise" style={{ '--i': 6 }}>
                <div className="hiw-section-head">
                    <span className="hiw-kicker">Not another app to manage</span>
                    <h2>How this is different</h2>
                </div>

                <div className="hiw-compare-list">
                    {COMPARE.map((c) => (
                        <div key={c.name} className={`hiw-compare-row ${c.highlight ? 'hiw-compare-row--highlight' : ''}`}>
                            <span className="hiw-compare-name">{c.name}</span>
                            <span className="hiw-compare-note">{c.note}</span>
                        </div>
                    ))}
                </div>
            </section>

            {/* ── FAQ ──────────────────────────────────────────────────────── */}
            <section className="hiw-section ts-rise" style={{ '--i': 7 }}>
                <div className="hiw-section-head">
                    <span className="hiw-kicker">Quick answers</span>
                    <h2>What people ask first</h2>
                </div>

                <div className="hiw-faq-list">
                    {FAQ.map((f) => (
                        <details key={f.q} className="hiw-faq-item">
                            <summary>
                                <span>{f.q}</span>
                                <span className="hiw-faq-icon" aria-hidden="true" />
                            </summary>
                            <p>{f.a}</p>
                        </details>
                    ))}
                </div>
            </section>

            {/* ── CTA ──────────────────────────────────────────────────────── */}
            <section className="hiw-join ts-rise" style={{ '--i': 8 }}>
                <p className="hiw-kicker">Bring it to your group</p>
                <h2>Try it with the people you already trust.</h2>
                <p className="hiw-prose hiw-prose--center">
                    Start small — one sphere, a handful of neighbours or members. The trail builds
                    itself from there.
                </p>
                <div className="hiw-join-actions">
                    <Link to="/register" className="btn btn-accent hiw-btn-lg">Join LogoSphere</Link>
                    <Link to="/about" className="btn btn-ghost hiw-btn-lg">Read the philosophy</Link>
                </div>
            </section>
        </div>
    );
};

export default HowItWorks;
