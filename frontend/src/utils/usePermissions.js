// usePermissions — one place that answers "what may the current user do with
// this sphere/alliance/project?". Every page used to re-derive this from the
// members array with slightly different rules (and forgot platform admins on
// alliances and projects). The vocabulary mirrors backend permissions.py:
//   sphere:   admin1 / role 'admin' manage; anyone signed in may join
//   alliance: role 'admin' (Lead) or 'steward' (Board member) manage
//   project:  role 'manager' or 'steward' manage
import { useLogin } from '../App';

const MANAGE_ROLES = {
    sphere: ['admin'],
    alliance: ['admin', 'steward'],
    project: ['manager', 'steward'],
};
const TOP_ROLES = { sphere: 'admin', alliance: 'admin', project: 'manager' };

export function usePermissions(kind, entity) {
    const { userId, isPlatformAdmin } = useLogin();
    const members = entity?.members || [];
    const me = userId ? members.find((m) => String(m.id) === String(userId)) : null;
    const role = me?.role || null;
    const isMember = !!me;
    const isFounder = !!userId && (
        String(entity?.admin1 || '') === String(userId) || role === TOP_ROLES[kind]
    );
    const canManage = isPlatformAdmin || isFounder || (!!role && (MANAGE_ROLES[kind] || []).includes(role));
    // Only the top role (or a platform admin) may change other members' roles.
    const canSetRoles = isPlatformAdmin || isFounder;
    // Activity (trail, openings) is members-only, except a public sphere.
    const canViewActivity = isMember || isPlatformAdmin || (kind === 'sphere' && !!entity?.is_public);
    return { userId, isPlatformAdmin, role, isMember, isFounder, canManage, canSetRoles, canViewActivity };
}
