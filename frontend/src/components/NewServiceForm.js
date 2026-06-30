import React, { useState, useEffect } from 'react';
import '../styles/App.css';
import api from '../api';

function NewServiceForm({ isVisible, onSuccess }) {
    const [formData, setFormData] = useState({
        type: 'offer',
        title: '',
        description: '',
        sphere_id: '',
        sphere_name: '',
        project_name: '',
    });
    const [spheres, setSpheres] = useState([]);
    const [projects, setProjects] = useState([]);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);

    useEffect(() => {
        if (!isVisible) return;
        api.get('/api/spheres').then((r) => setSpheres(r.data || [])).catch(() => {});
        api.get('/api/projects').then((r) => setProjects(r.data || [])).catch(() => {});
    }, [isVisible]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData((prev) => ({ ...prev, [name]: value }));
    };

    const handleSphereChange = (e) => {
        const selected = spheres.find((s) => s.sphere_id === e.target.value);
        setFormData((prev) => ({
            ...prev,
            sphere_id: selected ? selected.sphere_id : '',
            sphere_name: selected ? selected.name : '',
        }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!formData.title.trim()) { setError('Title is required.'); return; }
        setSubmitting(true);
        setError('');
        try {
            await api.post('/api/openings', {
                type: formData.type,
                title: formData.title.trim(),
                description: formData.description.trim(),
                sphere_id: formData.sphere_id || null,
                sphere_name: formData.sphere_name || null,
                project_name: formData.project_name || null,
                status: 'Posted',
            });
            setSuccess(true);
            setFormData({ type: 'offer', title: '', description: '', sphere_id: '', sphere_name: '', project_name: '' });
            setTimeout(() => { setSuccess(false); if (onSuccess) onSuccess(); }, 1200);
        } catch (err) {
            setError(err.response?.data?.message || 'Failed to submit. Are you logged in?');
        } finally {
            setSubmitting(false);
        }
    };

    if (!isVisible) return null;

    return (
        <div className="card" style={{ padding: '1.2em 1.4em', marginBottom: '1.2em' }}>
            <h3 style={{ marginBottom: '0.9em' }}>New Service</h3>
            {success && <p style={{ color: 'var(--success)', fontWeight: 600, marginBottom: '0.5em' }}>✓ Posted!</p>}
            {error && <p style={{ color: 'var(--danger)', fontSize: '0.85rem', marginBottom: '0.5em' }}>{error}</p>}
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '0.75em' }}>
                <div style={{ display: 'flex', gap: '0.5em' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.4em', cursor: 'pointer' }}>
                        <input type="radio" name="type" value="offer" checked={formData.type === 'offer'} onChange={handleChange} />
                        Offer
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.4em', cursor: 'pointer' }}>
                        <input type="radio" name="type" value="need" checked={formData.type === 'need'} onChange={handleChange} />
                        Need
                    </label>
                </div>

                <div>
                    <label htmlFor="nsf-title">Title *</label>
                    <input
                        id="nsf-title" name="title" type="text"
                        value={formData.title} onChange={handleChange}
                        placeholder="What are you offering or asking for?"
                        required
                    />
                </div>

                <div>
                    <label htmlFor="nsf-desc">Description</label>
                    <textarea
                        id="nsf-desc" name="description"
                        value={formData.description} onChange={handleChange}
                        placeholder="More details…" rows={3}
                        style={{ width: '100%', resize: 'vertical' }}
                    />
                </div>

                <div>
                    <label htmlFor="nsf-sphere">Sphere</label>
                    <select id="nsf-sphere" value={formData.sphere_id} onChange={handleSphereChange}>
                        <option value="">— none —</option>
                        {spheres.map((s) => (
                            <option key={s.sphere_id} value={s.sphere_id}>{s.name}</option>
                        ))}
                    </select>
                </div>

                <div>
                    <label htmlFor="nsf-project">Project (optional)</label>
                    <select id="nsf-project" name="project_name" value={formData.project_name} onChange={handleChange}>
                        <option value="">— none —</option>
                        {projects.map((p) => (
                            <option key={p.project_id || p.name} value={p.name}>{p.name}</option>
                        ))}
                    </select>
                </div>

                <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={submitting}
                    style={{ alignSelf: 'flex-start' }}
                >
                    {submitting ? 'Posting…' : 'Post to Openings'}
                </button>
            </form>
        </div>
    );
}

export default NewServiceForm;
