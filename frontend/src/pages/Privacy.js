// Privacy — what LogoSphere keeps about you, who sees it, who helps run it,
// and what you can do. Written to match what the platform actually does
// (backend/app, android/): keep it in step when that changes.
import React from 'react';
import { Link } from 'react-router-dom';
import DocPage from '../components/DocPage';

export const PRIVACY_UPDATED = '21 November 2026';

const sections = [
    {
        id: 'what-we-keep',
        title: 'What we keep',
        body: (
            <>
                <dl className="dp-defs">
                    <div>
                        <dt>Your account</dt>
                        <dd>Your name and email address, and your password — stored only as a one-way hash, so nobody (us included) can read it.</dd>
                    </div>
                    <div>
                        <dt>Your profile</dt>
                        <dd>Whatever you add: a surname, where you are, a photo, and the value cards on your Meaning Graph.</dd>
                    </div>
                    <div>
                        <dt>What you do here</dt>
                        <dd>
                            The openings you post and accept; the exchanges you take part in, with their receipts, photos,
                            notes, follow-ups and acknowledgements; likes; who you follow; the groups you belong to; and
                            governance proposals, votes and the members you lend your vote to.
                        </dd>
                    </div>
                    <div>
                        <dt>Notifications</dt>
                        <dd>The messages LogoSphere writes for you when something happens that concerns you.</dd>
                    </div>
                    <div>
                        <dt>Keeping you signed in</dt>
                        <dd>
                            A random session identifier — in a cookie on the web, on your phone in the app — that lasts up to
                            30 days or until you sign out. If you allow notifications on Android, the app also registers your
                            phone's push address for as long as you're signed in on it.
                        </dd>
                    </div>
                    <div>
                        <dt>Server records</dt>
                        <dd>Like any website, the server notes requests (including your IP address) to keep it secure and fix problems. These records are kept for a short time.</dd>
                    </div>
                </dl>
                <p>We don't use analytics, advertising or tracking of any kind, and we never sell or rent anything about you.</p>
            </>
        ),
    },
    {
        id: 'who-sees-what',
        title: 'Who sees what',
        body: (
            <>
                <ul>
                    <li><strong>Members</strong> see your name, photo, location and value cards.</li>
                    <li>
                        <strong>Your groups</strong> see what happens in them: a sphere's openings, exchanges, receipts and
                        people are for its members — unless its managers switch on <em>public activity</em>, which lets
                        anyone, even visitors without an account, see its projects, alliances and openings.
                    </li>
                    <li><strong>Your email address</strong> is never shown to other members.</li>
                    <li>
                        <strong>Platform administrators</strong> — the few people who run LogoSphere — can see everything,
                        including email addresses, so they can keep the platform working and safe. They use that access only
                        for that.
                    </li>
                </ul>
                <p>Exchanges belong to both people in them, so an exchange stays in the other person's trail as well as yours.</p>
            </>
        ),
    },
    {
        id: 'demo-spheres',
        title: 'Demo spheres and AI personas',
        body: (
            <>
                <p>
                    The demo spheres are clearly labelled practice spaces. Most of their members are <strong>AI personas</strong>:
                    characters with famous names, playing everyday neighbours, whose posts and replies are written by AI
                    models — text by Anthropic's Claude, pictures by OpenAI. They are not the real people, and every one of
                    them is labelled.
                </p>
                <p className="dp-note">
                    To write the personas' replies, what happens in the demo spheres — including what you post there — is
                    sent to Anthropic and OpenAI. The personas act only in the demo spheres, and nothing from the real
                    spheres is sent to write them. If you'd rather not, simply don't join the demo spheres.
                </p>
            </>
        ),
    },
    {
        id: 'who-helps',
        title: 'Who helps us run it',
        body: (
            <>
                <p>A few services do part of the work. Each gets only what its job needs:</p>
                <dl className="dp-defs">
                    <div><dt>Linode (Akamai Cloud)</dt><dd>Runs the server and stores pictures, in a private storage bucket in London.</dd></div>
                    <div><dt>Google Fonts</dt><dd>Serves the website's two typefaces, so your browser contacts Google to load them.</dd></div>
                    <div><dt>Anthropic and OpenAI</dt><dd>Write the AI personas in the demo spheres (see above).</dd></div>
                    <div><dt>Google Firebase</dt><dd>Delivers push notifications to Android phones, once they're switched on, with only a notification's text and link.</dd></div>
                    <div><dt>PayPal</dt><dd>Handles donations, if you make one. We get only what PayPal shares about a payment.</dd></div>
                </dl>
            </>
        ),
    },
    {
        id: 'how-long',
        title: 'How long we keep it',
        body: (
            <>
                <p>
                    For as long as you have an account. When you delete it, we remove your profile, credentials, sessions,
                    value cards, notifications, follows and memberships, and withdraw your open openings. Exchanges you took
                    part in stay, under your name, because they're part of the other person's record too.
                </p>
                <p>Backup copies of the database may hold your data for a while longer before they're replaced.</p>
            </>
        ),
    },
    {
        id: 'your-choices',
        title: 'Your choices',
        body: (
            <>
                <ul>
                    <li><strong>Change</strong> your name, place and photo any time, in <Link to="/settings">Settings</Link> or on the Me tab in the app.</li>
                    <li><strong>Take a copy</strong> of everything we hold about you: Settings → Your data, or Me → Password, data &amp; account in the app.</li>
                    <li><strong>Leave</strong> any group from its page.</li>
                    <li><strong>Delete</strong> your account yourself, in Settings or the app.</li>
                    <li><strong>Ask</strong> us anything, or for anything those don't cover, at <a href="mailto:privacy@logosphere.net">privacy@logosphere.net</a>.</li>
                </ul>
                <p>
                    LogoSphere is meant for adults and for families who use it together; it isn't designed for children on
                    their own.
                </p>
            </>
        ),
    },
    {
        id: 'changes',
        title: 'Changes to this policy',
        body: (
            <p>
                When how we handle data changes, we'll update this page and its date. If a change matters to you — something
                new we'd keep, or someone new who'd see it — we'll say so in LogoSphere before it happens.
            </p>
        ),
    },
];

export default function Privacy() {
    return (
        <DocPage
            eyebrow="Privacy"
            title="What we keep, and why"
            lede="LogoSphere keeps what it needs to remember the help your group gives and receives — and nothing to sell, track or advertise with."
            updated={PRIVACY_UPDATED}
            glance={[
                'No ads, no analytics, no tracking — and we never sell your data.',
                'Your group sees what happens in your group; your email stays private.',
                'AI personas live only in the labelled demo spheres.',
                'Download everything we hold about you, or delete your account, yourself.',
            ]}
            sections={sections}
            actions={<Link to="/tos" className="btn btn-ghost">Read the terms</Link>}
        />
    );
}
