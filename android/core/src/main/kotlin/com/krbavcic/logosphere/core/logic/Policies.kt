package com.krbavcic.logosphere.core.logic

import com.krbavcic.logosphere.core.model.Community
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.GroupPolicy

/**
 * A group's policies: which a kind has, their allowed values (backend/app/routes/entities.py
 * POLICY_FIELDS) and how the web words them (EntityManagement.js, GovernancePanel.js).
 */
object Policies {
    /** One policy field of a kind: its API name, its label, and each value with its wording. */
    data class Field(val key: String, val label: String, val options: List<Pair<String, String>>)

    private val JOIN = Field(
        "join_policy", "Membership join policy",
        listOf("open" to "Open — anyone can join directly", "approval" to "Approval required"),
    )
    private val DECISION = Field(
        "decision_policy", "How decisions pass",
        listOf(
            "majority" to "Simple majority — more weighted yes than no",
            "supermajority" to "Two-thirds supermajority",
            "consensus" to "Consensus — no weighted no votes",
        ),
    )
    private val PM = Field(
        "pm_policy", "Projects managed by",
        listOf("single-pm" to "Each project's own manager", "board" to "The Lead and Board members too"),
    )
    private val CONFIRM = Field(
        "confirm_policy", "Acceptances of the alliance's openings confirmed by",
        listOf("lead" to "The Lead only", "board" to "The Lead and Board members", "any-member" to "Any member"),
    )
    private val PHASE = Field(
        "phase", "Project phase",
        listOf("ongoing" to "Ongoing — taking openings and contributors", "closed" to "Closed — archived; no new openings"),
    )

    /** The fields a manager may set directly, per kind (a sphere's public/sandbox flags are separate). */
    fun fields(kind: CommunityKind): List<Field> = when (kind) {
        CommunityKind.Sphere -> listOf(JOIN, DECISION)
        CommunityKind.Alliance -> listOf(JOIN, DECISION, PM, CONFIRM)
        CommunityKind.Project -> listOf(JOIN, DECISION, PHASE)
    }

    /** The value [community] has for [key], or the server's default when it has none. */
    fun valueOf(community: Community, key: String): String = when (key) {
        "join_policy" -> community.joinPolicy
        "decision_policy" -> community.decisionPolicy
        "pm_policy" -> community.pmPolicy
        "confirm_policy" -> community.confirmPolicy
        "phase" -> community.phase
        else -> null
    } ?: default(key)

    fun default(key: String): String = when (key) {
        "join_policy" -> "open"
        "decision_policy" -> "majority"
        "pm_policy" -> "single-pm"
        "confirm_policy" -> "board"
        "phase" -> "ongoing"
        else -> ""
    }

    private val VALUE_LABELS = mapOf(
        "open" to "Open — anyone can join", "approval" to "Approval required",
        "majority" to "Simple majority", "supermajority" to "Two-thirds supermajority", "consensus" to "Consensus",
        "true" to "On", "false" to "Off",
        "single-pm" to "Each project's own manager", "board" to "Lead and Board members",
        "lead" to "The Lead only", "any-member" to "Any member",
        "ongoing" to "Ongoing", "closed" to "Closed (archived)",
    )

    /** A policy value in words, as the governance panel shows it. */
    fun valueLabel(value: String?): String = value?.let { VALUE_LABELS[it] ?: it.replace('-', ' ') } ?: "—"

    /** How proposals pass under [decisionPolicy], for "Proposals pass by …". */
    fun decisionCopy(decisionPolicy: String?): String = when (decisionPolicy) {
        "supermajority" -> "a two-thirds supermajority of weighted yes and no votes"
        "consensus" -> "consensus — at least one yes and no weighted no votes"
        "majority", null -> "a simple majority — more weighted yes than no"
        else -> decisionPolicy
    }

    /** What a policy proposal may change [policy] to: every option but the current value. */
    fun proposalOptions(key: String, policy: GroupPolicy): List<String> {
        val current = policy.value ?: if (key == "join_policy") "open" else null
        return policy.options.filter { it != current }
    }
}
