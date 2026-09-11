// MembersList — the People tab for a sphere / alliance / project. Shows every
// member with an avatar, a profile link and a role badge; when the viewer may
// set roles, each other member gets promote/demote/remove actions and any
// pending join requests can be approved or declined. Role display labels
// differ per kind (alliances use Lead / Board member), stored values don't.
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import PropTypes from 'prop-types';
import Avatar from './Avatar';
import api from '../api';
import { KIND_PATH } from '../utils/queries';
import '../styles/MembersList.css';

const ROLE_CONFIG = {
    sphere: {
        labels: { admin: 'Admin', member: 'Member' },
        defaultRole: 'member',
        assignable: [
            { value: 'admin', action: 'Make admin', when: (m) => m.role !== 'admin' },
            { value: 'member', action: 'Remove admin', when: (m) => m.role === 'admin' },
        ],
    },
    alliance: {
        labels: { admin: 'Lead', steward: 'Board member', member: 'Member' },
        defaultRole: 'member',
        assignable: [
            { value: 'steward', action: 'Make board member', when: (m) => m.role === 'member' },
            { value: 'member', action: 'Remove from board', when: (m) => m.role === 'steward' },
        ],
    },
    project: {
        labels: { manager: 'Manager', steward: 'Steward', contributor: 'Contributor', observer: 'Observer' },
        defaultRole: 'contributor',
        assignable: [
            { value: 'steward', action: 'Promote to steward', when: (m) => m.role === 'contributor' },
            { value: 'contributor', action: 'Demote to contributor', when: (m) => m.role === 'steward' },
        ],
    },
};
const FOUNDER_ROLE = { sphere: 'admin', alliance: 'admin', project: 'manager' };

export default function MembersList({ kind, entityId, members = [], pending = [], canSetRoles = false, currentUserId, onChanged }) {
    const [busyId, setBusyId] = useState(null);
    const [error, setError] = useState('');
    const cfg = ROLE_CONFIG[kind] || ROLE_CONFIG.sphere;

    const setRole = async (memberId, role) => {
        setBusyId(memberId);
        setError('');
        try {
            await api.post(`/api/${KIND_PATH[kind]}/${entityId}/members/${memberId}/role`, { role });
            if (onChanged) await onChanged();
        } catch (e) {
            setError(e.response?.data?.message || 'Could not update role.');
        } finally {
            setBusyId(null);
        }
    };

    if (members.length === 0 && pending.length === 0) {
        return <p className="empty-state">No members yet.</p>;
    }

    return (
        <div className="members-list">
            {error && <p className="members-error">{error}</p>}

            {canSetRoles && pending.length > 0 && (
                <div className="members-pending">
                    <p className="members-pending-title">Awaiting approval ({pending.length})</p>
                    {pending.map((p) => (
                        <div key={p.id} className="member-row member-row--pending">
                            <Avatar userId={p.id} name={p.name} size={40} />
                            <div className="member-main">
                                <Link to={`/user?id=${p.id}`} className="member-name">{p.name}</Link>
                                <span className="member-role role--pending">Requested to join</span>
                            </div>
                            <div className="member-actions">
                                <button className="member-role-btn" disabled={busyId === p.id} onClick={() => setRole(p.id, cfg.defaultRole)}>
                                    {busyId === p.id ? '…' : '✓ Approve'}
                                </button>
                                <button className="member-role-btn member-role-btn--danger" disabled={busyId === p.id} onClick={() => setRole(p.id, 'remove')}>
                                    Decline
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {members.map((m) => {
                const isSelf = m.id === currentUserId;
                const isFounder = m.role === FOUNDER_ROLE[kind];
                return (
                    <div key={m.id} className="member-row">
                        <Avatar userId={m.id} name={m.name} size={40} />
                        <div className="member-main">
                            <Link to={isSelf ? '/profile' : `/user?id=${m.id}`} className="member-name">
                                {m.name}{isSelf ? ' (you)' : ''}
                            </Link>
                            <span className={`member-role role--${m.role}`}>{cfg.labels[m.role] || m.role}</span>
                        </div>
                        {canSetRoles && !isSelf && (
                            <div className="member-actions">
                                {cfg.assignable.filter((r) => r.when(m)).map((r) => (
                                    <button key={r.value} className="member-role-btn" disabled={busyId === m.id} onClick={() => setRole(m.id, r.value)}>
                                        {busyId === m.id ? '…' : r.action}
                                    </button>
                                ))}
                                {!isFounder && (
                                    <button className="member-role-btn member-role-btn--danger" disabled={busyId === m.id} onClick={() => setRole(m.id, 'remove')}>
                                        Remove
                                    </button>
                                )}
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
}

MembersList.propTypes = {
    kind: PropTypes.oneOf(['sphere', 'alliance', 'project']).isRequired,
    entityId: PropTypes.string,
    members: PropTypes.array,
    pending: PropTypes.array,
    canSetRoles: PropTypes.bool,
    currentUserId: PropTypes.string,
    onChanged: PropTypes.func,
};
