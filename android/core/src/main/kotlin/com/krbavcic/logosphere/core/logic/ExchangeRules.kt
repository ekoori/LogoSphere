package com.krbavcic.logosphere.core.logic

import com.krbavcic.logosphere.core.model.Exchange
import com.krbavcic.logosphere.core.model.ExchangeDetail

/**
 * What a viewer may do with an exchange, following backend/app/routes/meaning_trail.py.
 *
 * Status moves only Initiated → In Progress → Finished by hand; Receipted is reached by adding the
 * receipt, and a follow-up note marks the last step. Cancelling is the initiator's, and only while
 * the exchange is still Initiated or In Progress (`_TRANSITIONS`).
 */
object ExchangeRules {
    const val INITIATED = "Initiated"
    const val IN_PROGRESS = "In Progress"
    const val FINISHED = "Finished"
    const val RECEIPTED = "Receipted"
    const val FOLLOW_UP = "Additional Comments Added"
    const val CANCELLED = "Cancelled"

    private val STEPS = listOf(INITIATED, IN_PROGRESS, FINISHED, RECEIPTED)
    private const val FOLLOW_UP_STEP = "Follow-up added"

    fun status(exchange: Exchange): String = exchange.status ?: INITIATED

    fun isCancelled(exchange: Exchange): Boolean = status(exchange) == CANCELLED

    /** Settled: past the work itself (finished, receipted, or followed up; "Completed" is legacy). */
    fun isCompleted(exchange: Exchange): Boolean =
        status(exchange) in setOf(FINISHED, RECEIPTED, FOLLOW_UP, "Completed")

    /** The status a participant can move it to next by hand, if any. */
    fun nextStatus(exchange: Exchange): String? = when (status(exchange)) {
        INITIATED -> IN_PROGRESS
        IN_PROGRESS -> FINISHED
        else -> null
    }

    private fun isParticipant(detail: ExchangeDetail) = detail.isInitiator || detail.isOther

    fun canAdvance(detail: ExchangeDetail): Boolean = isParticipant(detail) && nextStatus(detail.exchange) != null

    /** Title, description and banner: either side, until it's finished (and, as on the web, not once cancelled). */
    fun canEdit(detail: ExchangeDetail): Boolean =
        isParticipant(detail) && !detail.exchange.isFinished && !isCancelled(detail.exchange)

    fun canCancel(detail: ExchangeDetail): Boolean =
        detail.isInitiator && status(detail.exchange) in setOf(INITIATED, IN_PROGRESS)

    /** The receipt is the recipient's, one per exchange. */
    fun canAddReceipt(detail: ExchangeDetail): Boolean =
        detail.isOther && detail.exchange.receipt == null && !isCancelled(detail.exchange)

    /** The personal note is the initiator's, one per exchange. */
    fun canAddNote(detail: ExchangeDetail): Boolean =
        detail.isInitiator && detail.exchange.initiatorNote == null && !isCancelled(detail.exchange)

    fun bothSidesWritten(exchange: Exchange): Boolean = exchange.receipt != null && exchange.initiatorNote != null

    /** Once both sides have written, each participant may add one lighter follow-up. */
    fun canAddFollowUp(detail: ExchangeDetail): Boolean {
        val x = detail.exchange
        return bothSidesWritten(x) &&
            ((detail.isInitiator && x.initiatorFollowUp == null) || (detail.isOther && x.recipientFollowUp == null))
    }

    /** The single public acknowledgement is first come, open to anyone signed in. */
    fun canAcknowledge(detail: ExchangeDetail): Boolean = detail.canAcknowledge

    fun hasFollowUp(exchange: Exchange): Boolean =
        exchange.initiatorFollowUp != null || exchange.recipientFollowUp != null || status(exchange) == FOLLOW_UP

    fun progress(exchange: Exchange): Progress {
        val cancelled = isCancelled(exchange)
        val followUp = hasFollowUp(exchange)
        val steps = buildList {
            add(Step(INITIATED, exchange.startedAt))
            add(Step(IN_PROGRESS, exchange.inProgressAt))
            add(Step(FINISHED, exchange.finishedAt))
            add(Step(RECEIPTED, exchange.receiptedAt))
            if (followUp) add(Step(FOLLOW_UP_STEP, exchange.initiatorFollowUpAt ?: exchange.recipientFollowUpAt))
        }
        val current = when {
            cancelled -> 0
            followUp -> steps.lastIndex
            else -> STEPS.indexOf(status(exchange)).coerceAtLeast(0)
        }
        return Progress(steps, current, cancelled)
    }
}
