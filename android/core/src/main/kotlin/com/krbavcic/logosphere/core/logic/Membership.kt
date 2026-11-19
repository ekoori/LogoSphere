package com.krbavcic.logosphere.core.logic

import com.krbavcic.logosphere.core.model.Community
import com.krbavcic.logosphere.core.model.CommunityKind

/**
 * A viewer's standing in a sphere, alliance or project — the web's `usePermissions`, mirroring
 * backend/app/utils/permissions.py:
 *   sphere   — admin1 or role admin manage
 *   alliance — admin (Lead) or steward (Board member) manage
 *   project  — manager or steward manage
 * A platform admin may manage anything.
 */
object Membership {
    private val MANAGE_ROLES = mapOf(
        CommunityKind.Sphere to setOf("admin"),
        CommunityKind.Alliance to setOf("admin", "steward"),
        CommunityKind.Project to setOf("manager", "steward"),
    )

    fun role(community: Community, userId: String?): String? =
        userId?.let { id -> community.members.firstOrNull { it.id == id }?.role }

    /** A member in good standing (a request awaiting approval doesn't count). */
    fun isMember(community: Community, userId: String?): Boolean =
        userId != null && community.members.any { it.id == userId && it.role != "pending" }

    fun canManage(community: Community, userId: String?, isPlatformAdmin: Boolean): Boolean {
        if (userId == null) return false
        if (isPlatformAdmin || community.canManage || community.admin1 == userId) return true
        return role(community, userId) in MANAGE_ROLES.getValue(community.kind)
    }

    /** Trail, openings and people are for members — and everyone, on a public sphere. */
    fun canViewActivity(community: Community, userId: String?, isPlatformAdmin: Boolean): Boolean =
        isMember(community, userId) || isPlatformAdmin ||
            (community.kind == CommunityKind.Sphere && community.isPublic)

    /** Entities the viewer may act on behalf of, out of the given lists. */
    fun managed(all: List<Community>, userId: String?, isPlatformAdmin: Boolean): List<Community> =
        all.filter { canManage(it, userId, isPlatformAdmin) }
}
