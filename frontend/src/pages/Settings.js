// Settings — your account: name, where you are, how the site looks, your password,
// your data and, at the end, deleting the account. Every section saves on its
// own; nothing here pretends to save what doesn't exist yet.
import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useLogin } from '../App';
import api from '../api';
import { THEME_CHOICES, useTheme } from '../utils/theme';
import { MODE_CHOICES } from '../utils/modes';
import { usePlace } from '../utils/usePlace';
import PlaceFields from '../components/PlaceFields';
import '../styles/Settings.css';

const MIN_PASSWORD = 8;

function Note({ note }) {
    if (!note) return null;
    return <p className={`settings-msg ${note.ok ? 'settings-msg--ok' : 'settings-msg--err'}`} role="status">{note.text}</p>;
}

const errorText = (e, fallback) => e?.response?.data?.message || fallback;

function AccountSection() {
    const { userId, setUserName } = useLogin();
    const [profile, setProfile] = useState(null);
    const [fields, setFields] = useState({ name: '', surname: '' });
    const [saving, setSaving] = useState(false);
    const [note, setNote] = useState(null);

    useEffect(() => {
        api.get('/api/user/profile').then((r) => {
            const u = r.data;
            setProfile(u);
            setFields({ name: u.name || '', surname: u.surname || '' });
        }).catch(() => {});
    }, [userId]);

    const set = (k) => (e) => setFields((f) => ({ ...f, [k]: e.target.value }));
    const save = async (e) => {
        e.preventDefault();
        setSaving(true);
        setNote(null);
        try {
            await api.post('/api/updateuser', fields);
            if (setUserName) setUserName([fields.name, fields.surname].filter(Boolean).join(' '));
            setNote({ ok: true, text: 'Saved.' });
        } catch (err) {
            setNote({ ok: false, text: errorText(err, 'Could not save.') });
        } finally {
            setSaving(false);
        }
    };

    return (
        <section id="account-settings" className="settings-card">
            <h3>Your name</h3>
            <form onSubmit={save}>
                <div className="form-group">
                    <label htmlFor="name">First name</label>
                    <input type="text" id="name" value={fields.name} onChange={set('name')} autoComplete="given-name" required />
                </div>
                <div className="form-group">
                    <label htmlFor="surname">Last name</label>
                    <input type="text" id="surname" value={fields.surname} onChange={set('surname')} autoComplete="family-name" />
                </div>
                <div className="form-group">
                    <label htmlFor="settings-email">Email</label>
                    <input type="email" id="settings-email" value={profile?.email || ''} disabled />
                    <small className="settings-hint">Your email can't be changed here.</small>
                </div>
                <Note note={note} />
                <div className="settings-actions">
                    <button type="submit" className="btn-orange" disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</button>
                </div>
            </form>
        </section>
    );
}

function PlaceSection() {
    const { userId } = useLogin();
    const { hash } = useLocation();
    const editor = usePlace('users', userId);
    const [saving, setSaving] = useState(false);
    const [note, setNote] = useState(null);

    useEffect(() => {
        if (hash === '#place' && editor.loaded) document.getElementById('place')?.scrollIntoView({ block: 'start' });
    }, [hash, editor.loaded]);

    const save = async (e) => {
        e.preventDefault();
        if (editor.problem) { setNote({ ok: false, text: editor.problem }); return; }
        setSaving(true);
        setNote(null);
        try {
            await editor.save();
            setNote({ ok: true, text: 'Saved.' });
        } catch (err) {
            setNote({ ok: false, text: errorText(err, 'Could not save where you are.') });
        } finally {
            setSaving(false);
        }
    };

    return (
        <section id="place" className="settings-card place-anchor">
            <h3>Where you are</h3>
            <p className="settings-sub">As exactly or as roughly as you like, or not at all. It shows you what&rsquo;s near you.</p>
            <form onSubmit={save}>
                <PlaceFields editor={editor} label="Your place" />
                <Note note={note} />
                {editor.loaded && (
                    <div className="settings-actions">
                        <button type="submit" className="btn-orange" disabled={saving}>{saving ? 'Saving…' : 'Save where you are'}</button>
                    </div>
                )}
            </form>
        </section>
    );
}

function ModeSection() {
    const { uiMode, changeUiMode } = useLogin();
    const [note, setNote] = useState(null);
    const choose = async (mode) => {
        setNote(null);
        if (!(await changeUiMode(mode))) setNote({ ok: false, text: "That didn't save. Please try again." });
    };
    return (
        <section id="simple-or-advanced" className="settings-card">
            <h3>Simple or Advanced</h3>
            <p className="settings-sub">
                This changes only how much you&rsquo;re shown, here and in the app. Nothing of yours is lost
                by switching, and you can switch back whenever you like.
            </p>
            <div className="settings-choices" role="radiogroup" aria-label="Simple or Advanced">
                {MODE_CHOICES.map(([value, label, about]) => (
                    <label key={value} className={`settings-choice settings-choice--mode ${uiMode === value ? 'is-on' : ''}`}>
                        <input type="radio" name="ui-mode" value={value} checked={uiMode === value} onChange={() => choose(value)} />
                        <span><strong>{label}</strong><small>{about}</small></span>
                    </label>
                ))}
            </div>
            <Note note={note} />
        </section>
    );
}

function AppearanceSection() {
    const { choice, setTheme } = useTheme();
    return (
        <section id="appearance" className="settings-card">
            <h3>Appearance</h3>
            <p className="settings-sub">Kept in this browser. The ☾ / ☀ button at the top switches too.</p>
            <div className="settings-choices" role="radiogroup" aria-label="Theme">
                {THEME_CHOICES.map(([value, label]) => (
                    <label key={value} className={`settings-choice ${choice === value ? 'is-on' : ''}`}>
                        <input type="radio" name="theme" value={value} checked={choice === value} onChange={() => setTheme(value)} />
                        <span className={`settings-swatch settings-swatch--${value}`} aria-hidden="true" />
                        {label}
                    </label>
                ))}
            </div>
        </section>
    );
}

function PasswordSection() {
    const [current, setCurrent] = useState('');
    const [next, setNext] = useState('');
    const [again, setAgain] = useState('');
    const [saving, setSaving] = useState(false);
    const [note, setNote] = useState(null);
    const tooShort = next.length > 0 && next.length < MIN_PASSWORD;
    const mismatch = again.length > 0 && again !== next;

    const save = async (e) => {
        e.preventDefault();
        setSaving(true);
        setNote(null);
        try {
            const r = await api.post('/api/account/password', { current_password: current, new_password: next });
            setNote({ ok: true, text: r.data.message || 'Password changed.' });
            setCurrent(''); setNext(''); setAgain('');
        } catch (err) {
            setNote({ ok: false, text: errorText(err, 'Could not change your password.') });
        } finally {
            setSaving(false);
        }
    };

    return (
        <section id="password" className="settings-card">
            <h3>Password</h3>
            <form onSubmit={save}>
                <div className="form-group">
                    <label htmlFor="pw-current">Current password</label>
                    <input type="password" id="pw-current" value={current} onChange={(e) => setCurrent(e.target.value)} autoComplete="current-password" required />
                </div>
                <div className="form-group">
                    <label htmlFor="pw-new">New password</label>
                    <input type="password" id="pw-new" value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password" required aria-invalid={tooShort} />
                    <small className="settings-hint">{tooShort ? `At least ${MIN_PASSWORD} characters.` : `${MIN_PASSWORD} characters or more.`}</small>
                </div>
                <div className="form-group">
                    <label htmlFor="pw-again">New password again</label>
                    <input type="password" id="pw-again" value={again} onChange={(e) => setAgain(e.target.value)} autoComplete="new-password" required aria-invalid={mismatch} />
                    {mismatch && <small className="settings-hint settings-hint--err">The two don't match.</small>}
                </div>
                <Note note={note} />
                <div className="settings-actions">
                    <button type="submit" className="btn-orange" disabled={saving || !current || next.length < MIN_PASSWORD || next !== again}>
                        {saving ? 'Changing…' : 'Change password'}
                    </button>
                    <small className="settings-hint">Your other browsers and phones are signed out; this one stays signed in.</small>
                </div>
            </form>
        </section>
    );
}

function DataSection() {
    const [busy, setBusy] = useState(false);
    const [note, setNote] = useState(null);
    const download = async () => {
        setBusy(true);
        setNote(null);
        try {
            const r = await api.get('/api/account/export', { responseType: 'blob' });
            const name = /filename="([^"]+)"/.exec(r.headers['content-disposition'] || '')?.[1] || 'logosphere-data.json';
            const url = URL.createObjectURL(r.data);
            const a = document.createElement('a');
            a.href = url;
            a.download = name;
            document.body.appendChild(a);
            a.click();
            a.remove();
            setTimeout(() => URL.revokeObjectURL(url), 1000);
            setNote({ ok: true, text: `Saved as ${name}.` });
        } catch (_) {
            setNote({ ok: false, text: 'Could not download your data. Please try again.' });
        } finally {
            setBusy(false);
        }
    };
    return (
        <section id="your-data" className="settings-card">
            <h3>Your data</h3>
            <p className="settings-sub">
                Everything LogoSphere holds about you — your profile, value cards, memberships, openings, exchanges,
                follows, votes and notifications — in one file you can keep. Your password isn't in it: it's only
                stored as a one-way hash.
            </p>
            <Note note={note} />
            <button type="button" className="btn btn-ghost" onClick={download} disabled={busy}>
                {busy ? 'Preparing…' : 'Download your data'}
            </button>
        </section>
    );
}

function DeleteSection() {
    const { setIsLoggedIn, setUserId, setUserName, setIsPlatformAdmin } = useLogin();
    const navigate = useNavigate();
    const [password, setPassword] = useState('');
    const [armed, setArmed] = useState(false);
    const [busy, setBusy] = useState(false);
    const [note, setNote] = useState(null);

    const remove = async (e) => {
        e.preventDefault();
        if (!armed) { setArmed(true); return; }
        setBusy(true);
        setNote(null);
        try {
            await api.post('/api/account/delete', { password });
            setIsLoggedIn(false);
            setUserId(null);
            if (setUserName) setUserName('');
            if (setIsPlatformAdmin) setIsPlatformAdmin(false);
            navigate('/', { replace: true });
        } catch (err) {
            setNote({ ok: false, text: errorText(err, 'Could not delete your account.') });
            setArmed(false);
        } finally {
            setBusy(false);
        }
    };

    return (
        <section id="delete-account" className="settings-card settings-card--danger">
            <h3>Delete your account</h3>
            <p className="settings-sub">
                Your profile, value cards, notifications, follows and memberships are removed, and your open openings
                are withdrawn. Exchanges you took part in stay as history for the other people in them, under your
                name. This can't be undone.
            </p>
            <form onSubmit={remove}>
                <div className="form-group">
                    <label htmlFor="delete-password">Your password, to confirm</label>
                    <input type="password" id="delete-password" value={password}
                           onChange={(e) => { setPassword(e.target.value); setArmed(false); }}
                           autoComplete="current-password" required />
                </div>
                <Note note={note} />
                <button type="submit" className="btn-danger" disabled={busy || !password}>
                    {busy ? 'Deleting…' : armed ? 'Really delete my account' : 'Delete my account'}
                </button>
                {armed && <small className="settings-hint settings-hint--err">Press again to delete it for good.</small>}
            </form>
        </section>
    );
}

const SettingsPage = () => (
    <div className="settings-page">
        <div className="settings-head">
            <p className="settings-eyebrow">Account</p>
            <h1>Settings</h1>
            <p className="settings-lede">Your name, how LogoSphere looks, your password and your data. What you care about lives on your Meaning Graph.</p>
            <nav className="settings-jump" aria-label="Sections">
                <a href="#account-settings">Name &amp; place</a>
                <a href="#simple-or-advanced">Simple or Advanced</a>
                <a href="#appearance">Appearance</a>
                <a href="#password">Password</a>
                <a href="#your-data">Your data</a>
                <a href="#delete-account">Delete account</a>
            </nav>
        </div>
        <AccountSection />
                <PlaceSection />
        <ModeSection />
        <AppearanceSection />
        <PasswordSection />
        <DataSection />
        <DeleteSection />
    </div>
);

export default SettingsPage;
