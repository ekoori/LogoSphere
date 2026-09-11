// EntityListPage — /spheres, /alliances, /projects. One page replaces the
// three copies. Lists come from the query layer (cached, shared with every
// other page that needs them) with value cards embedded, so a page of cards
// is one request. The search box is real; the old placeholder filter buttons
// that did nothing are gone.
import React, { useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import api from '../api';
import EntityForm from '../components/EntityForm';
import EntityCard from '../components/EntityCard';
import { useEntityList, useInvalidate, KIND_PATH, ID_KEY } from '../utils/queries';
import '../styles/EntityCard.css';

const COPY = {
    sphere: { plural: 'Spheres', empty: 'No spheres yet. Be the first to start a community.', create: 'Create Sphere' },
    alliance: { plural: 'Alliances', empty: 'No alliances yet. Gather a few people and start one.', create: 'Create Alliance' },
    project: { plural: 'Projects', empty: 'No projects yet. Start a shared mission for your community.', create: 'Create Project' },
};

export default function EntityListPage({ kind }) {
    const copy = COPY[kind];
    const { data, isLoading, isError, error } = useEntityList(kind);
    const invalidate = useInvalidate();
    const [formVisible, setFormVisible] = useState(false);
    const [search, setSearch] = useState('');

    const rows = useMemo(() => {
        const list = (data || []).filter((e) => e.name);
        const q = search.trim().toLowerCase();
        if (!q) return list;
        return list.filter((e) =>
            (e.name || '').toLowerCase().includes(q)
            || (e.description || '').toLowerCase().includes(q)
            || (e.sphere_name || '').toLowerCase().includes(q)
            || (e.value_cards || []).some((c) => (c.title || '').toLowerCase().includes(q)));
    }, [data, search]);

    const handleJoin = async (id) => {
        const res = await api.post(`/api/${KIND_PATH[kind]}/${id}/join`);
        await invalidate.entity(kind, id);
        return res.data;
    };

    return (
        <div className="container">
            <aside>
                <div className="search-box">
                    <input
                        type="search"
                        placeholder={`Search ${copy.plural}…`}
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        aria-label={`Search ${copy.plural}`}
                    />
                </div>
                <button className="btn-orange" onClick={() => setFormVisible((v) => !v)}>
                    {formVisible ? 'Cancel' : copy.create}
                </button>
            </aside>
            <main>
                <EntityForm
                    kind={kind}
                    isVisible={formVisible}
                    onCreated={() => setFormVisible(false)}
                    onCancel={() => setFormVisible(false)}
                />
                {isLoading ? (
                    <p className="entity-list-status">Loading {copy.plural.toLowerCase()}…</p>
                ) : isError ? (
                    <p className="entity-list-error">Could not load {copy.plural.toLowerCase()}: {error?.response?.data?.message || 'please try again.'}</p>
                ) : rows.length === 0 ? (
                    <p className="empty-state">{search ? `Nothing matches “${search}”.` : copy.empty}</p>
                ) : (
                    <div className="entity-grid">
                        {rows.map((e) => (
                            <EntityCard key={e[ID_KEY[kind]] || e.id} kind={kind} entity={e} onJoin={handleJoin} />
                        ))}
                    </div>
                )}
            </main>
        </div>
    );
}

EntityListPage.propTypes = { kind: PropTypes.oneOf(['sphere', 'alliance', 'project']).isRequired };
