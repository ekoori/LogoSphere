// A stored place being edited: loaded when there's an id, saved with the form
// it sits in (components/PlaceFields.js shows it). Without an id it's blank.
import { useCallback, useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import api from '../api';
import { hasPoint, placeProblem, samePlace, toPayload } from './places';

const BLANK = { loaded: false, failed: false, saved: null, place: null, findable: false, wasFindable: false };

const fromServer = (data) => ({
    loaded: true,
    failed: false,
    saved: data.place || null,
    place: data.place || null,
    findable: !!data.findable,
    wasFindable: !!data.findable,
});

export function usePlace(kind, id) {
    const client = useQueryClient();
    const [state, setState] = useState(BLANK);

    useEffect(() => {
        setState(BLANK);
        if (!id) return undefined;
        let current = true;
        api.get(`/api/places/${kind}/${id}`)
            .then((r) => { if (current) setState(fromServer(r.data)); })
            .catch(() => { if (current) setState({ ...BLANK, failed: true }); });
        return () => { current = false; };
    }, [kind, id]);

    const setPlace = useCallback((place) => setState((s) => ({ ...s, place })), []);
    const setFindable = useCallback((findable) => setState((s) => ({ ...s, findable })), []);

    const person = kind === 'users';
    // With no point there's nothing to be found by.
    const findable = state.findable && hasPoint(state.place);
    const placeChanged = state.loaded && !samePlace(state.saved, state.place);
    const changed = placeChanged || (state.loaded && person && findable !== state.wasFindable);
    const problem = placeChanged ? placeProblem(state.place) : null;

    /** Saves what changed: {id, place}, or null when nothing did. Throws as axios does. */
    const save = async (to = id) => {
        if (!changed) return null;
        const body = {};
        if (placeChanged) body.place = toPayload(state.place);
        if (person) body.findable = findable;
        const { data } = await api.post(`/api/places/${kind}/${to}`, body);
        setState(fromServer(data));
        client.invalidateQueries();     // distances everywhere follow from it
        return data;
    };

    return { person, loaded: state.loaded, failed: state.failed, place: state.place, setPlace, findable, setFindable, changed, problem, save };
}
