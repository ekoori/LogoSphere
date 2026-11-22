// A small map of OpenStreetMap's tiles: drag, pinch, wheel, buttons, arrow keys.
// Mounted only when someone asks for a map, so nothing is fetched from
// OpenStreetMap until then. Their tile policy: attribution shown, the browser's
// own Referer, no bulk or early fetching.
import React, { useCallback, useEffect, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import { MAX_ZOOM, MIN_ZOOM, TILE, project, squareAround, tilesFor, unproject } from '../utils/mercator';
import '../styles/Places.css';

const TILES = 'https://tile.openstreetmap.org';
const clamp = (z) => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, z));

export default function SlippyMap({ view, onView, pin = null, km = null, crosshair = false }) {
    const box = useRef(null);
    const touch = useRef({ points: new Map(), apart: 0 });
    const latest = useRef(view);
    const [size, setSize] = useState({ width: 0, height: 0 });
    latest.current = view;

    useEffect(() => {
        const el = box.current;
        const measure = () => setSize({ width: el.clientWidth, height: el.clientHeight });
        measure();
        const watch = new ResizeObserver(measure);
        watch.observe(el);
        return () => watch.disconnect();
    }, []);

    const move = useCallback((next) => {
        latest.current = next;
        onView(next);
    }, [onView]);

    const panBy = useCallback((dx, dy) => {
        const v = latest.current;
        const p = project(v.lat, v.lon, v.z);
        move({ ...unproject(p.x - dx, p.y - dy, v.z), z: v.z });
    }, [move]);

    const zoomBy = useCallback((steps) => {
        const v = latest.current;
        const z = clamp(v.z + steps);
        if (z !== v.z) move({ ...v, z });
    }, [move]);

    useEffect(() => {
        const el = box.current;
        let last = 0;
        const wheel = (e) => {
            e.preventDefault();
            if (e.timeStamp - last < 160) return;
            last = e.timeStamp;
            zoomBy(e.deltaY < 0 ? 1 : -1);
        };
        el.addEventListener('wheel', wheel, { passive: false });
        return () => el.removeEventListener('wheel', wheel);
    }, [zoomBy]);

    const down = (e) => {
        if (e.target.closest('a, button')) return;
        e.currentTarget.setPointerCapture?.(e.pointerId);
        touch.current.points.set(e.pointerId, { x: e.clientX, y: e.clientY });
        touch.current.apart = 0;
    };

    const drag = (e) => {
        const t = touch.current;
        const was = t.points.get(e.pointerId);
        if (!was) return;
        const now = { x: e.clientX, y: e.clientY };
        t.points.set(e.pointerId, now);
        if (t.points.size === 1) {
            panBy(now.x - was.x, now.y - was.y);
            return;
        }
        const [a, b] = [...t.points.values()];
        const apart = Math.hypot(a.x - b.x, a.y - b.y);
        if (!t.apart) t.apart = apart;
        else if (apart > t.apart * 1.45 || apart < t.apart * 0.69) {
            zoomBy(apart > t.apart ? 1 : -1);
            t.apart = apart;
        }
    };

    const up = (e) => {
        touch.current.points.delete(e.pointerId);
        touch.current.apart = 0;
    };

    const key = (e) => {
        if (e.target !== e.currentTarget) return;
        const by = { ArrowLeft: [60, 0], ArrowRight: [-60, 0], ArrowUp: [0, 60], ArrowDown: [0, -60] }[e.key];
        if (by) panBy(...by);
        else if (e.key === '+' || e.key === '=') zoomBy(1);
        else if (e.key === '-') zoomBy(-1);
        else return;
        e.preventDefault();
    };

    const centre = project(view.lat, view.lon, view.z);
    const world = TILE * 2 ** view.z;
    const onScreen = (lat, lon) => {
        const p = project(lat, lon, view.z);
        let dx = p.x - centre.x;
        if (dx > world / 2) dx -= world;
        if (dx < -world / 2) dx += world;
        return { left: size.width / 2 + dx, top: size.height / 2 + p.y - centre.y };
    };

    const marked = pin || (crosshair ? view : null);
    let square = null;
    if (marked && km) {
        const s = squareAround(marked.lat, marked.lon, km);
        const middle = onScreen(s.lat, s.lon);
        const width = (s.dLon / 360) * world;
        const height = project(s.lat - s.dLat / 2, s.lon, view.z).y - project(s.lat + s.dLat / 2, s.lon, view.z).y;
        square = { left: middle.left - width / 2, top: middle.top - height / 2, width, height };
    }

    return (
        <div
            className="map"
            ref={box}
            tabIndex={0}
            role="application"
            aria-label="Map. Drag it or use the arrow keys; plus and minus zoom."
            onPointerDown={down}
            onPointerMove={drag}
            onPointerUp={up}
            onPointerCancel={up}
            onKeyDown={key}
        >
            {size.width > 0 && tilesFor(view, size.width, size.height).map((t) => (
                <img key={t.key} className="map-tile" src={`${TILES}/${t.path}.png`} alt="" draggable={false}
                     style={{ left: t.left, top: t.top }} />
            ))}
            {square && <div className="map-square" style={square} />}
            {pin && !crosshair && <div className="map-pin" style={onScreen(pin.lat, pin.lon)} aria-hidden="true" />}
            {crosshair && <div className="map-pin map-pin--middle" aria-hidden="true" />}
            <div className="map-zoom">
                <button type="button" onClick={() => zoomBy(1)} aria-label="Zoom in">+</button>
                <button type="button" onClick={() => zoomBy(-1)} aria-label="Zoom out">&minus;</button>
            </div>
            <a className="map-credit" href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">
                &copy; OpenStreetMap contributors
            </a>
        </div>
    );
}

SlippyMap.propTypes = {
    view: PropTypes.shape({ lat: PropTypes.number, lon: PropTypes.number, z: PropTypes.number }).isRequired,
    onView: PropTypes.func.isRequired,
    pin: PropTypes.shape({ lat: PropTypes.number, lon: PropTypes.number }),
    km: PropTypes.number,
    crosshair: PropTypes.bool,
};
