// A small force layout for the Meaning Graph: cards push each other apart,
// closeness pulls, everything leans to the middle. Deterministic: the same
// cards settle into the same picture (the app's ForceLayout.kt is its twin).
// No randomness, no dependency.
const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));
const COOLING = 0.985;
const SETTLED = 0.012;
// Tuned so that linked cards sit nearer than unlinked ones: weak links are
// shorter than the room unlinked cards give each other, strong ones shorter still.
const PUSH = 6000;
const LEAN = 0.012;
const NEAR = 16;
const SPAN = 40;
const PULL = 0.03;
const MORE_PULL = 0.4;
const KEEP_SPEED = 0.58;
const TOP_SPEED = 30;

/** @param links [{a, b, weight}] with weight 0..1 */
export function createLayout(ids, links, previous = new Map()) {
    const nodes = [...ids].sort().map((id, i) => {
        const was = previous.get(id);
        const r = 26 * Math.sqrt(i + 0.5);
        return {
            id, vx: 0, vy: 0, held: false,
            x: was ? was.x : r * Math.cos(i * GOLDEN_ANGLE),
            y: was ? was.y : r * Math.sin(i * GOLDEN_ANGLE),
        };
    });
    const byId = new Map(nodes.map((n) => [n.id, n]));
    const joined = links.filter((l) => byId.has(l.a) && byId.has(l.b));
    const count = new Map();
    joined.forEach((l) => [l.a, l.b].forEach((id) => count.set(id, (count.get(id) || 0) + 1)));
    const springs = joined
        .map((l) => {
            // The square root spreads out the low end, where most closeness is.
            const t = Math.sqrt(Math.min(1, Math.max(0, l.weight)));
            return {
                a: byId.get(l.a),
                b: byId.get(l.b),
                length: NEAR + SPAN * (1 - t),
                // A card with many connections mustn't drag its whole neighbourhood into one knot.
                pull: (PULL + MORE_PULL * t) / Math.sqrt(Math.min(count.get(l.a), count.get(l.b))),
            };
        })
        .sort((p, q) => p.a.id.localeCompare(q.a.id) || p.b.id.localeCompare(q.b.id));
    let heat = previous.size ? 0.45 : 1;

    function step() {
        for (let i = 0; i < nodes.length; i += 1) {
            const p = nodes[i];
            for (let j = i + 1; j < nodes.length; j += 1) {
                const q = nodes[j];
                let dx = q.x - p.x;
                let dy = q.y - p.y;
                let d2 = dx * dx + dy * dy;
                if (d2 < 0.01) {
                    dx = Math.cos(i + j);
                    dy = Math.sin(i + j);
                    d2 = 1;
                }
                const d = Math.sqrt(d2);
                const f = (PUSH * heat) / Math.max(d2, 120);
                p.vx -= (dx / d) * f;
                p.vy -= (dy / d) * f;
                q.vx += (dx / d) * f;
                q.vy += (dy / d) * f;
            }
        }
        springs.forEach(({ a, b, length, pull }) => {
            const dx = b.x - a.x;
            const dy = b.y - a.y;
            const d = Math.sqrt(dx * dx + dy * dy) || 1;
            const f = (d - length) * pull * heat;
            a.vx += (dx / d) * f;
            a.vy += (dy / d) * f;
            b.vx -= (dx / d) * f;
            b.vy -= (dy / d) * f;
        });
        nodes.forEach((n) => {
            if (n.held) {
                n.vx = 0;
                n.vy = 0;
                return;
            }
            n.vx = (n.vx - n.x * LEAN * heat) * KEEP_SPEED;
            n.vy = (n.vy - n.y * LEAN * heat) * KEEP_SPEED;
            const speed = Math.sqrt(n.vx * n.vx + n.vy * n.vy);
            const brake = speed > TOP_SPEED ? TOP_SPEED / speed : 1;
            n.x += n.vx * brake;
            n.y += n.vy * brake;
        });
        heat *= COOLING;
    }

    return {
        nodes,
        byId,
        step,
        moving: () => heat > SETTLED,
        reheat: () => { heat = Math.max(heat, 0.3); },
        settle: () => {
            for (let i = 0; i < 400 && heat > SETTLED; i += 1) step();
        },
        positions: () => new Map(nodes.map((n) => [n.id, { x: n.x, y: n.y }])),
    };
}
