// Only a map, for the Android app to show (no header, no account, no API).
// Where to start comes in the fragment, which never reaches the server or its
// logs; the chosen point goes back to the app through the bridge it provides.
import React, { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { coordinatesFromHash } from '../utils/mapHash';
import { zoomFor } from '../utils/mercator';
import SlippyMap from '../components/SlippyMap';
import '../styles/Places.css';

export default function MapPickerPage() {
    const { hash } = useLocation();
    const [start] = useState(() => coordinatesFromHash(hash));
    const [view, setView] = useState(() => ({
        lat: start.lat ?? 10,
        lon: start.lon ?? 20,
        z: start.lat === null ? 2 : zoomFor(start.km),
    }));
    const app = window.LogoSphereMap;

    return (
        <div className="map-only">
            <SlippyMap view={view} onView={setView} crosshair km={start.km} />
            <div className="map-only-foot">
                {app ? (
                    <button type="button" className="place-btn place-btn--main" onClick={() => app.picked(view.lat, view.lon)}>
                        Put the pin here
                    </button>
                ) : (
                    <p className="place-note">This map is part of the LogoSphere app.</p>
                )}
            </div>
        </div>
    );
}
