// MembersList — the People tab for a sphere / alliance / project. Shows every
// member with an avatar, a profile link, and a role badge. When the viewer can
// manage the entity, each other member gets promote/demote buttons wired to the
// role endpoints. Role display labels differ per kind (alliance uses the
// Lead / Board member vocabulary), but the stored role values are stable.
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import Avatar from './Avatar';
import api from '../api';
import '../styles/MembersList.css';

const ROLE_CONFIG = {
    sphere: {
        path: 'spheres',
        labels: { admin: 'Admin', member: 'Member' },
        // Actions the top role can apply to another member.
        assignable: [
            { value: 'admin', action: 'Make admin', when: (m) => m.role !== 'admin' },
            { value: 'member', action: 'Remove admin', when: (m) => m.role === 'admin' },
        ],
    },
    alliance: {
        path: 'alliances',
        labels: { admin: 'Lead', steward: 'Board member', member: 'Member' },
        assignable: [
            { value: 'steward', action: 'Make board member', when: (m) => m.role === 'member' },
            { value: 'member', action: 'Remove from board', when: (m) => m.role === 'steward' },
        ],
    },
    project: {
        path: 'projects',
        labels: { manager: 'Manager', steward: 'Steward', contributor: 'Contributor' },
        assignable: [
            { value: 'steward', action: 'Promote to steward', when: (m) => m.role === 'contributor' },
            { value: 'contributor', action: 'Demote to contributor', when: (m) => m.role === 'steward' },
        ],
    },
};

export default function MembersList({ kind, entityId, members = [], canManage = false, currentUserId, onChanged }) {
    const [busyId, setBusyId] = useState(null);
    const [error, setError] = useState('');
    const cfg = ROLE_CONFIG[kind] || ROLE_CONFIG.sphere;

    const setRole = async (memberId, role) => {
        setBusyId(memberId);
        setError('');
        try {
            await api.post(`/api/${cfg.path}/${entityId}/members/${memberId}/role`, { role });
            if (onChanged) await onChanged();
        } catch (e) {
            setError(e.response?.data?.message || 'Could not update role.');
        } finally {
            setBusyId(null);
        }
    };

    if (members.length === 0) {
        return <p className="empty-state">No members yet.</p>;
    }

    return (
        <div className="members-list">
            {error && <p className="members-error">{error}</p>}
            {members.map((m) => (
                <div key={m.id} className="member-row">
                    <Avatar userId={m.id} name={m.name} size={40} />
                    <div className="member-main">
                        <Link to={m.id === currentUserId ? '/profile' : `/user?id=${m.id}`} className="member-name">
                            {m.name}{m.id === currentUserId ? ' (you)' : ''}
                        </Link>
                        <span className={`member-role role--${m.role}`}>{cfg.labels[m.role] || m.role}</span>
                    </div>
                    {canManage && m.id !== currentUserId && (
                        <div className="member-actions">
                            {cfg.assignable.filter((r) => r.when(m)).map((r) => (
                                <button
                                    key={r.value}
                                    className="member-role-btn"
                                    disabled={busyId === m.id}
                                    onClick={() => setRole(m.id, r.value)}
                                >
                                    {busyId === m.id ? '…' : r.action}
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}
