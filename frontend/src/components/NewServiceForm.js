import React, { useState, useEffect } from 'react';
import '../styles/App.css';
import api from '../api';
import { useSimple } from '../utils/useSimple';
import { useLogin } from '../App';
import { forUpload } from '../utils/pictures';
import AiPictureMaker from './AiPictureMaker';
import { Picture } from './AiTag';
import PlacePicker from './PlacePicker';
import { placeProblem, toPayload } from '../utils/places';
import { SharePicker } from './Sharing';
import { loanQuestion, shareChoices } from '../utils/sharing';
import '../styles/Sharing.css';

// `actingAs` (optional): { id, name, sphereId, sphereName, projectName } — when
// set, the opening is posted on behalf of that sphere/alliance/project instead
// of the logged-in human, and its own sphere/project context is preset & locked.
function NewServiceForm({ isVisible, onSuccess, actingAs = null }) {
    const simple = useSimple();
    const [formData, setFormData] = useState({
        type: 'offer',
        title: '',
        description: '',
        sphere_id: actingAs?.sphereId || '',
        sphere_name: actingAs?.sphereName || '',
        project_name: actingAs?.projectName || '',
        cadence: 'single',
    });
    const { userId, isPlatformAdmin } = useLogin();
    const [spheres, setSpheres] = useState([]);
    const [projects, setProjects] = useState([]);
    const [submitting, setSubmitting] = useState(false);
    const [picture, setPicture] = useState(null);       // {file, url, isAi}
    useEffect(() => () => { if (picture) URL.revokeObjectURL(picture.url); }, [picture]);
    const choosePicture = (file, isAi = false) => setPicture(file ? { file, isAi, url: URL.createObjectURL(file) } : null);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);
    const [place, setPlace] = useState(null);
    const [posted, setPosted] = useState(0);            // a fresh picker for each opening
    const [borrow, setBorrow] = useState(false);
    const [alsoIn, setAlsoIn] = useState([]);

    useEffect(() => {
        if (!isVisible) return;
        api.get('/api/spheres').then((r) => setSpheres(r.data || [])).catch(() => {});
        // Closed (archived) projects take no new openings.
        api.get('/api/projects').then((r) => setProjects((r.data || []).filter((p) => p.phase !== 'closed'))).catch(() => {});
    }, [isVisible]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData((prev) => ({ ...prev, [name]: value }));
    };

    const handleSphereChange = (e) => {
        const selected = spheres.find((s) => s.sphere_id === e.target.value);
        setAlsoIn([]);      // what it could be shared with follows from its own sphere
        setFormData((prev) => ({
            ...prev,
            sphere_id: selected ? selected.sphere_id : '',
            sphere_name: selected ? selected.name : '',
        }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!formData.title.trim()) { setError('Title is required.'); return; }
        const wrongPlace = placeProblem(place);
        if (wrongPlace) { setError(wrongPlace); return; }
        setSubmitting(true);
        setError('');
        try {
            const created = await api.post('/api/openings', {
                type: formData.type,
                title: formData.title.trim(),
                description: formData.description.trim(),
                sphere_id: formData.sphere_id || null,
                sphere_name: formData.sphere_name || null,
                project_name: formData.project_name || null,
                cadence: formData.cadence,
                borrow,
                also_sphere_ids: !simple && formData.sphere_id && alsoIn.length ? alsoIn : undefined,
                status: 'Posted',
                acting_as_id: actingAs?.id || undefined,
            });
            const lost = [];
            const where = toPayload(place);
            if (where) {
                try {
                    await api.post(`/api/places/openings/${created.data.service_id}`, { place: where });
                } catch (err) {
                    lost.push('where it is');
                }
            }
            if (picture) {
                try {
                    const fd = new FormData();
                    fd.append('image', await forUpload(picture.file));
                    await api.post(`/api/openings/${created.data.service_id}/image`, fd);
                } catch (err) {
                    lost.push('the picture');
                }
                setPicture(null);
            }
            if (lost.length) setError(`Posted, but ${lost.join(' and ')} didn't save. You can add that from its page.`);
            setPlace(null);
            setBorrow(false);
            setAlsoIn([]);
            setPosted((n) => n + 1);
            setSuccess(true);
            setFormData({
                type: 'offer', title: '', description: '', cadence: 'single',
                sphere_id: actingAs?.sphereId || '', sphere_name: actingAs?.sphereName || '',
                project_name: actingAs?.projectName || '',
            });
            setTimeout(() => { setSuccess(false); if (onSuccess) onSuccess(); }, 1200);
        } catch (err) {
            setError(err.response?.data?.message || 'Failed to submit. Are you logged in?');
        } finally {
            setSubmitting(false);
        }
    };

    if (!isVisible) return null;
    // Only where it can be posted: the server refuses a sphere you aren't in.
    const postable = spheres.filter((s) => isPlatformAdmin || s.sphere_id === actingAs?.sphereId
        || (s.members || []).some((m) => String(m.id) === String(userId)));
    const home = spheres.find((s) => s.sphere_id === formData.sphere_id);
    const shareable = !simple && home ? shareChoices(spheres, { homeId: home.sphere_id, userId, isDemo: home.is_demo }) : [];

    return (
        <div className="card" style={{ padding: '1.2em 1.4em', marginBottom: '1.2em' }}>
            <h3 style={{ marginBottom: '0.9em' }}>
                {actingAs ? `New Opening — posting as ${actingAs.name}` : 'New Opening'}
            </h3>
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

                <div style={{ display: 'flex', gap: '0.5em' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.4em', cursor: 'pointer' }}>
                        <input type="radio" name="cadence" value="single" checked={formData.cadence === 'single'} onChange={handleChange} />
                        One-time
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.4em', cursor: 'pointer' }}>
                        <input type="radio" name="cadence" value="perpetual" checked={formData.cadence === 'perpetual'} onChange={handleChange} />
                        {simple ? 'Again and again (like weekly lessons)' : 'Ongoing (e.g. lessons — stays open, can be accepted repeatedly)'}
                    </label>
                </div>

                <label className="loan-check">
                    <input type="checkbox" checked={borrow} onChange={(e) => setBorrow(e.target.checked)} />
                    {loanQuestion(formData.type)}
                </label>

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
                    <select id="nsf-sphere" value={formData.sphere_id} onChange={handleSphereChange} disabled={!!actingAs?.sphereId}>
                        <option value="">Everyone on LogoSphere</option>
                        {postable.map((s) => (
                            <option key={s.sphere_id} value={s.sphere_id}>{s.name}</option>
                        ))}
                    </select>
                </div>

                {shareable.length > 0 && <SharePicker choices={shareable} value={alsoIn} onChange={setAlsoIn} />}

                <div>
                    <PlacePicker key={posted} value={place} onChange={setPlace} label="Where (optional)" />
                </div>

                {!simple && <div>
                    <label htmlFor="nsf-project">Project (optional)</label>
                    <select id="nsf-project" name="project_name" value={formData.project_name} onChange={handleChange} disabled={!!actingAs?.projectName}>
                        <option value="">— none —</option>
                        {projects.map((p) => (
                            <option key={p.project_id || p.name} value={p.name}>{p.name}</option>
                        ))}
                    </select>
                </div>}

                <div>
                    <span className="picture-label">Picture (optional)</span>
                    <div className="picture-field">
                        {picture && <Picture isAi={picture.isAi} src={picture.url} alt="Your opening's picture" />}
                        <label className="ai-open">
                            {picture ? 'Choose another' : 'Choose a picture'}
                            <input type="file" accept="image/*" hidden
                                   onChange={(e) => { choosePicture(e.target.files?.[0]); e.target.value = ''; }} />
                        </label>
                        {picture && <button type="button" className="ai-open" onClick={() => choosePicture(null)}>Remove</button>}
                        <AiPictureMaker purpose="opening" title={formData.title} description={formData.description}
                                        onUse={(file) => choosePicture(file, true)} />
                    </div>
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
