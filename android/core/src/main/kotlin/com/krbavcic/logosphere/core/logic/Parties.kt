package com.krbavcic.logosphere.core.logic

import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.Exchange

/**
 * One side of an exchange: a person, or a group (alliance, project, sphere) that a person acted
 * for. [isViewer] is true only when the side is the viewer themself, which screens show as "You".
 */
data class Party(
    val id: String?,
    val name: String,
    /** null for a person; otherwise which kind of group. */
    val group: CommunityKind?,
    val actingUserId: String?,
    val actingUserName: String?,
    val isViewer: Boolean,
    /** The person (or the human acting for the group) is an AI persona. */
    val isAgent: Boolean = false,
) {
    val label: String get() = if (isViewer) "You" else name

    /** The AI persona label goes next to this side's own name only for a person, never "You". */
    val personaByName: Boolean get() = isAgent && group == null && !isViewer

    /** A group is never labelled itself: the label goes next to the persona acting for it. */
    val personaActsForGroup: Boolean get() = isAgent && group != null && actingUserName != null
}

object Parties {
    fun initiator(exchange: Exchange, viewerId: String?): Party {
        val id = exchange.initiatorId ?: exchange.userId
        val group = CommunityKind.of(exchange.initiatorKind)
        return Party(
            id = id,
            name = exchange.initiatorName ?: "Initiator",
            group = group,
            actingUserId = exchange.initiatorActingUserId,
            actingUserName = exchange.initiatorActingUserName,
            isViewer = group == null && id != null && id == viewerId,
            isAgent = exchange.initiatorIsAgent,
        )
    }

    fun recipient(exchange: Exchange, viewerId: String?): Party? {
        val id = exchange.otherUserId ?: return null
        val group = CommunityKind.of(exchange.otherKind)
        return Party(
            id = id,
            name = exchange.otherUserName ?: "Recipient",
            group = group,
            actingUserId = exchange.recipientActingUserId,
            actingUserName = exchange.recipientActingUserName,
            isViewer = group == null && id == viewerId,
            isAgent = exchange.otherIsAgent,
        )
    }
}
