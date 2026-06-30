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
    <div className="container">
      <div className="settings-sidebar">
        <h2>Settings</h2>
      </div>
      <div className="settings-main">
        <div className="settings-list">
          <section id="account-settings">
            <h3>Account Settings</h3>
            <form onSubmit={handleSaveAccount}>
              <div className="form-group">
                <label htmlFor="name">First name</label>
                <input type="text" id="name" name="name" value={fields.name} onChange={handleChange} />
              </div>
              <div className="form-group">
                <label htmlFor="surname">Last name</label>
                <input type="text" id="surname" name="surname" value={fields.surname} onChange={handleChange} />
              </div>
              <div className="form-group">
                <label htmlFor="location">Location</label>
                <input type="text" id="location" name="location" value={fields.location} onChange={handleChange} placeholder="City, Country" />
              </div>
              <div className="form-group">
                <label>Email</label>
                <input type="email" value={profile?.email || ''} disabled style={{ opacity: 0.6 }} />
                <small style={{ color: 'var(--ink-faint)', fontSize: '0.75rem' }}>Email cannot be changed here.</small>
              </div>
              {saveMsg && <p style={{ color: saveMsg === 'Saved.' ? 'var(--leaf)' : 'var(--danger)', fontSize: '0.85rem' }}>{saveMsg}</p>}
              <button type="submit" className="btn-orange" disabled={saving}>{saving ? 'Saving…' : 'Save Changes'}</button>
            </form>
          </section>

          <section id="user-experience">
            <h3>User Experience</h3>
            <form onSubmit={(e) => e.preventDefault()}>
              <div className="form-group">
                <label htmlFor="theme">Theme</label>
                <select id="theme" name="theme" value={fields.theme} onChange={handleChange}>
                  <option value="light">Light</option>
                  <option value="dark">Dark (coming soon)</option>
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="language">Language</label>
                <select id="language" name="language" value={fields.language} onChange={handleChange}>
                  <option value="en">English</option>
                  <option value="es">Spanish</option>
                  <option value="fr">French</option>
                </select>
              </div>
              <button type="submit" className="btn-orange">Save Changes</button>
            </form>
          </section>

          <section id="notifications">
            <h3>Notifications</h3>
            <form onSubmit={(e) => e.preventDefault()}>
              <div className="form-group">
                <label htmlFor="emailNotifications">Email Notifications</label>
                <input type="checkbox" id="emailNotifications" name="emailNotifications" checked={fields.emailNotifications} onChange={handleChange} />
              </div>
              <div className="form-group">
                <label htmlFor="smsNotifications">SMS Notifications</label>
                <input type="checkbox" id="smsNotifications" name="smsNotifications" checked={fields.smsNotifications} onChange={handleChange} />
              </div>
              <button type="submit" className="btn-orange">Save Changes</button>
            </form>
          </section>

          <section id="privacy-security">
            <h3>Privacy &amp; Security</h3>
            <form onSubmit={(e) => e.preventDefault()}>
              <div className="form-group">
                <label htmlFor="twoFactorAuth">Two-Factor Authentication</label>
                <input type="checkbox" id="twoFactorAuth" name="twoFactorAuth" checked={fields.twoFactorAuth} onChange={handleChange} />
              </div>
              <div className="form-group">
                <label htmlFor="publicProfile">Public Profile</label>
                <input type="checkbox" id="publicProfile" name="publicProfile" checked={fields.publicProfile} onChange={handleChange} />
              </div>
              <button type="submit" className="btn-orange">Save Changes</button>
            </form>
          </section>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
