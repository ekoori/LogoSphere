import React, { useState, useEffect } from 'react';
import { useLogin } from '../App';
import api from '../api';
import '../styles/Settings.css';

const SettingsPage = () => {
  const { userId } = useLogin();
  const [profile, setProfile] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');
  const [fields, setFields] = useState({
    name: '', surname: '', location: '',
    theme: 'light', language: 'en',
    emailNotifications: true, smsNotifications: false,
    twoFactorAuth: false, publicProfile: true,
  });

  useEffect(() => {
    api.get('/api/user/profile').then((r) => {
      const u = r.data;
      setProfile(u);
      setFields((f) => ({
        ...f,
        name: u.name || '',
        surname: u.surname || '',
        location: u.location || '',
      }));
    }).catch(() => {});
  }, [userId]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFields((f) => ({ ...f, [name]: type === 'checkbox' ? checked : value }));
  };

  const handleSaveAccount = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSaveMsg('');
    try {
      await api.post('/api/updateuser', {
        name: fields.name,
        surname: fields.surname,
        location: fields.location,
      });
      setSaveMsg('Saved.');
    } catch {
      setSaveMsg('Failed to save.');
    } finally {
      setSaving(false);
      setTimeout(() => setSaveMsg(''), 3000);
    }
  };

  return (
    <div className="settings-page">
      <div className="settings-head">
        <p className="settings-eyebrow">Account</p>
        <h1>Settings</h1>
        <p className="settings-lede">Your name and where you are. Everything else about your profile lives on your Meaning Graph.</p>
      </div>

      <section id="account-settings" className="settings-card">
        <h3>Account Settings</h3>
        <form onSubmit={handleSaveAccount}>
          <div className="form-group">
            <label htmlFor="name">First name</label>
            <input type="text" id="name" name="name" value={fields.name} onChange={handleChange} autoComplete="given-name" />
          </div>
          <div className="form-group">
            <label htmlFor="surname">Last name</label>
            <input type="text" id="surname" name="surname" value={fields.surname} onChange={handleChange} autoComplete="family-name" />
          </div>
          <div className="form-group">
            <label htmlFor="location">Location</label>
            <input type="text" id="location" name="location" value={fields.location} onChange={handleChange} placeholder="City, Country" />
          </div>
          <div className="form-group">
            <label htmlFor="settings-email">Email</label>
            <input type="email" id="settings-email" value={profile?.email || ''} disabled />
            <small className="settings-hint">Email cannot be changed here.</small>
          </div>
          {saveMsg && <p className={`settings-msg ${saveMsg === 'Saved.' ? 'settings-msg--ok' : 'settings-msg--err'}`} role="status">{saveMsg}</p>}
          <div className="settings-actions">
            <button type="submit" className="btn-orange" disabled={saving}>{saving ? 'Saving…' : 'Save Changes'}</button>
          </div>
        </form>
      </section>

      <section id="coming-soon" className="settings-card settings-coming-soon">
        <h3>Preferences &amp; Notifications</h3>
        <p>
          Theme, language, notification and privacy preferences aren't configurable yet. They'll
          appear here once they actually do something; nothing set here would be saved today.
        </p>
      </section>
    </div>
  );
};

export default SettingsPage;
