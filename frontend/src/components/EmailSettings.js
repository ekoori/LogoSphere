// Settings → Email: which notifications also come by email. All off until
// chosen, and only to a confirmed address. Each tick saves by itself.
import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import api from '../api';

const PERSONAS = 'personas';    // only widens the other topics

export default function EmailSettings() {
    const { hash } = useLocation();
    const [mail, setMail] = useState(null);
    const [failed, setFailed] = useState(false);
    const [saving, setSaving] = useState(false);
    const [note, setNote] = useState(null);

    useEffect(() => {
        api.get('/api/account/email').then((r) => setMail(r.data)).catch(() => setFailed(true));
    }, []);

    useEffect(() => {
        if (hash === '#email' && mail) document.getElementById('email')?.scrollIntoView({ block: 'start' });
    }, [hash, mail]);

    const toggle = async (key) => {
        const was = mail;
        const topics = was.topics.includes(key) ? was.topics.filter((k) => k !== key) : [...was.topics, key];
        setMail({ ...was, topics });
        setSaving(true);
        setNote(null);
        try {
            const { data } = await api.post('/api/account/email', { topics });
            setMail(data);
            setNote({ ok: true, text: data.confirmation_sent ? 'Saved. Now open the link we emailed you to confirm the address.' : 'Saved.' });
        } catch (err) {
            setMail(was);
            setNote({ ok: false, text: err.response?.data?.message || "That didn't save. Please try again." });
        } finally {
            setSaving(false);
        }
    };

    const sendLink = async () => {
        setSaving(true);
        try {
            setNote({ ok: true, text: (await api.post('/api/account/email/confirm')).data.message });
        } catch (err) {
            setNote({ ok: false, text: err.response?.data?.message || "That didn't send. Please try again." });
        } finally {
            setSaving(false);
        }
    };

    const usable = mail?.on && mail?.can_receive;
    const others = mail?.topics.some((key) => key !== PERSONAS);

    return (
        <section id="email" className="settings-card place-anchor">
            <h3>Email</h3>
            <p className="settings-sub">Your notifications can come by email too. Nothing does unless you tick it.</p>
            {failed && <p className="settings-msg settings-msg--err">Your email settings didn&rsquo;t load.</p>}
            {mail && !mail.on && <p className="settings-hint">LogoSphere can&rsquo;t send email yet.</p>}
            {mail?.on && !mail.can_receive && <p className="settings-hint">This account&rsquo;s address can&rsquo;t receive email.</p>}
            {usable && (
                <>
                    <p className="settings-sub settings-email-address">
                        To <strong>{mail.email}</strong>{mail.confirmed ? ' (confirmed)' : ' (not confirmed yet)'}
                    </p>
                    {!mail.confirmed && (
                        <p className="settings-sub">
                            Nothing is sent until you confirm it.{' '}
                            <button type="button" className="settings-linklike" onClick={sendLink} disabled={saving}>Email me the link</button>
                        </p>
                    )}
                    <div className="settings-choices">
                        {mail.choices.map(({ key, label, about }) => {
                            const on = mail.topics.includes(key);
                            return (
                                <label key={key} className={`settings-choice settings-choice--mode ${on ? 'is-on' : ''}`}>
                                    <input type="checkbox" checked={on} onChange={() => toggle(key)}
                                           disabled={saving || (key === PERSONAS && !others && !on)} />
                                    <span><strong>{label}</strong><small>{about}</small></span>
                                </label>
                            );
                        })}
                    </div>
                </>
            )}
            {note && <p className={`settings-msg settings-msg--${note.ok ? 'ok' : 'err'}`} role="status">{note.text}</p>}
        </section>
    );
}
