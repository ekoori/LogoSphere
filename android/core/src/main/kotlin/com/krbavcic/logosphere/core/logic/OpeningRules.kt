package com.krbavcic.logosphere.core.logic

import com.krbavcic.logosphere.core.model.Community
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.Opening

/**
 * What a viewer may do with an opening. These follow the server's guards in
 * backend/app/routes/openings.py, so the app never offers an action the server will refuse.
 */
object OpeningRules {
    private val SINGLE_STEPS = listOf("Posted", "Accepted", "In Progress", "Completed")
    private val PERPETUAL_STEPS = listOf("Posted", "Accepted (multiple)", "In Progress (multiple)", "Completed (multiple)")

    /** Posted by the viewer — or for an entity they act for. */
    fun isOwn(opening: Opening, viewerId: String?): Boolean =
        opening.isProvider || (viewerId != null && opening.providerId == viewerId)

    /** May confirm or decline acceptances and withdraw it (its party, or a platform admin). */
    fun mayManage(opening: Opening, viewerId: String?): Boolean = opening.canManage || isOwn(opening, viewerId)

    /** Closed to acceptances: finished, withdrawn, or a one-time opening already in an exchange. */
    fun isClosed(opening: Opening): Boolean =
        opening.status == "Completed" || opening.status == "Cancelled" ||
            (!opening.isPerpetual && opening.status == "In Progress")

    /** `accept_service`: not your own, not yet accepted by you, and still open. */
    fun canAccept(opening: Opening, viewerId: String?): Boolean =
        viewerId != null && opening.isCurrent && !isOwn(opening, viewerId) &&
            opening.myAcceptance == null && !isClosed(opening)

    /** `reject_service` from the accepting side: your acceptance, while it still awaits confirmation. */
    fun canTakeBack(opening: Opening): Boolean =
        opening.myAcceptance?.status == "pending" && opening.status != "Cancelled"

    /** `cancel_service`: a current opening that hasn't been taken into an exchange yet. */
    fun canWithdraw(opening: Opening, viewerId: String?): Boolean =
        mayManage(opening, viewerId) && opening.isCurrent && !isClosed(opening)

    /** Alliances and projects the viewer manages that may accept this opening on their behalf. */
    fun acceptAsOptions(opening: Opening, managed: List<Community>): List<Community> =
        managed.filter {
            it.kind != CommunityKind.Sphere && it.id != opening.providerId &&
                (opening.sphereId == null || Sharing.isIn(opening, it.parentSphereId))
        }

    /**
     * Posted → Accepted → In Progress → Completed, each with the date it was reached. A perpetual
     * opening gathers many acceptances, so its middle phases show the latest activity.
     */
    fun progress(opening: Opening): Progress {
        val cancelled = opening.status == "Cancelled"
        val activity = opening.activity
        val current = when {
            cancelled -> 1
            opening.isPerpetual -> when {
                activity?.completedLastAt != null -> 3
                (activity?.inProgressCount ?: 0) > 0 -> 2
                (activity?.acceptedCount ?: 0) > 0 -> 1
                else -> 0
            }
            else -> SINGLE_STEPS.indexOfFirst { it.equals(opening.status, ignoreCase = true) }.coerceAtLeast(0)
        }
        val dates = if (opening.isPerpetual) {
            listOf(opening.createdAt, activity?.acceptedLastAt, activity?.inProgressLastAt, activity?.completedLastAt)
        } else {
            listOf(opening.createdAt, opening.acceptedAt, opening.inProgressAt, opening.completedAt)
        }
        val labels = if (opening.isPerpetual) PERPETUAL_STEPS else SINGLE_STEPS
        val steps = labels.mapIndexed { i, label -> Step(label, if (i <= current) dates[i] else null) }
        return Progress(steps, current, cancelled)
    }
}
