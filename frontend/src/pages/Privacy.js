// Privacy — what LogoSphere keeps about you, who sees it, who helps run it,
// and what you can do. Written to match what the platform actually does
// (backend/app, android/): keep it in step when that changes.
import React from 'react';
import { Link } from 'react-router-dom';
import DocPage from '../components/DocPage';

export const PRIVACY_UPDATED = '23 November 2026';

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
                        <dt>Places</dt>
                        <dd>
                            The words you use for a place and, if you put it on the map, a point no more exact than you chose:
                            a pin is rounded before it is saved. For yourself we also keep whether members nearby may find
                            you. That is off unless you switch it on.
                        </dd>
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
                        <dt>Your choices on the Meaning Graph and in Settings</dt>
                        <dd>
                            Which pairs of value cards you judged close or not (others see only totals, from two people up),
                            and whether you use Simple or Advanced.
                        </dd>
                    </div>
                    <div>
                        <dt>AI help</dt>
                        <dd>
                            That you used it, for two days, to keep to daily limits. Not what you typed. For each picture it
                            draws we keep a fingerprint and a tiny thumbnail, so AI pictures can be labelled.
                        </dd>
                    </div>
                    <div>
                        <dt>Email</dt>
                        <dd>
                            Whether you confirmed your address, and which notifications you chose to get by email. When
                            someone starts to join, their name and address for up to a day, until the emailed link is used.
                            To prevent misuse, we count emails and requests for up to a day, without storing the address or
                            the connection they count.
                        </dd>
                    </div>
                    <div>
                        <dt>Events, announcements and invitations</dt>
                        <dd>
                            Events you put on, with their pictures and places, and whether you said you would come to which
                            date. Announcements you write. For an invitation link, a one-way hash of it, who made it and who
                            joined with it, for two weeks. If someone signs up with one, that hash waits with their name
                            and address until they finish.
                        </dd>
                    </div>
                    <div>
                        <dt>Messages, blocks and reports</dt>
                        <dd>
                            Messages you send and get, whom you blocked, and the reports you make with a copy of what you
                            reported.
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
                    <li><strong>Members</strong> see your name, photo, the words you use for where you are, and your value cards.</li>
                    <li>
                        <strong>Your groups</strong> see what happens in them: a sphere's openings, exchanges, receipts and
                        people are for its members — unless its managers switch on <em>public activity</em>, which lets
                        anyone, even visitors without an account, see its projects, alliances and openings.
                    </li>
                    <li><strong>Your email address</strong> is never shown to other members.</li>
                    <li>
                        <strong>An event</strong>, with who is coming, is seen by the members of its sphere, or by every
                        signed-in member when it is for everyone.
                    </li>
                    <li>
                        <strong>An announcement</strong> is read by the group&rsquo;s members, and for an alliance or project
                        by the rest of its sphere. Its notification never has the words.
                    </li>
                    <li>
                        <strong>An invitation link</strong> shows your name, and the group&rsquo;s, to whoever holds it.
                        You&rsquo;re told who joined with it.
                    </li>
                    <li>
                        <strong>A message</strong> is for the two people in it. Writing to everyone who responded to an
                        opening sends each their own, so they don&rsquo;t learn who else responded. AI personas neither read
                        nor send messages, and none go to an AI provider.
                    </li>
                    <li><strong>Blocks and reports</strong> aren&rsquo;t told to the person they&rsquo;re about.</li>
                    <li>
                        <strong>Platform administrators</strong> — the few people who run LogoSphere — see email
                        addresses and what happens in every group, so they can keep the platform working and safe, and use
                        that access only for that. They don&rsquo;t see your point on the map, and of private messages they
                        see only what was reported. Like all that is stored, both can be reached by whoever runs the server:
                        messages aren&rsquo;t end-to-end encrypted.
                    </li>
                </ul>
                <p>Exchanges belong to both people in them, so an exchange stays in the other person's trail as well as yours.</p>
            </>
        ),
    },
    {
        id: 'places',
        title: 'Places and who is near',
        body: (
            <>
                <ul>
                    <li><strong>Your point</strong> is never shown to another member, however exact you made it.</li>
                    <li>
                        <strong>Distances</strong> are worked out between squares a kilometre across and told only in steps
                        (within 2 km, 5 km, 10 km and so on). Someone determined could work out your square from several of
                        them, and only if you chose to be findable. A rougher place blurs that further.
                    </li>
                    <li>
                        <strong>A group, opening or event</strong> shows its words and a rough distance. It shows the spot
                        itself only when whoever runs it chose &ldquo;the exact spot&rdquo;, and for a private sphere only to
                        those inside it. An event for everyone shows it to every signed-in member.
                    </li>
                    <li>
                        <strong>Your device&rsquo;s location</strong> is read once, when you press &ldquo;Use where I am
                        now&rdquo;, and is never followed.
                    </li>
                    <li>
                        <strong>Maps</strong> come from OpenStreetMap, only when you open one. It then learns your IP address,
                        that you came from LogoSphere, and the part of the world you&rsquo;re looking at.
                    </li>
                </ul>
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
        id: 'ai-help',
        title: 'AI help, when you ask for it',
        body: (
            <>
                <p>
                    AI can help you word a value card, or draw a picture for an offer, need, group or event. It does nothing
                    until you press its button, and it saves nothing by itself.
                </p>
                <ul>
                    <li><strong>Wording a card</strong> sends what you typed for that card to Anthropic&rsquo;s Claude.</li>
                    <li><strong>Drawing a picture</strong> sends the title, the description and your hint to OpenAI.</li>
                    <li>Neither gets your name, email address, location or anything else about you, unless you type it there yourself.</li>
                    <li>
                        <strong>AI pictures are labelled</strong>, and in real spheres they can&rsquo;t be receipt photos or
                        exchange pictures. We can&rsquo;t recognise every AI picture made elsewhere. In demo spheres,
                        evidence may be AI-made.
                    </li>
                </ul>
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
                    <div><dt>OpenStreetMap</dt><dd>Draws the map, when you open one (see Places above).</dd></div>
                    <div><dt>Google Fonts</dt><dd>Serves the website's two typefaces, so your browser contacts Google to load them.</dd></div>
                    <div><dt>Anthropic and OpenAI</dt><dd>Write the AI personas in the demo spheres, and give AI help when you ask for it (see above).</dd></div>
                    <div>
                        <dt>Mailgun</dt>
                        <dd>
                            Delivers email, once it&rsquo;s switched on: joining, password links, and the notifications you
                            chose. It gets your address and that email. We switch off its tracking of opens and clicks.
                        </dd>
                    </div>
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
                    part in stay, under your name, because they're part of the other person's record too. So do the messages
                    you sent, for the person who got them, without your name; and reports, as the safety record. A
                    group&rsquo;s events and announcements stay with it, without your name. Your events for everyone are
                    cancelled, keeping only their name and time; your replies to events and your invitation links go.
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
                    <li><strong>Choose</strong> which notifications are emailed (none unless you pick some), or stop them from any of those emails.</li>
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
                'Your spot on the map is never shown to other members.',
                'Notification emails are off until you switch them on.',
                'AI personas live only in the labelled demo spheres.',
                'AI help runs only when you press its button, and gets only what you typed there.',
                'Download everything we hold about you, or delete your account, yourself.',
            ]}
            sections={sections}
            actions={<Link to="/tos" className="btn btn-ghost">Read the terms</Link>}
        />
    );
}
