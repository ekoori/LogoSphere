// EntityForm — create a sphere, alliance or project. One form replaces the
// three New*Form components. Alliances and projects are anchored to a sphere
// the user belongs to; a project may optionally be run on behalf of an
// alliance the user manages within that sphere. The join policy is applied
// right after creation (the create endpoints take the core fields only).
import React, { useState } from 'react';
import PropTypes from 'prop-types';
import api from '../api';
import SphereBanner from './SphereBanner';
import { useLogin } from '../App';
import { useEntityList, useManagedEntities, useInvalidate, KIND_PATH } from '../utils/queries';
import '../styles/EntityCard.css';

const NOUN = { sphere: 'Sphere', alliance: 'Alliance', project: 'Project' };
const MANAGER_WORD = { sphere: 'an admin', alliance: 'a Lead or Board member', project: 'a manager' };

export default function EntityForm({ kind, isVisible, onCreated, onCancel }) {
    const { userId, isPlatformAdmin } = useLogin();
    const invalidate = useInvalidate();
    const spheres = useEntityList('sphere', { enabled: isVisible && kind !== 'sphere' });
    const managed = useManagedEntities(userId, isPlatformAdmin);

    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [location, setLocation] = useState('');
    const [sphereId, setSphereId] = useState('');
    const [ownerAllianceId, setOwnerAllianceId] = useState('');
    const [joinPolicy, setJoinPolicy] = useState('open');
    const [image, setImage] = useState(null);
    const [previewUrl, setPreviewUrl] = useState('');
    const [error, setError] = useState('');
    const [submitting, setSubmitting] = useState(false);

    if (!isVisible) return null;

    // Spheres the user belongs to — an alliance/project must live in one.
    const mySpheres = (spheres.data || []).filter((s) =>
        isPlatformAdmin || (s.members || []).some((m) => String(m.id) === String(userId)));
    // Alliances the user manages within the chosen sphere (projects only).
    const allianceOptions = managed.filter(
        (m) => m.kind === 'alliance' && (!sphereId || String(m.sphere_id) === String(sphereId)));

    const handleImageChange = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onloadend = () => setPreviewUrl(reader.result);
        reader.readAsDataURL(file);
        setImage(file);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (kind !== 'sphere' && !sphereId) { setError(`Please choose the sphere this ${kind} belongs to.`); return; }
        setError('');
        setSubmitting(true);
        try {
            const fd = new FormData();
            fd.append('name', name.trim());
            fd.append('description', description.trim());
            fd.append('location', location.trim());
            if (kind !== 'sphere') {
                const sphere = mySpheres.find((s) => s.sphere_id === sphereId);
                fd.append('sphere_id', sphereId);
                fd.append('sphere_name', sphere ? sphere.name : '');
            }
            if (kind === 'project') {
                const alliance = allianceOptions.find((a) => a.id === ownerAllianceId);
                if (alliance) fd.append('owner_alliance_id', alliance.id);
            }
            if (image) fd.append('image', image);
            const res = await api.post(`/api/${KIND_PATH[kind]}`, fd);
            const created = res.data || {};
            const newId = created[`${kind}_id`] || created.id;
            if (newId && joinPolicy !== 'open') {
                await api.patch(`/api/${KIND_PATH[kind]}/${newId}`, { join_policy: joinPolicy });
            }
            await invalidate.entity(kind, newId);
            setName(''); setDescription(''); setLocation(''); setSphereId(''); setOwnerAllianceId('');
            setJoinPolicy('open'); setImage(null); setPreviewUrl('');
            if (onCreated) onCreated(created);
        } catch (err) {
            setError(err.response?.data?.message || `Failed to create ${kind}.`);
        } finally {
            setSubmitting(false);
        }
    };

    const needsSphere = kind !== 'sphere';
    const noSphere = needsSphere && !spheres.isLoading && mySpheres.length === 0;

    return (
        <div id="entity-form" className="exchange">
            <h3>Create a New {NOUN[kind]}</h3>
            {error && <p className="form-error">{error}</p>}
            <form onSubmit={handleSubmit}>
                <SphereBanner previewUrl={previewUrl} onImageChange={handleImageChange} />

                <label htmlFor="entity-name">{NOUN[kind]} name</label>
                <input type="text" id="entity-name" value={name} onChange={(e) => setName(e.target.value)} required />

                <label htmlFor="entity-description">Description</label>
                <textarea id="entity-description" value={description} onChange={(e) => setDescription(e.target.value)} required />

                {needsSphere && (
                    <>
                        <label htmlFor="entity-sphere">{kind === 'alliance' ? 'Operating sphere' : 'Sphere'}</label>
                        {noSphere ? (
                            <p className="form-hint">You need to join a sphere before you can start {kind === 'alliance' ? 'an alliance' : 'a project'} in it.</p>
                        ) : (
                            <select id="entity-sphere" value={sphereId} onChange={(e) => setSphereId(e.target.value)} required>
                                <option value="">— choose a sphere —</option>
                                {mySpheres.map((s) => <option key={s.sphere_id} value={s.sphere_id}>{s.name}</option>)}
                            </select>
                        )}
                    </>
                )}

                {kind === 'project' && allianceOptions.length > 0 && (
                    <>
                        <label htmlFor="entity-alliance">On behalf of an alliance (optional)</label>
                        <select id="entity-alliance" value={ownerAllianceId} onChange={(e) => setOwnerAllianceId(e.target.value)}>
                            <option value="">— just me —</option>
                            {allianceOptions.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
                        </select>
                    </>
                )}

                <label htmlFor="entity-join-policy">Membership join policy</label>
                <select id="entity-join-policy" value={joinPolicy} onChange={(e) => setJoinPolicy(e.target.value)}>
                    <option value="open">Open — anyone can join directly</option>
                    <option value="approval">Approval required — {MANAGER_WORD[kind]} must approve</option>
                </select>

                <label htmlFor="entity-location">Geographical location</label>
                <input type="text" id="entity-location" value={location} onChange={(e) => setLocation(e.target.value)} />

                <div className="form-buttons">
                    <button type="submit" className="btn-orange" disabled={submitting || noSphere}>
                        {submitting ? 'Creating…' : `Create ${NOUN[kind]}`}
                    </button>
                    <button type="button" className="btn-blue" onClick={onCancel}>Cancel</button>
                </div>
            </form>
        </div>
    );
}

EntityForm.propTypes = {
    kind: PropTypes.oneOf(['sphere', 'alliance', 'project']).isRequired,
    isVisible: PropTypes.bool,
    onCreated: PropTypes.func,
    onCancel: PropTypes.func,
};
