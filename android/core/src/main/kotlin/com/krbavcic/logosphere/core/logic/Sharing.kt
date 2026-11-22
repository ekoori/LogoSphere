package com.krbavcic.logosphere.core.logic

import com.krbavcic.logosphere.core.model.Community
import com.krbavcic.logosphere.core.model.Exchange
import com.krbavcic.logosphere.core.model.GroupSummary
import com.krbavcic.logosphere.core.model.Opening

/** An opening in more spheres than its own, and loans: the site's utils/sharing.js. */
object Sharing {
    fun loanLabel(isOffer: Boolean): String = if (isOffer) "To lend" else "To borrow"

    fun loanQuestion(isOffer: Boolean): String = if (isOffer) "It's a loan: I'd like it back" else "I only need to borrow it"

    /** Its own sphere, or one it was shared with. */
    fun isIn(opening: Opening, sphereId: String?): Boolean =
        sphereId != null && (opening.sphereId == sphereId || opening.sharedWith.any { it.id == sphereId })

    /**
     * The spheres to offer: those the viewer is in, on the same side of demo and real as the
     * opening's own, and whatever it's shared with [already] (so that can be taken back).
     */
    fun choices(
        spheres: List<Community>,
        homeId: String?,
        isDemo: Boolean,
        viewerId: String?,
        already: List<GroupSummary> = emptyList(),
        mayAdd: Boolean = true,
    ): List<GroupSummary> {
        if (homeId == null) return emptyList()
        val added = if (!mayAdd) emptyList() else spheres
            .filter { it.id != homeId && it.isDemo == isDemo && Membership.isMember(it, viewerId) }
            .map { GroupSummary(id = it.id, name = it.name) }
        return (already + added).distinctBy { it.id }.sortedBy { it.name.lowercase() }
    }

    /** What an exchange that is a loan says. */
    fun loanNote(exchange: Exchange): String? = when {
        !exchange.borrow -> null
        exchange.status == null || exchange.status in listOf("Initiated", "In Progress") ->
            "A loan. Mark the exchange finished when it's back."
        else -> "This was a loan."
    }
}
