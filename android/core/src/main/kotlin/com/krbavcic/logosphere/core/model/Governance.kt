package com.krbavcic.logosphere.core.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// Liquid democracy for a sphere, alliance or project (backend/app/routes/governance.py): members
// propose a policy change (applied when it passes) or a motion, vote yes / no / abstain, and may
// lend their vote to another member. Delegation is transitive; a direct vote always overrides it.

/** One policy a group may vote on: its value now, what it may become, and its name. */
@Serializable
data class GroupPolicy(
    val value: String? = null,
    val label: String = "",
    val options: List<String> = emptyList(),
)

/** A weighted count: each vote carries its voter plus everyone whose delegation ends with them. */
@Serializable
data class Tally(
    val yes: Int = 0,
    val no: Int = 0,
    val abstain: Int = 0,
    val eligible: Int = 0,
    val unrepresented: Int = 0,
    @SerialName("direct_votes") val directVotes: Int? = null,
)

@Serializable
data class Proposal(
    @SerialName("proposal_id") val id: String,
    /** "policy" or "motion". */
    val kind: String = "motion",
    val title: String = "",
    val description: String? = null,
    @SerialName("policy_key") val policyKey: String? = null,
    @SerialName("policy_value") val policyValue: String? = null,
    @SerialName("policy_label") val policyLabel: String? = null,
    /** open, passed, rejected or withdrawn. */
    val status: String = "open",
    @SerialName("created_by") val createdBy: String? = null,
    @SerialName("created_by_name") val createdByName: String? = null,
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("closes_at") val closesAt: String? = null,
    @SerialName("closed_at") val closedAt: String? = null,
    @SerialName("decision_policy") val decisionPolicy: String? = null,
    val tally: Tally? = null,
    @SerialName("would_pass") val wouldPass: Boolean = false,
    @SerialName("my_vote") val myVote: String? = null,
) {
    val isOpen: Boolean get() = status == "open"
    val isPolicy: Boolean get() = kind == "policy"
}

/** `GET /api/<kind>s/<id>/governance`. */
@Serializable
data class GroupGovernance(
    @SerialName("decision_policy") val decisionPolicy: String = "majority",
    /** Keyed by policy (join_policy, decision_policy, …), in the server's order. */
    val policies: Map<String, GroupPolicy> = emptyMap(),
    @SerialName("can_manage") val canManage: Boolean = false,
    @SerialName("is_member") val isMember: Boolean = false,
    val members: List<PersonRef> = emptyList(),
    @SerialName("my_delegate") val myDelegate: PersonRef? = null,
    @SerialName("delegated_to_me") val delegatedToMe: List<PersonRef> = emptyList(),
    val proposals: List<Proposal> = emptyList(),
) {
    val open: List<Proposal> get() = proposals.filter { it.isOpen }
    val decided: List<Proposal> get() = proposals.filterNot { it.isOpen }
}

/** A new proposal: a policy change (key and value) or a free-text motion. */
data class NewProposal(
    val kind: String,
    val title: String,
    val description: String,
    val days: Int,
    val policyKey: String? = null,
    val policyValue: String? = null,
)
