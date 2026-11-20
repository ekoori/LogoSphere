// Contribute — how to help build LogoSphere, with or without writing code.
import React from 'react';
import { Link } from 'react-router-dom';
import DocPage from '../components/DocPage';

const REPO = 'https://github.com/ekoori/LogoSphere';

const WAYS = [
    ['◍', 'Bring your group', 'Use it for real with the people you already help, and tell us what got in the way. That shapes LogoSphere more than anything else.'],
    ['✓', 'Test it', 'Try the website and the Android app. When something breaks or confuses you, open an issue with what you did and what you saw.'],
    ['✎', 'Words and design', 'Clearer wording, kinder empty states, better pages, more accessible screens — all welcome.'],
    ['{ }', 'Code', 'The backend, the website and the Android app all live in one repository, with tests for each.'],
];

const sections = [
    {
        id: 'ways-to-help',
        title: 'Ways to help',
        body: (
            <div className="dp-cards">
                {WAYS.map(([glyph, title, text]) => (
                    <article key={title} className="dp-card">
                        <span className="dp-card-glyph" aria-hidden="true">{glyph}</span>
                        <h3>{title}</h3>
                        <p>{text}</p>
                    </article>
                ))}
            </div>
        ),
    },
    {
        id: 'built-with',
        title: 'What it\'s built with',
        body: (
            <dl className="dp-defs">
                <div><dt>Server</dt><dd>Python and Flask, with Cassandra 5 for storage and pictures in object storage.</dd></div>
                <div><dt>Website</dt><dd>React, built with Vite; one design system, in light and dark.</dd></div>
                <div><dt>Android app</dt><dd>Kotlin and Jetpack Compose, talking to the same API as the website.</dd></div>
                <div><dt>The API</dt><dd>Described in <code>LogoSphereAPI.yaml</code> (OpenAPI); a test keeps it in step with the code.</dd></div>
                <div><dt>Demo spheres</dt><dd>AI personas written with Anthropic's Claude, their pictures drawn with an OpenAI image model.</dd></div>
            </dl>
        ),
    },
    {
        id: 'how-we-work',
        title: 'How we work',
        body: (
            <ul>
                <li>Small, careful changes, each with tests: pytest for the server, Vitest for the website, JUnit for the app.</li>
                <li>Words for people: messages say what happened and what to do next, in plain language.</li>
                <li>Private by default: no tracking, no ads, and only what a feature needs.</li>
                <li>Every screen in both light and dark, at phone width and with a screen reader.</li>
            </ul>
        ),
    },
    {
        id: 'get-started',
        title: 'Get started',
        body: (
            <>
                <p>
                    The code is on <a href={REPO} target="_blank" rel="noreferrer noopener">GitHub</a>. Its README explains how
                    to run everything on your own computer.
                </p>
                <p>
                    Not sure where to begin? Open an issue saying what you'd like to work on, or what you wish LogoSphere
                    did — we'll help you find a good first step.
                </p>
            </>
        ),
    },
];

export default function Contribute() {
    return (
        <DocPage
            eyebrow="Contribute"
            title="Help build LogoSphere"
            lede="LogoSphere is open source, built by volunteers and shaped by the groups that use it. There's a place for you whether or not you write code."
            sections={sections}
            contents={false}
            actions={(
                <>
                    <a href={REPO} target="_blank" rel="noreferrer noopener" className="btn btn-accent">Visit the repository</a>
                    <Link to="/how-it-works" className="btn btn-ghost">How LogoSphere works</Link>
                </>
            )}
        />
    );
}
