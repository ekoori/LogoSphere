// The Meaning Graph drawn: a canvas you can pan, zoom, drag and tap, like a
// note-graph. Colour is the kind of meaning; a circle is a person's card, a
// square a group's, and the glyph inside says the kind without colour; size
// is how many connections it has (never likes).
// The List view on the page is the same data for keyboards and screen readers.
import React, { useCallback, useEffect, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import { createLayout } from '../utils/forceLayout';
import { kindOf, titleOf } from '../utils/graph';

const MIN_ZOOM = 0.2;
const MAX_ZOOM = 4;
const HIT_PX = 16; // at least this far from a node still hits it
const LABEL_ZOOM = 1.05;
const STEPS_A_FRAME = 2; // so it settles in about two seconds
const ZOOM_BUTTONS = { wide: 56, high: 144 }; // their corner: no label runs under them
const GLYPH_FROM = 5; // smaller than this and the glyph is a smudge
const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));
const radiusFor = (degree) => 5.5 + Math.min(9, Math.sqrt(degree || 0) * 2.3);
const stillPlease = () => !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
const short = (text) => (text.length > 34 ? `${text.slice(0, 32)}…` : text);

function readColours(el) {
    const css = getComputedStyle(el);
    const get = (name) => css.getPropertyValue(name).trim();
    return {
        creative: get('--mg-creative'),
        experiential: get('--mg-experiential'),
        attitudinal: get('--mg-attitudinal'),
        surface: get('--mg-surface'),
        edge: get('--mg-edge'),
        edgeLit: get('--mg-edge-lit'),
        ink: get('--mg-ink'),
        font: css.fontFamily,
    };
}

export default function GraphCanvas({ nodes, edges, degree, found, selected, onSelect, theme }) {
    const wrap = useRef(null);
    const canvas = useRef(null);
    const state = useRef({
        layout: null, view: { x: 0, y: 0, k: 1 }, touched: false, pointers: new Map(), frame: 0, width: 0, height: 0,
    });
    const latest = useRef({});
    const [tip, setTip] = useState(null);
    const hovered = tip?.id || null;
    latest.current = { nodes, edges, degree, found, selected, hovered };

    const draw = useCallback(() => {
        const s = state.current;
        const el = canvas.current;
        if (!el || !s.layout || !s.width) return;
        const c = s.colours;
        const { nodes: ns, edges: es, degree: deg, found: hits, selected: sel, hovered: over } = latest.current;
        const ctx = el.getContext('2d');
        const dpr = window.devicePixelRatio || 1;
        const { x: ox, y: oy, k } = s.view;
        const px = (p) => s.width / 2 + ox + p.x * k;
        const py = (p) => s.height / 2 + oy + p.y * k;
        const pos = s.layout.byId;
        const scale = clamp(Math.sqrt(k), 0.7, 1.7);

        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.clearRect(0, 0, s.width, s.height);

        const centre = over || sel;
        const lit = new Set(centre && pos.has(centre) ? [centre] : []);
        if (lit.size) es.forEach((e) => {
            if (e.a === centre) lit.add(e.b);
            if (e.b === centre) lit.add(e.a);
        });
        const searching = hits && hits.size < ns.length;
        const bright = (id) => (lit.size ? lit.has(id) : !searching || hits.has(id));

        es.forEach((e) => {
            const a = pos.get(e.a);
            const b = pos.get(e.b);
            if (!a || !b) return;
            const on = lit.size ? e.a === centre || e.b === centre : false;
            ctx.globalAlpha = lit.size && !on ? 0.16 : 1;
            ctx.strokeStyle = on ? c.edgeLit : c.edge;
            ctx.lineWidth = 0.8 + 1.6 * e.closeness;
            ctx.beginPath();
            ctx.moveTo(px(a), py(a));
            ctx.lineTo(px(b), py(b));
            ctx.stroke();
        });

        ns.forEach((n) => {
            const p = pos.get(n.id);
            if (!p) return;
            const r = radiusFor(deg.get(n.id)) * scale;
            ctx.globalAlpha = bright(n.id) ? 1 : 0.22;
            ctx.beginPath();
            if (n.owner.kind === 'user') ctx.arc(px(p), py(p), r, 0, Math.PI * 2);
            else ctx.rect(px(p) - r * 0.89, py(p) - r * 0.89, r * 1.78, r * 1.78);
            ctx.fillStyle = c[kindOf(n).key];
            ctx.fill();
            // A ring in the surface colour keeps touching marks apart.
            ctx.lineWidth = 2;
            ctx.strokeStyle = c.surface;
            ctx.stroke();
            if (r >= GLYPH_FROM) {
                ctx.font = `700 ${Math.round(r * 1.15)}px ${c.font}`;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = c.surface;
                ctx.fillText(kindOf(n).glyph, px(p), py(p) + 0.5);
            }
            if (n.id === sel || n.id === over) {
                ctx.beginPath();
                ctx.arc(px(p), py(p), r + 4, 0, Math.PI * 2);
                ctx.strokeStyle = c.ink;
                ctx.lineWidth = 2;
                ctx.stroke();
            }
        });

        // Labels where they fit: the one pointed at and its neighbours first, then the most connected.
        ctx.font = `600 12px ${c.font}`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        // A label may cover neither another label nor a node: under its node, else over it.
        const taken = [];
        const marks = ns.flatMap((n) => {
            const p = pos.get(n.id);
            if (!p || !bright(n.id)) return []; // a dimmed node may be written over
            const r = radiusFor(deg.get(n.id)) * scale;
            return [{ id: n.id, l: px(p) - r, r: px(p) + r, t: py(p) - r, b: py(p) + r }];
        });
        const overlaps = (box, o) => box.l < o.r && box.r > o.l && box.t < o.b && box.b > o.t;
        const rank = (n) => (n.id === centre ? 1e6 : 0) + (lit.has(n.id) ? 1e4 : 0) + (deg.get(n.id) || 0);
        const ordered = [...ns].sort((a, b) => rank(b) - rank(a) || a.id.localeCompare(b.id));
        const allow = lit.size || k >= LABEL_ZOOM || searching ? ordered.length : Math.max(6, Math.round(ordered.length / 5));
        ordered.forEach((n) => {
            if (taken.length >= allow) return; // so many that fit, not the first so many tried
            const p = pos.get(n.id);
            if (!p || !bright(n.id)) return;
            const x = px(p);
            const r = radiusFor(deg.get(n.id)) * scale;
            const text = short(titleOf(n));
            const w = ctx.measureText(text).width;
            const at = [py(p) + r + 4, py(p) - r - 18]
                .map((top) => ({ y: top, l: x - w / 2 - 3, r: x + w / 2 + 3, t: top - 1, b: top + 15 }))
                .find((box) => n.id === centre || (
                    box.l >= 0 && box.r <= s.width && box.t >= 0 && box.b <= s.height
                    && !(box.r > s.width - ZOOM_BUTTONS.wide && box.t < ZOOM_BUTTONS.high)
                    && !taken.some((o) => overlaps(box, o))
                    && !marks.some((o) => o.id !== n.id && overlaps(box, o))
                ));
            if (!at) return;
            taken.push(at);
            const { y } = at;
            ctx.globalAlpha = 1;
            ctx.lineWidth = 3;
            ctx.lineJoin = 'round';
            ctx.strokeStyle = c.surface;
            ctx.strokeText(text, x, y);
            ctx.fillStyle = c.ink;
            ctx.fillText(text, x, y);
        });
        ctx.globalAlpha = 1;
    }, []);

    const fit = useCallback(() => {
        const s = state.current;
        if (!s.layout?.nodes.length || !s.width) return;
        const xs = s.layout.nodes.map((n) => n.x);
        const ys = s.layout.nodes.map((n) => n.y);
        const [l, r, t, b] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
        const [side, ends] = [Math.min(130, s.width * 0.18), Math.min(90, s.height * 0.18)]; // room for labels
        const k = clamp(Math.min((s.width - side) / Math.max(r - l, 120), (s.height - ends) / Math.max(b - t, 120)), MIN_ZOOM, 1.6);
        s.view = { k, x: (-(l + r) / 2) * k, y: (-(t + b) / 2) * k - 6 };
    }, []);

    const animate = useCallback(() => {
        const s = state.current;
        cancelAnimationFrame(s.frame);
        const tick = () => {
            for (let i = 0; i < STEPS_A_FRAME && s.layout.moving(); i += 1) s.layout.step();
            if (!s.touched) fit();
            draw();
            if (s.layout.moving()) s.frame = requestAnimationFrame(tick);
        };
        s.frame = requestAnimationFrame(tick);
    }, [draw, fit]);

    // A new set of cards or connections: settle again from where things were.
    const shape = `${nodes.map((n) => n.id).join()}|${edges.map((e) => `${e.a}${e.b}${e.closeness}`).join()}`;
    useEffect(() => {
        const s = state.current;
        s.layout = createLayout(
            latest.current.nodes.map((n) => n.id),
            latest.current.edges.map((e) => ({ a: e.a, b: e.b, weight: e.closeness })),
            s.layout?.positions(),
        );
        // Other connections between the same cards keep the view you chose; other cards fit afresh.
        const cards = latest.current.nodes.map((n) => n.id).join();
        if (cards !== s.cards) s.touched = false;
        s.cards = cards;
        setTip(null);
        if (stillPlease() || document.hidden) {
            s.layout.settle();
            fit();
            draw();
        } else {
            // The first tangle sorts itself out unseen; the rest is worth watching.
            for (let i = 0; i < 40; i += 1) s.layout.step();
            animate();
        }
        return () => cancelAnimationFrame(s.frame);
    }, [shape, animate, draw, fit]);

    useEffect(() => {
        const s = state.current;
        const resize = () => {
            const rect = wrap.current.getBoundingClientRect();
            const dpr = window.devicePixelRatio || 1;
            s.width = rect.width;
            s.height = rect.height;
            canvas.current.width = Math.round(rect.width * dpr);
            canvas.current.height = Math.round(rect.height * dpr);
            if (!s.touched) fit();
            draw();
        };
        s.colours = readColours(wrap.current);
        resize();
        const watch = new ResizeObserver(resize);
        watch.observe(wrap.current);
        return () => watch.disconnect();
    }, [draw, fit]);

    useEffect(() => {
        state.current.colours = readColours(wrap.current);
        draw();
    }, [theme, draw]);

    useEffect(() => { draw(); }, [selected, hovered, found, degree, draw]);

    const zoomAt = useCallback((factor, x = null, y = null) => {
        const s = state.current;
        const v = s.view;
        const k = clamp(v.k * factor, MIN_ZOOM, MAX_ZOOM);
        const cx = (x ?? s.width / 2) - s.width / 2;
        const cy = (y ?? s.height / 2) - s.height / 2;
        s.view = { k, x: cx - ((cx - v.x) * k) / v.k, y: cy - ((cy - v.y) * k) / v.k };
        s.touched = true;
        draw();
    }, [draw]);

    useEffect(() => {
        const el = canvas.current;
        // Not React's onWheel: that listener is passive, and the page would scroll too.
        const wheel = (e) => {
            e.preventDefault();
            const r = el.getBoundingClientRect();
            zoomAt(Math.exp(-e.deltaY * 0.0015), e.clientX - r.left, e.clientY - r.top);
        };
        el.addEventListener('wheel', wheel, { passive: false });
        return () => el.removeEventListener('wheel', wheel);
    }, [zoomAt]);

    const at = (e) => {
        const r = canvas.current.getBoundingClientRect();
        return { x: e.clientX - r.left, y: e.clientY - r.top };
    };
    const nodeAt = (p) => {
        const s = state.current;
        let best = null;
        let bestGap = Infinity;
        s.layout?.nodes.forEach((n) => {
            const d = Math.hypot(s.width / 2 + s.view.x + n.x * s.view.k - p.x, s.height / 2 + s.view.y + n.y * s.view.k - p.y);
            const reach = Math.max(HIT_PX, radiusFor(degree.get(n.id)) * 1.7 + 2);
            if (d <= reach && d < bestGap) {
                best = n;
                bestGap = d;
            }
        });
        return best;
    };

    const down = (e) => {
        const s = state.current;
        canvas.current.setPointerCapture?.(e.pointerId);
        const p = at(e);
        s.pointers.set(e.pointerId, p);
        if (s.pointers.size === 1) {
            s.press = { start: p, node: nodeAt(p), moved: false };
        } else if (s.press) {
            if (s.press.node) s.press.node.held = false;
            s.press = { ...s.press, node: null, moved: true };
        }
    };

    const move = (e) => {
        const s = state.current;
        const p = at(e);
        const was = s.pointers.get(e.pointerId);
        if (!was) {
            const n = nodeAt(p);
            setTip(n ? { id: n.id, x: p.x, y: p.y } : null);
            return;
        }
        if (s.pointers.size === 2) {
            const other = [...s.pointers.entries()].find(([id]) => id !== e.pointerId)[1];
            const before = Math.hypot(was.x - other.x, was.y - other.y) || 1;
            zoomAt(Math.hypot(p.x - other.x, p.y - other.y) / before, (p.x + other.x) / 2, (p.y + other.y) / 2);
        } else if (s.press) {
            if (Math.hypot(p.x - s.press.start.x, p.y - s.press.start.y) > 5) s.press.moved = true;
            if (s.press.moved) {
                s.touched = true;
                setTip(null);
                const n = s.press.node;
                if (n) {
                    n.held = true;
                    n.x += (p.x - was.x) / s.view.k;
                    n.y += (p.y - was.y) / s.view.k;
                    if (stillPlease()) draw();
                    else {
                        s.layout.reheat();
                        animate();
                    }
                } else {
                    s.view.x += p.x - was.x;
                    s.view.y += p.y - was.y;
                    draw();
                }
            }
        }
        s.pointers.set(e.pointerId, p);
    };

    const up = (e) => {
        const s = state.current;
        s.pointers.delete(e.pointerId);
        if (s.pointers.size) return;
        if (s.press?.node) s.press.node.held = false;
        if (s.press && !s.press.moved && e.type === 'pointerup') onSelect(s.press.node?.id || null);
        s.press = null;
    };

    const key = (e) => {
        const s = state.current;
        const pan = { ArrowLeft: [40, 0], ArrowRight: [-40, 0], ArrowUp: [0, 40], ArrowDown: [0, -40] }[e.key];
        if (pan) {
            s.view.x += pan[0];
            s.view.y += pan[1];
            s.touched = true;
            draw();
        } else if (e.key === '+' || e.key === '=') zoomAt(1.25);
        else if (e.key === '-') zoomAt(0.8);
        else if (e.key === 'Escape') onSelect(null);
        else return;
        e.preventDefault();
    };

    const reset = () => {
        state.current.touched = false;
        fit();
        draw();
    };
    const tipNode = tip && nodes.find((n) => n.id === tip.id);

    return (
        <div className="mg-canvas" ref={wrap}>
            <canvas
                ref={canvas}
                tabIndex={0}
                role="img"
                aria-label={`Meaning Graph: ${nodes.length} value cards, ${edges.length} connections. “See it as a list” has the same as text.`}
                style={{ cursor: hovered ? 'pointer' : 'grab' }}
                onPointerDown={down}
                onPointerMove={move}
                onPointerUp={up}
                onPointerCancel={up}
                onPointerLeave={() => setTip(null)}
                onKeyDown={key}
            />
            {tipNode && (
                <div className="mg-tip" style={{ left: clamp(tip.x + 14, 4, Math.max(4, state.current.width - 236)), top: clamp(tip.y + 14, 4, Math.max(4, state.current.height - 76)) }}>
                    <strong>{titleOf(tipNode)}</strong>
                    <span>{kindOf(tipNode).glyph} {kindOf(tipNode).label} · {tipNode.owner.name}</span>
                    <span>{degree.get(tipNode.id) || 0} connection{degree.get(tipNode.id) === 1 ? '' : 's'}</span>
                </div>
            )}
            <div className="mg-zoom">
                <button type="button" onClick={() => zoomAt(1.3)} aria-label="Zoom in">+</button>
                <button type="button" onClick={() => zoomAt(0.77)} aria-label="Zoom out">−</button>
                <button type="button" onClick={reset} aria-label="Fit everything in">⤢</button>
            </div>
        </div>
    );
}

GraphCanvas.propTypes = {
    nodes: PropTypes.array.isRequired,
    edges: PropTypes.array.isRequired,
    degree: PropTypes.instanceOf(Map).isRequired,
    found: PropTypes.instanceOf(Set),
    selected: PropTypes.string,
    onSelect: PropTypes.func.isRequired,
    theme: PropTypes.string,
};
