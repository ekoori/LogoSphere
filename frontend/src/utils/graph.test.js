import { describe, expect, it } from 'vitest';
import { closestTo, visibleGraph } from './graph';
import { createLayout } from './forceLayout';

const node = (id, more = {}) => ({ id, card: { title: `Card ${id}` }, owner: { id: `o-${id}`, name: `Owner ${id}` }, ...more });
const graph = {
    nodes: [node('a', { mine: true, near: true }), node('b', { near: true }), node('c', { is_demo: true }), node('d')],
    edges: [{ a: 'a', b: 'b', closeness: 0.5 }, { a: 'b', b: 'c', closeness: 0.3 }, { a: 'c', b: 'd', closeness: 0.05 }],
};
const ids = (g) => g.nodes.map((n) => n.id).join('');

describe('what the graph shows', () => {
    it('shows everything, and only connections close enough', () => {
        const all = visibleGraph(graph, { from: 0.12 });
        expect(ids(all)).toBe('abcd');
        expect(all.edges).toHaveLength(2);
        expect(all.degree.get('b')).toBe(2);
    });
    it('mine is your cards and what they connect to', () => {
        expect(ids(visibleGraph(graph, { scope: 'mine', from: 0.12 }))).toBe('ab');
    });
    it('near is your spheres', () => {
        expect(ids(visibleGraph(graph, { scope: 'near' }))).toBe('ab');
    });
    it('leaves out the demonstration when asked', () => {
        const g = visibleGraph(graph, { demos: false });
        expect(ids(g)).toBe('abd');
        expect(g.edges).toHaveLength(1);
    });
    it('a search keeps what the matches connect to', () => {
        const g = visibleGraph(graph, { query: 'card a', from: 0.12 });
        expect(ids(g)).toBe('ab');
        expect([...g.found]).toEqual(['a']);
    });
    it('focus is one card and its neighbours; owner, one owner’s', () => {
        expect(ids(visibleGraph(graph, { focus: 'c', from: 0.12 }))).toBe('bc');
        expect(ids(visibleGraph(graph, { owner: 'o-d', from: 0.12 }))).toBe('d');
    });
    it('lists connections closest first', () => {
        expect(closestTo('b', graph.edges).map((c) => c.other)).toEqual(['a', 'c']);
    });
});

describe('the layout', () => {
    const links = [{ a: 'a', b: 'b', weight: 0.9 }];
    const settled = (order) => {
        const layout = createLayout(order, links);
        layout.settle();
        return layout;
    };
    const gap = (l, p, q) => Math.hypot(l.byId.get(p).x - l.byId.get(q).x, l.byId.get(p).y - l.byId.get(q).y);

    it('is the same picture whatever the order', () => {
        expect(settled(['a', 'b', 'c', 'd']).positions()).toEqual(settled(['d', 'c', 'b', 'a']).positions());
    });
    it('draws close cards nearer, without piling them up', () => {
        const l = settled(['a', 'b', 'c', 'd']);
        expect(gap(l, 'a', 'b')).toBeLessThan(gap(l, 'a', 'c') * 0.7);
        expect(gap(l, 'a', 'b')).toBeGreaterThan(12);
    });
    it('even a faint connection sits nearer than none, and a strong one nearer still', () => {
        const drawn = (weight) => {
            const l = createLayout(['a', 'b', 'c', 'd'], [{ a: 'a', b: 'b', weight }]);
            l.settle();
            return l;
        };
        const faint = drawn(0.12);
        [['a', 'c'], ['a', 'd'], ['b', 'c'], ['b', 'd'], ['c', 'd']].forEach(([p, q]) => {
            expect(gap(faint, 'a', 'b')).toBeLessThan(gap(faint, p, q));
        });
        expect(gap(drawn(0.9), 'a', 'b')).toBeLessThan(gap(faint, 'a', 'b'));
    });
    it('holds together for a big, dense graph', () => {
        const all = Array.from({ length: 160 }, (_, i) => `n${i}`);
        const dense = all.flatMap((id, i) => Array.from({ length: 12 }, (_, j) => (
            { a: id, b: all[(i + j + 1) % (i < 40 ? 40 : 160)], weight: ((i * j) % 10) / 10 }
        ))).filter((l) => l.a !== l.b);
        const l = createLayout(all, dense);
        l.settle();
        l.nodes.forEach((n) => expect(Math.hypot(n.x, n.y)).toBeLessThan(2500));
    });
});
