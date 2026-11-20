package com.krbavcic.logosphere.core.logic

import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.Member

/**
 * Roles in a sphere, alliance or project, as the web's MembersList words them. The stored values
 * are the server's (backend/app/routes/entities.py KINDS); only the labels differ per kind —
 * an alliance's admin is its Lead, its stewards the Board.
 */
object Roles {
    /** Something a manager may do to a member: set [role] (or `remove`), offered when [appliesTo]. */
    data class Action(val role: String, val label: String, val appliesTo: (Member) -> Boolean)

    const val REMOVE = "remove"

    fun founderRole(kind: CommunityKind): String = when (kind) {
        CommunityKind.Project -> "manager"
        else -> "admin"
    }

    /** The role an approved request becomes. */
    fun defaultRole(kind: CommunityKind): String = when (kind) {
        CommunityKind.Project -> "contributor"
        else -> "member"
    }

    fun label(kind: CommunityKind, role: String?): String = when (kind) {
        CommunityKind.Sphere -> mapOf("admin" to "Admin", "member" to "Member")
        CommunityKind.Alliance -> mapOf("admin" to "Lead", "steward" to "Board member", "member" to "Member")
        CommunityKind.Project -> mapOf("manager" to "Manager", "steward" to "Steward", "contributor" to "Contributor", "observer" to "Observer")
    }[role] ?: role.orEmpty().replaceFirstChar { it.uppercase() }

    /** Promotions and demotions offered for [member]; removal is separate (never the founder). */
    fun actions(kind: CommunityKind, member: Member): List<Action> = when (kind) {
        CommunityKind.Sphere -> listOf(
            Action("admin", "Make admin") { it.role != "admin" },
            Action("member", "Remove admin") { it.role == "admin" },
        )
        CommunityKind.Alliance -> listOf(
            Action("steward", "Make board member") { it.role == "member" },
            Action("member", "Remove from board") { it.role == "steward" },
        )
        CommunityKind.Project -> listOf(
            Action("steward", "Promote to steward") { it.role == "contributor" },
            Action("contributor", "Demote to contributor") { it.role == "steward" },
        )
    }.filter { it.appliesTo(member) }

    /** The founder can't be removed (the server refuses). */
    fun canRemove(kind: CommunityKind, member: Member): Boolean = member.role != founderRole(kind)

    /** "the Lead or a Board member"…: who must approve a request, in words. */
    fun managerWord(kind: CommunityKind): String = when (kind) {
        CommunityKind.Sphere -> "an admin"
        CommunityKind.Alliance -> "a Lead or Board member"
        CommunityKind.Project -> "a manager"
    }

    /** What a group calls its people. */
    fun peopleWord(kind: CommunityKind): String = if (kind == CommunityKind.Project) "Contributors" else "Members"
}
