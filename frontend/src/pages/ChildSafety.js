// Child safety standards — LogoSphere's published standards against child sexual abuse and
// exploitation (CSAE), which Google Play asks of every app in its Social category. The app has
// the same words (android ui/info/InfoContent.kt).
import React from 'react';
import { Link } from 'react-router-dom';
import DocPage from '../components/DocPage';

export const CHILD_SAFETY_UPDATED = '26 November 2026';

const sections = [
    {
        id: 'zero-tolerance',
        title: 'Zero tolerance',
        body: (
            <>
                <p>
                    LogoSphere does not allow child sexual abuse and exploitation (CSAE) of any kind, anywhere in it: on
                    logosphere.earth and in the LogoSphere app, in openings, messages, pictures, receipts, groups, events and
                    everything else members share.
                </p>
                <p>
                    That includes child sexual abuse material (CSAM), whether photographed, drawn or made with AI; sexualising
                    a child in any way; grooming, or trying to meet a child for sexual purposes; sextortion; and trafficking.
                </p>
            </>
        ),
    },
    {
        id: 'who-its-for',
        title: 'Who LogoSphere is for',
        body: (
            <p>
                LogoSphere is meant for adults and for families who use it together; it isn&rsquo;t designed for children
                on their own. If we learn that a child is using an account on their own, we close it.
            </p>
        ),
    },
    {
        id: 'report',
        title: 'How to report',
        body: (
            <ul>
                <li>
                    <strong>In LogoSphere:</strong> press <em>Report</em> on the person, message, opening, event,
                    announcement or acknowledgement, or use the flag at the top of every screen. Reports go only to the
                    platform&rsquo;s administrators; the person reported isn&rsquo;t told.
                </li>
                <li><strong>By email:</strong> <a href="mailto:support@logosphere.earth">support@logosphere.earth</a>.</li>
                <li>
                    <strong>If a child is in danger now,</strong> call your local emergency number first: 000 in Australia,
                    911 in the United States, 112 in Europe.
                </li>
                <li>
                    You can also report child sexual abuse material directly to{' '}
                    <a href="https://report.cybertip.org/">NCMEC&rsquo;s CyberTipline</a> or, in Australia, to the{' '}
                    <a href="https://www.accce.gov.au/report">Australian Centre to Counter Child Exploitation</a>.
                </li>
            </ul>
        ),
    },
    {
        id: 'what-we-do',
        title: 'What we do',
        body: (
            <ul>
                <li>A report about a child&rsquo;s safety comes before anything else, as soon as we see it.</li>
                <li>We remove CSAE content as soon as we know of it, and close the accounts involved.</li>
                <li>
                    We report child sexual abuse material to NCMEC and to the Australian Centre to Counter Child
                    Exploitation, keep what the law asks us to keep for them, and work with law enforcement.
                </li>
                <li>
                    AI pictures in LogoSphere are made by OpenAI&rsquo;s image model, which refuses sexual content involving
                    children, and any AI result can be reported like everything else.
                </li>
            </ul>
        ),
    },
    {
        id: 'contact',
        title: 'Child safety contact',
        body: (
            <p>
                The people who run LogoSphere are its child safety contact, and can answer for these standards and how we
                keep them: <a href="mailto:support@logosphere.earth">support@logosphere.earth</a>.
            </p>
        ),
    },
];

export default function ChildSafety() {
    return (
        <DocPage
            eyebrow="Child safety"
            title="Child safety standards"
            lede="LogoSphere's standards against child sexual abuse and exploitation (CSAE), for logosphere.earth and the LogoSphere app."
            updated={CHILD_SAFETY_UPDATED}
            glance={[
                'No child sexual abuse or exploitation, of any kind, ever.',
                'Report it where you see it, or with the flag on every screen.',
                'We remove it, close the accounts, and report it to the authorities.',
                'Contact: support@logosphere.earth.',
            ]}
            sections={sections}
            actions={<Link to="/tos" className="btn btn-ghost">Read the terms</Link>}
        />
    );
}
