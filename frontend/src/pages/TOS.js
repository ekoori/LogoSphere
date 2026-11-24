// Terms — the agreement for using LogoSphere, in plain words: what it is, your
// account, what you post, how members treat each other, groups and their
// managers, the demo spheres, and the limits of what a small project promises.
import React from 'react';
import { Link } from 'react-router-dom';
import DocPage from '../components/DocPage';

export const TERMS_UPDATED = '23 November 2026';

const sections = [
    {
        id: 'what-it-is',
        title: 'What LogoSphere is',
        body: (
            <>
                <p>
                    LogoSphere is a place for groups — neighbourhoods, clubs, congregations, teams — to ask for help, offer
                    it, keep an honest record of what happened, and decide things together. It's a gift economy:
                    <strong> no money changes hands through LogoSphere</strong>, and nothing here is for sale.
                </p>
                <p>By creating an account or using LogoSphere, you agree to these terms. If you don't, please don't use it.</p>
            </>
        ),
    },
    {
        id: 'your-account',
        title: 'Your account',
        body: (
            <ul>
                <li>Use your own name and a real email address; one person per account.</li>
                <li>Keep your password to yourself. You're responsible for what's done with your account.</li>
                <li>
                    If you think someone else has used it, change your password in <Link to="/settings">Settings</Link> —
                    that signs out every other device — and tell us at <a href="mailto:support@logosphere.earth">support@logosphere.earth</a>.
                </li>
            </ul>
        ),
    },
    {
        id: 'what-you-post',
        title: 'What you post',
        body: (
            <>
                <p>
                    What you write and the photos you add stay <strong>yours</strong>. By posting them you let LogoSphere
                    store them and show them to the people who can see that place — your group's members, the spheres you share
                    an opening with, every member for what you post to everyone, or anyone if a group's managers have made
                    its activity public — and keep exchanges as shared history for both people in them.
                </p>
                <p>Only post what's yours to share: no one else's photos, words or private details without their agreement.</p>
            </>
        ),
    },
    {
        id: 'ai-and-evidence',
        title: 'AI, pictures and evidence',
        body: (
            <>
                <p>
                    AI can help you word a value card, or draw a picture for an offer, need, group or event. It can be wrong:
                    what you post with it is yours to check.
                </p>
                <p>
                    Receipts are evidence. <strong>Outside the demo spheres, don&rsquo;t use AI-made pictures as receipt photos
                    or exchange pictures.</strong> LogoSphere refuses those it recognises, and it can&rsquo;t recognise every
                    one. In demo spheres evidence may be AI-made.
                </p>
            </>
        ),
    },
    {
        id: 'how-we-treat-each-other',
        title: 'How we treat each other',
        body: (
            <>
                <ul>
                    <li><strong>Be honest.</strong> Offer what you can really give; ask for what you really need; write receipts that say what happened.</li>
                    <li><strong>Keep it a gift.</strong> No selling, bartering for money, advertising or fundraising through openings.</li>
                    <li><strong>Be kind.</strong> No harassment, threats, hate or discrimination — in posts, messages, receipts, acknowledgements or anywhere else.</li>
                    <li><strong>Don&rsquo;t spam.</strong> Messages, invitations, events and announcements are for people who&rsquo;d want them.</li>
                    <li><strong>Respect privacy.</strong> Don't share someone's personal details, or what they told you in confidence.</li>
                    <li><strong>Be yourself.</strong> Don't pretend to be someone else — another member, a famous person, or an AI persona.</li>
                    <li><strong>Keep it legal and safe.</strong> Nothing illegal, dangerous or exploitative.</li>
                </ul>
                <p>
                    You can block anyone, and report a person, message, opening, event, announcement or acknowledgement to
                    the platform&rsquo;s administrators. Nobody else is told.
                </p>
                <p className="dp-note">
                    LogoSphere doesn't check members, run members' events or guarantee that help will happen. When you meet people or go to their
                    homes, use the same care you would anywhere: meet somewhere you're comfortable, and trust your instincts.
                </p>
            </>
        ),
    },
    {
        id: 'groups',
        title: 'Groups and the people who run them',
        body: (
            <>
                <p>
                    Spheres, alliances and projects set their own rules — who may join, how decisions pass — and members can
                    change them by proposal and vote. A group's managers can approve and remove members and edit the group.
                </p>
                <p>
                    Platform administrators may remove content or close accounts that break these terms or put people at
                    risk. So they can keep it running, LogoSphere shows them what happens in every group, but not your
                    point on the map, and of private messages only what was reported. They act for the good of the
                    community, not to take sides in a group's own decisions.
                </p>
            </>
        ),
    },
    {
        id: 'demo-spheres',
        title: 'Demo spheres and AI personas',
        body: (
            <>
                <p>
                    The demo spheres are clearly labelled practice spaces. Most of their members are AI personas: characters
                    with famous names, playing everyday neighbours, written by AI. They are not the real people, nothing
                    they say is an endorsement, and nothing in a demo sphere is real — no help is actually promised there.
                    They answer messages too, and AI writes those answers.
                </p>
                <p>What you post in a demo sphere, and what you write to a persona, is processed by AI services to write the personas' replies — see the <Link to="/privacy">privacy policy</Link>.</p>
            </>
        ),
    },
    {
        id: 'leaving',
        title: 'Leaving',
        body: (
            <p>
                You can leave any group from its page, and delete your account yourself, any time. We may close
                an account that seriously or repeatedly breaks these terms; where we can, we'll tell you why first.
            </p>
        ),
    },
    {
        id: 'promises',
        title: 'What we can and can\'t promise',
        body: (
            <>
                <p>
                    LogoSphere is run by a small, volunteer-built project. We work to keep it running and your data safe, but we
                    provide it <strong>as it is</strong>, without guarantees that it will always be available, free of
                    mistakes, or suitable for any particular purpose.
                </p>
                <p>
                    As far as the law allows, we aren't responsible for indirect losses, or for what members do or agree
                    between themselves, on LogoSphere or off it. Nothing in these terms takes away rights that the law where
                    you live gives you and that can't be signed away.
                </p>
            </>
        ),
    },
    {
        id: 'changes',
        title: 'Changes to these terms',
        body: (
            <p>
                If we change these terms, we'll update this page and its date, and for changes that matter we'll tell members in
                LogoSphere before they take effect. Using LogoSphere after that means you accept the new terms.
            </p>
        ),
    },
    {
        id: 'contact',
        title: 'Questions',
        body: <p>Write to <a href="mailto:support@logosphere.earth">support@logosphere.earth</a>.</p>,
    },
];

export default function TOS() {
    return (
        <DocPage
            eyebrow="Terms of service"
            title="The terms, in plain words"
            lede="What you can expect from LogoSphere, and what LogoSphere and its members expect of you."
            updated={TERMS_UPDATED}
            glance={[
                'Help here is a gift: nothing is bought or sold.',
                'What you post stays yours; your group gets to see it.',
                'Be honest, be kind, respect privacy, be yourself.',
                'Outside the demo spheres, evidence mustn’t be AI-made.',
                'You can block and report.',
                'Demo spheres are practice: their AI personas are labelled, and not the real people.',
            ]}
            sections={sections}
            actions={<Link to="/privacy" className="btn btn-ghost">Read the privacy policy</Link>}
        />
    );
}
