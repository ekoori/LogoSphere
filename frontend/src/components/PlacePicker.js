// Where something is, linked to the real world as exactly as someone wants:
// a name from the offline search, the device's location, or a pin on a map.
// It only holds the choice; whoever uses it saves it (POST /api/places/…).
import React, { useEffect, useId, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import api from '../api';
import { zoomFor } from '../utils/mercator';
import { PIN_PRECISIONS, coarsened, hasPoint, isFiner, isPin, linkedTo, squareKm, withWords } from '../utils/places';
import SlippyMap from './SlippyMap';
import '../styles/Places.css';

const WORLD = { lat: 10, lon: 20, z: 2 };
const SEARCH_AFTER_MS = 300;

const howFarOff = (metres) => (metres >= 1000 ? `${Math.ceil(metres / 1000)} km` : `${Math.ceil(metres)} m`);

export default function PlacePicker({ value, onChange, person = false, label = 'Where' }) {
    const inputId = useId();
    const [found, setFound] = useState([]);
    const [credit, setCredit] = useState(null);
    const [typed, setTyped] = useState(null);
    const [map, setMap] = useState(null);
    const [precision, setPrecision] = useState(isPin(value) ? value.precision : '1km');
    const [moveIt, setMoveIt] = useState(false);
    const [locating, setLocating] = useState(false);
    const [problem, setProblem] = useState('');
    // The device and the name lookup answer later: they go by what's true then.
    const latest = useRef({});
    latest.current = { value, onChange, precision };
    const words = value?.label || '';

    useEffect(() => {
        if (isPin(value)) setPrecision(value.precision);
    }, [value]);

    useEffect(() => {
        if (typed === null || typed.trim().length < 2) {
            setFound([]);
            return undefined;
        }
        let wanted = true;
        const timer = setTimeout(() => {
            api.post('/api/places/search', { q: typed })
                .then((r) => {
                    if (!wanted) return;
                    setFound(r.data.results || []);
                    setCredit(r.data.attribution || null);
                })
                .catch(() => { if (wanted) setFound([]); });
        }, SEARCH_AFTER_MS);
        return () => {
            wanted = false;
            clearTimeout(timer);
        };
    }, [typed]);

    const write = (text) => {
        onChange(withWords(value, text));
        // Words for a pin are just its name; anything else may be a place to look up.
        setTyped(isPin(value) ? null : text);
    };

    const choose = (place) => {
        onChange({ id: place.id, label: place.label, lat: place.lat, lon: place.lon, precision: place.precision });
        setTyped(null);
        setMap(null);
        setMoveIt(false);
        setProblem('');
    };

    const putPin = async (lat, lon) => {
        const { value: was, precision: as, onChange: change } = latest.current;
        // `fresh`: the point is as true as the device or finger, so it may still be made more exact.
        const pin = { label: was?.label || '', lat, lon, precision: as, fresh: true };
        setTyped(null);
        setMoveIt(false);
        setProblem('');
        change(pin);
        if (pin.label) return;
        try {
            // A town's name to begin with. For that a square kilometre is close enough.
            const r = await api.post('/api/places/nearest', coarsened(lat, lon, Math.max(squareKm(as) || 0, 1)));
            const name = r.data.results?.[0]?.label;
            const now = latest.current.value;
            if (name && isPin(now) && !now.label && now.lat === lat && now.lon === lon) latest.current.onChange({ ...now, label: name });
        } catch (_) { /* they can name it themselves */ }
    };

    const whereIAm = () => {
        if (!navigator.geolocation) {
            setProblem("This browser can't tell where you are. Choose on a map instead.");
            return;
        }
        setLocating(true);
        setProblem('');
        navigator.geolocation.getCurrentPosition(
            ({ coords }) => {
                setLocating(false);
                const km = squareKm(latest.current.precision);
                putPin(coords.latitude, coords.longitude);
                // An open map follows. A closed one stays closed: its tiles would tell OpenStreetMap.
                setMap((open) => open && { lat: coords.latitude, lon: coords.longitude, z: zoomFor(km) });
                if (coords.accuracy > (km ?? 0.1) * 1000) {
                    setProblem(`Your device only knew where you are to within ${howFarOff(coords.accuracy)}. You can check it on the map.`);
                }
            },
            () => {
                setLocating(false);
                setProblem("We couldn't get where you are. Choose on a map instead.");
            },
            { enableHighAccuracy: precision === 'exact', timeout: 15_000, maximumAge: 60_000 },
        );
    };

    const toggleMap = () => {
        if (map) setMap(null);
        else if (isPin(value)) setMap({ lat: value.lat, lon: value.lon, z: zoomFor(squareKm(value.precision)) });
        else if (hasPoint(value)) setMap({ lat: value.lat, lon: value.lon, z: 11 });
        else setMap(WORLD);
    };

    const rounding = (next) => {
        setPrecision(next);
        if (!isPin(value)) return;
        if (!value.fresh && isFiner(next, value.precision)) {
            // What was stored is only the middle of its square: it can't be more exact by itself.
            setMap({ lat: value.lat, lon: value.lon, z: zoomFor(squareKm(next)) });
            setMoveIt(true);
            return;
        }
        setMoveIt(false);
        onChange({ ...value, precision: next });
    };

    const offTheMap = () => {
        onChange(words ? { label: words } : null);
        setTyped(null);
        setMap(null);
        setMoveIt(false);
    };

    const exactness = map || isPin(value);

    return (
        <div className="place-picker">
            <label htmlFor={inputId}>{label}</label>
            <input id={inputId} type="text" value={words} maxLength={120} autoComplete="off"
                   placeholder={person ? 'e.g. your suburb or town' : 'e.g. the hall, the suburb or the town'}
                   onChange={(e) => write(e.target.value)} />
            {found.length > 0 && (
                <>
                    <ul className="place-found" aria-label="Places with that name">
                        {found.map((place) => (
                            <li key={place.id}>
                                <button type="button" onClick={() => choose(place)}>
                                    {place.label}<small>{place.precision}</small>
                                </button>
                            </li>
                        ))}
                    </ul>
                    {credit && (
                        <a className="place-credit" href={credit.url} target="_blank" rel="noreferrer">{credit.text}</a>
                    )}
                </>
            )}
            {person && <p className="place-note">Other members see these words: a suburb or town is plenty.</p>}
            {value && linkedTo(value) && (
                <p className={`place-state${hasPoint(value) ? ' is-linked' : ''}`} role="status">{linkedTo(value)}</p>
            )}
            {isPin(value) && !words.trim() && <p className="place-problem">Give it a name above: that is what others see.</p>}

            <div className="place-buttons">
                <button type="button" className="place-btn" onClick={whereIAm} disabled={locating}>
                    {locating ? 'Finding you…' : 'Use where I am now'}
                </button>
                <button type="button" className="place-btn" aria-expanded={!!map} onClick={toggleMap}>
                    {map ? 'Close the map' : 'Choose on a map'}
                </button>
                {hasPoint(value) && (
                    <button type="button" className="place-btn" onClick={offTheMap}>Take it off the map</button>
                )}
            </div>
            {problem && <p className="place-problem" role="alert">{problem}</p>}

            {exactness && (
                <>
                    <label className="place-precision">
                        How exact?
                        <select value={precision} onChange={(e) => rounding(e.target.value)}>
                            {PIN_PRECISIONS.map((p) => <option key={p.key} value={p.key}>{p.label}</option>)}
                        </select>
                    </label>
                    <p className="place-note">
                        {precision !== 'exact'
                            ? 'It is rounded to that before it is saved.'
                            : person
                                ? 'It is saved exactly. Other members never get it: they only see a rough distance.'
                                : 'Everyone this is shown to will see the exact spot. Think twice if it is someone’s home.'}
                    </p>
                </>
            )}
            {moveIt && <p className="place-problem" role="status">To be more exact, put the pin again on the map.</p>}

            {map && (
                <div className="place-map">
                    <SlippyMap view={map} onView={setMap} crosshair km={squareKm(precision)} />
                    <button type="button" className="place-btn place-btn--main"
                            onClick={() => { putPin(map.lat, map.lon); setMap(null); }}>
                        Put the pin here
                    </button>
                </div>
            )}
        </div>
    );
}

PlacePicker.propTypes = {
    value: PropTypes.object,
    onChange: PropTypes.func.isRequired,
    person: PropTypes.bool,
    label: PropTypes.string,
};
