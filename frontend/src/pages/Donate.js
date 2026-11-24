// Donate — what keeping LogoSphere running costs, and how to help pay for it.
import React from 'react';
import { Link } from 'react-router-dom';
import DocPage from '../components/DocPage';

// Donations are paused (2026-11-24): the PayPal address here was at logosphere.net, a domain
// LogoSphere doesn't own. Put the PayPal account that should receive them (its email or
// merchant ID) in PAYPAL_BUSINESS to open them again; the header's Donate links follow.
const PAYPAL_BUSINESS = '';
export const DONATIONS_OPEN = PAYPAL_BUSINESS !== '';

const sections = [
    {
        id: 'what-it-costs',
        title: 'What it costs',
        body: (
            <>
                <p>LogoSphere has no ads and sells nothing — your data least of all. What it does cost:</p>
                <ul>
                    <li>A server, and storage for everyone's pictures.</li>
                    <li>The AI services that write the AI personas in the demo spheres, so anyone can try LogoSphere before bringing their group.</li>
                    <li>The address, certificates and upkeep that keep it all reachable and safe.</li>
                </ul>
                <p>Donations pay for these, so more groups can use LogoSphere freely.</p>
            </>
        ),
    },
    {
        id: 'how-to-give',
        title: 'How to give',
        body: DONATIONS_OPEN ? (
            <>
                <p>Donations go through PayPal: you can pay with a PayPal account or a card. PayPal handles the payment; we receive only what PayPal shares about it.</p>
                <form action="https://www.paypal.com/donate" method="post" target="_blank" className="dp-donate">
                    <input type="hidden" name="business" value={PAYPAL_BUSINESS} />
                    <input type="hidden" name="no_recurring" value="0" />
                    <input type="hidden" name="item_name" value="Support LogoSphere" />
                    <input type="hidden" name="currency_code" value="USD" />
                    <button type="submit" className="btn btn-accent">Donate with PayPal</button>
                </form>
            </>
        ) : (
            <p>Donations are paused for a little while, until the account that receives them is set up. You can still help in the other ways below.</p>
        ),
    },
    {
        id: 'other-ways',
        title: 'Other ways to help',
        body: (
            <ul>
                <li><strong>Bring your group</strong> — LogoSphere is worth the most when it's used.</li>
                <li><strong>Give your time</strong> — testing, writing, design or code: see <Link to="/contribute">Contribute</Link>.</li>
                <li><strong>Tell someone</strong> who runs a group that could use it.</li>
            </ul>
        ),
    },
    {
        id: 'thank-you',
        title: 'Thank you',
        body: <p>Every gift — money, time or a word to a friend — keeps a little more help from getting lost in a chat thread. We're grateful.</p>,
    },
];

export default function Donate() {
    return (
        <DocPage
            eyebrow="Donate"
            title="Keep LogoSphere running"
            lede="It runs on donations and volunteers' time, so it can stay free, ad-free and on the side of the groups that use it."
            sections={sections}
            contents={false}
            actions={<Link to="/contribute" className="btn btn-ghost">Or give your time</Link>}
        />
    );
}
