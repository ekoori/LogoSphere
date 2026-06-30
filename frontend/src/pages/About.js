// About — a manifesto for a meaning-based economy.
// Long-form, editorial. Argues from the problem (value collapses into thin
// proxies) toward the design idea (Thick Models of Value → Value Cards →
// Frankl's three modes of meaning) and how it threads through the platform.

import React, { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import '../styles/About.css';

// What a Thick Model of Value keeps that a metric throws away.
const PRESERVES = [
    { k: 'Reasons', d: 'The “because” behind a choice — not only the choice itself.' },
    { k: 'Endorsement', d: 'What you’d still choose after reflection, told apart from impulse.' },
    { k: 'Context & roles', d: 'The promises, boundaries, and obligations a situation carries.' },
    { k: 'Trade-offs', d: 'Priorities, thresholds, and the lines you will not cross.' },
    { k: 'Collective goods', d: 'Trust, legitimacy, the commons no single person holds.' },
    { k: 'Endorsed change', d: 'Growth you would affirm — distinguished from drift and capture.' },
];

// Viktor Frankl's three avenues to meaning, each with a lived example.
const MODES = [
    {
        tag: 'Creative',
        glyph: '✶',
        gloss: 'what you make and give',
        ex: '“I rebuilt the tool library’s catalogue so anyone can find what to borrow.”',
    },
    {
        tag: 'Experiential',
        glyph: '❍',
        gloss: 'what you receive and encounter',
        ex: '“Sitting with a neighbour as she learned to sharpen her grandfather’s plane.”',
    },
    {
        tag: 'Attitudinal',
        glyph: '△',
        gloss: 'the stance you take under constraint',
        ex: '“We kept the repair café free, even when keeping it open got hard.”',
    },
];

// How existing LogoSphere primitives deepen under a meaning lens.
const MAPPING = [
    {
        from: 'Meaning Graph',
        to: 'Meaning Graph',
        d: 'A profile holds a handful of Value Cards instead of a tag cloud — what you care about, and why.',
    },
    {
        from: 'Receipt',
        to: 'Meaning Receipt',
        d: 'A record of exchange that names the value it expressed, what it cost, and the receiver’s endorsement.',
    },
    {
        from: 'Acknowledgement',
        to: 'Light signal',
        d: 'Public thanks stays lightweight — warmth, not currency. The weight-bearing work belongs to receipts.',
    },
    {
        from: 'Sphere & Project',
        to: 'Norm bundle + drift clause',
        d: 'A community declares its shared values — and a “we’re drifting if…” clause to catch its own slide.',
    },
    {
        from: 'Openings',
        to: 'Meaning-tagged exchange',
        d: 'Offers and needs carry the values they serve; matching favours overlaps that are endorsed and evidenced.',
    },
];

// The CLEAR mnemonic — the anatomy of a Value Card.
const CLEAR = [
    { l: 'C', w: 'Concrete', d: 'behaviours you can actually see' },
    { l: 'L', w: 'Levers & limits', d: 'trade-offs and boundaries' },
    { l: 'E', w: 'Endorsement', d: 'chosen on reflection, not impulse' },
    { l: 'A', w: 'Anti-signals', d: 'what drift looks like' },
    { l: 'R', w: 'Review', d: 'revisited on a cadence' },
];

const About = () => {
    const rootRef = useRef(null);

    // Scroll-triggered reveals. We arm the hidden state only once JS runs, then
    // guarantee the page can never stay hidden: in-view content reveals on the
    // next frame (so the entrance animation plays), IntersectionObserver handles
    // the scroll stagger, and a fallback timer + visibility listener catch any
    // environment where the observer never fires (e.g. a backgrounded tab).
    useEffect(() => {
        const root = rootRef.current;
        if (!root) return;
        root.classList.add('is-armed');
        const els = Array.from(root.querySelectorAll('.ab-reveal'));
        const reveal = (el) => el.classList.add('is-visible');

        const revealInView = () => {
            els.forEach((el) => {
                if (el.getBoundingClientRect().top < window.innerHeight * 0.92) reveal(el);
            });
        };

        const raf = requestAnimationFrame(revealInView);

        let io;
        if ('IntersectionObserver' in window) {
            io = new IntersectionObserver(
                (entries, obs) => {
                    entries.forEach((e) => {
                        if (e.isIntersecting) {
                            reveal(e.target);
                            obs.unobserve(e.target);
                        }
                    });
                },
                { threshold: 0.14, rootMargin: '0px 0px -6% 0px' }
            );
            els.forEach((el) => io.observe(el));
        } else {
            els.forEach(reveal);
        }

        const onShow = () => { if (document.visibilityState === 'visible') revealInView(); };
        document.addEventListener('visibilitychange', onShow);
        const fallback = setTimeout(() => els.forEach(reveal), 1400);

        return () => {
            cancelAnimationFrame(raf);
            if (io) io.disconnect();
            clearTimeout(fallback);
            document.removeEventListener('visibilitychange', onShow);
        };
    }, []);

    return (
        <div className="ab-page" ref={rootRef}>
            {/* ── Hero / thesis ──────────────────────────────────────────── */}
            <header className="ab-hero ab-reveal">
                <div className="ab-hero-graph" aria-hidden="true">
                    <svg viewBox="0 0 600 360" preserveAspectRatio="xMidYMid slice">
                        <g className="ab-graph-edges">
                            <line x1="90" y1="70" x2="250" y2="140" />
                            <line x1="250" y1="140" x2="430" y2="80" />
                            <line x1="250" y1="140" x2="360" y2="270" />
                            <line x1="430" y1="80" x2="540" y2="190" />
                            <line x1="360" y1="270" x2="180" y2="300" />
                            <line x1="90" y1="70" x2="180" y2="300" />
                            <line x1="540" y1="190" x2="360" y2="270" />
                        </g>
                        <g className="ab-graph-nodes">
                            <circle cx="90" cy="70" r="7" />
                            <circle cx="250" cy="140" r="11" />
                            <circle cx="430" cy="80" r="8" />
                            <circle cx="360" cy="270" r="9" />
                            <circle cx="540" cy="190" r="6" />
                            <circle cx="180" cy="300" r="7" />
                        </g>
                    </svg>
                </div>

                <p className="ab-eyebrow">LogoSphere · a meaning-based economy</p>
                <h1 className="ab-hero-title">
                    An economy that<br />remembers <em>why.</em>
                </h1>
                <p className="ab-lead">
                    Every system that scales human cooperation must compress what people care about into
                    something it can move around. Money does it with price. Platforms do it with clicks.
                    Each translation is lossy — and what leaks away is the meaning. LogoSphere is an
                    attempt to keep it.
                </p>
            </header>

            {/* ── 01 · The collapse of value ─────────────────────────────── */}
            <section className="ab-section ab-reveal">
                <div className="ab-section-head">
                    <span className="ab-num">01</span>
                    <h2>When value collapses</h2>
                </div>
                <div className="ab-prose">
                    <p>
                        Tell a community its worth is a number, and it will manufacture the number. This is
                        Goodhart’s trap: <em>when a measure becomes a target, it stops being a good measure.</em>{' '}
                        Likes, daily-active-users, reputation points — thin proxies are easy to optimise
                        precisely because they’ve already discarded the reasons underneath them.
                    </p>
                    <p>
                        A meaning-centric platform inherits a sharper version of the same risk. The moment
                        meaning can be cashed in, people optimise for <em>appearing</em> meaningful. The
                        proxy doesn’t just mislead — it crowds out the thing it was meant to stand for.
                    </p>
                </div>

                <div className="ab-collapse" aria-hidden="false">
                    <div className="ab-collapse-side ab-collapse-thin">
                        <span className="ab-collapse-tag">Thin proxy</span>
                        <div className="ab-metrics">
                            <span className="ab-metric">♥ 2,431</span>
                            <span className="ab-metric">DAU 18.2k</span>
                            <span className="ab-metric">★ 4.9</span>
                            <span className="ab-metric">pts 1,290</span>
                        </div>
                        <p className="ab-collapse-note">Easy to move. Easy to fake. Blind to why.</p>
                    </div>

                    <div className="ab-collapse-arrow" aria-hidden="true">
                        <span>becomes</span>
                        <svg viewBox="0 0 48 24" width="48" height="24">
                            <path d="M2 12 H40 M32 5 L42 12 L32 19" fill="none" />
                        </svg>
                    </div>

                    <div className="ab-collapse-side ab-collapse-thick">
                        <span className="ab-collapse-tag ab-collapse-tag--thick">Thick value</span>
                        <p className="ab-thick-line">
                            <strong>Tools stay alive in the neighbourhood</strong> — repaired and shared,
                            not landfilled — <em>because the labour already inside a thing shouldn’t be
                            thrown away.</em>
                        </p>
                        <p className="ab-collapse-note">Hard to fake. Carries its own reasons.</p>
                    </div>
                </div>
            </section>

            {/* ── 02 · Thick Models of Value ─────────────────────────────── */}
            <section className="ab-section ab-reveal">
                <div className="ab-section-head">
                    <span className="ab-num">02</span>
                    <h2>Thick Models of Value</h2>
                </div>
                <div className="ab-prose">
                    <p>
                        A <strong>Thick Model of Value</strong> is a representation rich enough to survive
                        being optimised. Where a preference records <em>what</em> you chose, and a written
                        rule records <em>what’s allowed</em>, a TMV carries the <em>why</em> — and the
                        texture around it.
                    </p>
                </div>

                <ul className="ab-preserves">
                    {PRESERVES.map((p, i) => (
                        <li key={p.k} className="ab-preserve" style={{ '--i': i }}>
                            <h3>{p.k}</h3>
                            <p>{p.d}</p>
                        </li>
                    ))}
                </ul>

                <p className="ab-ladder-caption">
                    A ladder of fidelity — each rung keeps more of what mattered:
                </p>
                <ol className="ab-ladder">
                    <li><span className="ab-rung-k">Preferences</span><span className="ab-rung-d">what — utilities, rankings</span></li>
                    <li><span className="ab-rung-k">Values-as-text</span><span className="ab-rung-d">policies you can lawyer around</span></li>
                    <li className="ab-rung-top"><span className="ab-rung-k">Thick value</span><span className="ab-rung-d">reasons, endorsement, context</span></li>
                </ol>
            </section>

            {/* ── 03 · The Value Card ────────────────────────────────────── */}
            <section className="ab-section ab-reveal">
                <div className="ab-section-head">
                    <span className="ab-num">03</span>
                    <h2>The Value Card</h2>
                </div>
                <div className="ab-prose">
                    <p>
                        To be usable by humans, a thick value compresses into a card — a small, honest
                        artefact you could read in ten seconds and recognise as your own.
                    </p>
                </div>

                <div className="ab-card-row">
                    <article className="ab-valuecard">
                        <span className="ab-valuecard-punch" aria-hidden="true" />
                        <div className="ab-vc-field">
                            <span className="ab-vc-label">I care about</span>
                            <p>Tools staying alive in the neighbourhood — repaired, shared, not landfilled.</p>
                        </div>
                        <div className="ab-vc-field">
                            <span className="ab-vc-label">Because</span>
                            <p>Throwing away a fixable thing wastes the care and labour already inside it.</p>
                        </div>
                        <div className="ab-vc-field">
                            <span className="ab-vc-label">Looks like</span>
                            <p>Running the Saturday repair café · teaching the fix, not just doing it · lending freely.</p>
                        </div>
                        <div className="ab-vc-field ab-vc-drift">
                            <span className="ab-vc-label">Drift looks like</span>
                            <p>Hoarding the best tools · counting repairs for status · skipping the teaching to save time.</p>
                        </div>
                        <div className="ab-vc-field">
                            <span className="ab-vc-label">In conflict, I prioritise</span>
                            <p>Teaching someone over finishing faster.</p>
                        </div>
                        <div className="ab-vc-field ab-vc-never">
                            <span className="ab-vc-label">Never</span>
                            <p>Charging for access to shared tools.</p>
                        </div>
                    </article>

                    <div className="ab-clear">
                        <p className="ab-clear-title">CLEAR values</p>
                        <ul>
                            {CLEAR.map((c) => (
                                <li key={c.l}>
                                    <span className="ab-clear-letter">{c.l}</span>
                                    <span className="ab-clear-text">
                                        <strong>{c.w}</strong> — {c.d}
                                    </span>
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>
            </section>

            {/* ── 04 · Three kinds of meaning ────────────────────────────── */}
            <section className="ab-section ab-reveal">
                <div className="ab-section-head">
                    <span className="ab-num">04</span>
                    <h2>Three kinds of meaning</h2>
                </div>
                <div className="ab-prose">
                    <p>
                        Meaning isn’t pleasure, and it isn’t status. Following Viktor Frankl, it arrives by
                        three routes — and a healthy ledger can tell them apart.
                    </p>
                </div>

                <div className="ab-modes">
                    {MODES.map((m, i) => (
                        <article key={m.tag} className="ab-mode" style={{ '--i': i }}>
                            <span className="ab-mode-glyph" aria-hidden="true">{m.glyph}</span>
                            <h3>{m.tag}</h3>
                            <p className="ab-mode-gloss">{m.gloss}</p>
                            <p className="ab-mode-ex">{m.ex}</p>
                        </article>
                    ))}
                </div>
            </section>

            {/* ── 05 · Meaning, woven into the platform ──────────────────── */}
            <section className="ab-section ab-reveal">
                <div className="ab-section-head">
                    <span className="ab-num">05</span>
                    <h2>Woven into the platform</h2>
                </div>
                <div className="ab-prose">
                    <p>
                        None of this is a rewrite. LogoSphere already speaks in profiles, Receipts,
                        acknowledgements, spheres, and a gift-economy openings. A meaning lens simply lets each
                        primitive carry more of the truth it was always reaching for.
                    </p>
                </div>

                <ul className="ab-mapping">
                    {MAPPING.map((m, i) => (
                        <li key={m.from} className="ab-map-row" style={{ '--i': i }}>
                            <span className="ab-map-from">{m.from}</span>
                            <span className="ab-map-arrow" aria-hidden="true">→</span>
                            <span className="ab-map-to">{m.to}</span>
                            <p className="ab-map-d">{m.d}</p>
                        </li>
                    ))}
                </ul>
            </section>

            {/* ── 06 · Endorsed, not performed ───────────────────────────── */}
            <section className="ab-section ab-section--quote ab-reveal">
                <blockquote className="ab-quote">
                    <p>“If meaning becomes a currency, it will be optimised.”</p>
                </blockquote>
                <div className="ab-prose ab-prose--center">
                    <p>
                        So the whole design turns on one distinction. <strong>Endorsed meaning</strong> is
                        what holds up under reflection and deliberation. <strong>Performed meaning</strong>{' '}
                        is status play wearing meaning’s clothes. Every mechanism here — receipts over
                        points, reasons over scores, drift clauses over leaderboards — exists to keep the
                        first from collapsing into the second.
                    </p>
                </div>
            </section>

            {/* ── Join ───────────────────────────────────────────────────── */}
            <section className="ab-join ab-reveal">
                <p className="ab-eyebrow">Build it with us</p>
                <h2>Help shape an economy worth measuring.</h2>
                <p className="ab-prose ab-prose--center">
                    If you’d rather your contributions be remembered for what they meant than counted for
                    what they scored, you belong here.
                </p>
                <div className="ab-join-actions">
                    <Link to="/register" className="btn btn-accent ab-btn-lg">Join LogoSphere</Link>
                    <Link to="/contribute" className="btn btn-ghost ab-btn-lg">Contribute</Link>
                </div>
            </section>
        </div>
    );
};

export default About;
