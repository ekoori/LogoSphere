// Putting on an event, or changing one.
import React, { useEffect, useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import api from '../api';
import { useLogin } from '../App';
import AiPictureMaker from '../components/AiPictureMaker';
import { Picture } from '../components/AiTag';
import PlaceFields from '../components/PlaceFields';
import PlacePicker from '../components/PlacePicker';
import { useEntity, useEntityList, ID_KEY } from '../utils/queries';
import { usePlace } from '../utils/usePlace';
import { placeProblem, toPayload } from '../utils/places';
import { forUpload } from '../utils/pictures';
import { REPEATS, deviceZone, lengthChoices, lengthText, repeatText, zoneChoices } from '../utils/events';
import '../styles/Events.css';

const EVERYONE = 'everyone';
const said = (err, fallback) => err.response?.data?.message || fallback;

/** The groups the viewer is in. */
function useMyGroups(enabled) {
    const { userId } = useLogin();
    const spheres = useEntityList('sphere', { enabled });
    const alliances = useEntityList('alliance', { enabled });
    const projects = useEntityList('project', { enabled });
    const groups = useMemo(() => [['sphere', spheres.data], ['alliance', alliances.data], ['project', projects.data]]
        .flatMap(([kind, rows]) => (rows || [])
            .filter((g) => !(kind === 'project' && g.phase === 'closed'))
            .filter((g) => (g.members || []).some((m) => String(m.id) === String(userId) && m.role !== 'pending'))
            .map((g) => ({ id: g[ID_KEY[kind]], name: g.name, kind }))),
    [userId, spheres.data, alliances.data, projects.data]);
    return { groups, loaded: !enabled || [spheres, alliances, projects].every((q) => q.isSuccess) };
}

function WhoFor({ value, onChange, groups }) {
    return (
        <label className="evt-field">
            Who is it for?
            <select value={value} onChange={(e) => onChange(e.target.value)} required>
                <option value="" disabled>Choose…</option>
                {groups.map((g) => <option key={g.id} value={g.id}>{g.name} ({g.kind})</option>)}
                <option value={EVERYONE}>Everyone on LogoSphere</option>
            </select>
        </label>
    );
}

WhoFor.propTypes = { value: PropTypes.string.isRequired, onChange: PropTypes.func.isRequired, groups: PropTypes.array.isRequired };

function EventForm({ event, group }) {
    const navigate = useNavigate();
    const client = useQueryClient();
    const editing = !!event;
    const { groups, loaded } = useMyGroups(!editing && !group);

    const [title, setTitle] = useState(event?.title || '');
    const [description, setDescription] = useState(event?.description || '');
    const [day, setDay] = useState(event?.starts.slice(0, 10) || '');
    const [clock, setClock] = useState(event?.starts.slice(11, 16) || '');
    const [length, setLength] = useState(event?.length_min || 120);
    const [repeats, setRepeats] = useState(event?.repeats || 'never');
    const [until, setUntil] = useState(event?.until || '');
    const [tz, setTz] = useState(event?.tz || deviceZone);
    const [zoneOpen, setZoneOpen] = useState(false);
    const [chosen, setChosen] = useState('');
    const [place, setPlace] = useState(null);           // a new one's; an existing one's has its editor
    const editor = usePlace('events', event?.id);
    const [picture, setPicture] = useState(null);       // {file, url, isAi}
    const [busy, setBusy] = useState(false);
    const [problem, setProblem] = useState('');

    useEffect(() => () => { if (picture) URL.revokeObjectURL(picture.url); }, [picture]);
    const choosePicture = (file, isAi) => setPicture(file ? { file, isAi, url: URL.createObjectURL(file) } : null);

    // With no groups there's only everyone; otherwise it's chosen, never assumed.
    const host = event?.host?.id || group?.id || chosen || (loaded && !groups.length ? EVERYONE : '');
    const everyone = editing ? !event.host : host === EVERYONE;
    const hostKind = event?.host?.kind || group?.kind || groups.find((g) => g.id === host)?.kind;

    const save = async (e) => {
        e.preventDefault();
        if (busy) return;
        const wrongPlace = editing ? editor.problem : placeProblem(place);
        if (wrongPlace) { setProblem(wrongPlace); return; }
        if (!editing && !host) { setProblem('Choose who it is for.'); return; }
        setBusy(true);
        setProblem('');
        const fields = {
            title: title.trim(),
            description: description.trim(),
            starts: `${day}T${clock}`,
            tz,
            length_min: Number(length),
            repeats,
            until: repeats === 'never' ? null : until || null,
        };
        let id = event?.id;
        try {
            if (editing) await api.patch(`/api/events/${id}`, fields);
            else id = (await api.post('/api/events', { ...fields, host_id: everyone ? undefined : host })).data.id;
        } catch (err) {
            setProblem(said(err, "That didn't save. Please try again."));
            setBusy(false);
            return;
        }
        // It's saved from here: what follows can fail without it being made twice.
        const lost = [];
        try {
            if (editing) await editor.save();
            else if (toPayload(place)) await api.post(`/api/places/events/${id}`, { place: toPayload(place) });
        } catch (_) {
            lost.push('where it is');
        }
        let pictureAt;
        if (picture) {
            try {
                const body = new FormData();
                body.append('image', await forUpload(picture.file));
                await api.post(`/api/events/${id}/image`, body);
                pictureAt = Date.now();
            } catch (_) {
                lost.push('the picture');
            }
        }
        client.removeQueries({ queryKey: ['event', id] });
        client.invalidateQueries({ queryKey: ['events'] });
        navigate(`/event?id=${id}`, {
            replace: true,
            state: { pictureAt, note: lost.length ? `Saved, but ${lost.join(' and ')} didn't. Press "Change it" to try again.` : '' },
        });
    };

    return (
        <form className="evt-form" onSubmit={save}>
            {!editing && !group && loaded && groups.length > 0 && <WhoFor value={host} onChange={setChosen} groups={groups} />}
            {!editing && !group && !loaded && <p className="evt-soft" role="status">Finding your groups…</p>}
            {(group || event?.host) && <p className="evt-for">For <strong>{(event?.host || group).name}</strong></p>}
            {(everyone || hostKind) && (
                <p className="evt-soft">
                    {everyone
                        ? 'Every signed-in member will see it, where it is and who is coming.'
                        : hostKind === 'sphere'
                            ? "The sphere's members will see it, and who is coming."
                            : `The members of the ${hostKind}'s sphere will see it, and who is coming.`}
                </p>
            )}

            <label className="evt-field">
                What is it?
                <input type="text" value={title} maxLength={120} required placeholder="e.g. Mending night"
                       onChange={(e) => setTitle(e.target.value)} />
            </label>
            <label className="evt-field">
                More about it (optional)
                <textarea rows={4} value={description} maxLength={4000} onChange={(e) => setDescription(e.target.value)}
                          placeholder="What to bring, who it suits, how to get in" />
            </label>

            <div className="evt-pair">
                <label className="evt-field">
                    Day
                    <input type="date" value={day} required onChange={(e) => setDay(e.target.value)} />
                </label>
                <label className="evt-field">
                    Starts at
                    <input type="time" value={clock} required onChange={(e) => setClock(e.target.value.slice(0, 5))} />
                </label>
                <label className="evt-field">
                    Lasts
                    <select value={length} onChange={(e) => setLength(Number(e.target.value))}>
                        {lengthChoices(length).map((n) => <option key={n} value={n}>{lengthText(n)}</option>)}
                    </select>
                </label>
            </div>
            <div className="evt-pair">
                <label className="evt-field">
                    Repeats
                    <select value={repeats} onChange={(e) => setRepeats(e.target.value)}>
                        {REPEATS.map((key) => <option key={key} value={key}>{repeatText(key, day)}</option>)}
                    </select>
                </label>
                {repeats !== 'never' && (
                    <label className="evt-field">
                        Until (optional)
                        <input type="date" value={until} min={day || undefined} onChange={(e) => setUntil(e.target.value)} />
                    </label>
                )}
            </div>
            {zoneOpen ? (
                <label className="evt-field">
                    Time zone
                    <select value={tz} onChange={(e) => setTz(e.target.value)}>
                        {zoneChoices(tz).map((name) => <option key={name} value={name}>{name.replace(/_/g, ' ')}</option>)}
                    </select>
                </label>
            ) : (
                <p className="evt-soft">
                    Times are {tz.replace(/_/g, ' ')} time.{' '}
                    <button type="button" className="evt-link" onClick={() => setZoneOpen(true)}>Change</button>
                </p>
            )}

            {editing
                ? <PlaceFields editor={editor} label="Where (optional)" />
                : <PlacePicker value={place} onChange={setPlace} label="Where (optional)" />}

            <div className="evt-picture">
                <label className="evt-field">
                    Picture (optional)
                    <input type="file" accept="image/*" onChange={(e) => choosePicture(e.target.files?.[0], false)} />
                </label>
                {(picture || event?.has_image) && (
                    <div className="evt-preview">
                        <Picture isAi={picture ? picture.isAi : event.image_is_ai} alt="The event's picture"
                                 src={picture ? picture.url : `/api/events/${event.id}/image?size=640`} />
                    </div>
                )}
                <AiPictureMaker purpose="event" title={title} description={description} onUse={async (file) => choosePicture(file, true)} />
            </div>

            {problem && <p className="evt-problem" role="alert">{problem}</p>}
            <div className="evt-foot">
                <button type="submit" className="evt-btn evt-btn--main" disabled={busy}>
                    {busy ? 'Saving…' : editing ? 'Save the changes' : 'Put it on'}
                </button>
                <button type="button" className="evt-btn" disabled={busy} onClick={() => navigate(-1)}>Back</button>
            </div>
        </form>
    );
}

EventForm.propTypes = { event: PropTypes.object, group: PropTypes.object };

export default function EventEditPage() {
    const [params] = useSearchParams();
    const id = params.get('id');
    const groupId = params.get('group');
    const kind = ['sphere', 'alliance', 'project'].includes(params.get('kind')) ? params.get('kind') : null;
    const found = useQuery({
        queryKey: ['event', id],
        queryFn: () => api.get(`/api/events/${id}`).then((r) => r.data),
        enabled: !!id,
        retry: false,
    });
    const forGroup = useEntity(kind, groupId, { enabled: !id });
    const naming = !id && groupId && kind;

    let body;
    if ((id && found.isError) || (naming && forGroup.isError)) {
        body = <p className="empty-state">That didn&rsquo;t load. <Link to="/events">See what&rsquo;s on</Link></p>;
    } else if ((id && !found.data) || (naming && !forGroup.data)) {
        body = <p className="evt-soft" role="status">Loading…</p>;
    } else if (id && (!found.data.can_manage || found.data.cancelled)) {
        body = (
            <p className="empty-state">
                {found.data.cancelled ? 'It was cancelled, so it can’t be changed. ' : 'Only whoever put it on, or the group’s managers, can change it. '}
                <Link to={`/event?id=${id}`}>Back to the event</Link>
            </p>
        );
    } else {
        const group = naming ? { id: groupId, kind, name: forGroup.data.name } : null;
        body = <EventForm key={id || groupId || 'new'} event={id ? found.data : null} group={group} />;
    }

    return (
        <div className="evt-page evt-page--form">
            <h1>{id ? 'Change the event' : 'Put on an event'}</h1>
            {body}
        </div>
    );
}
