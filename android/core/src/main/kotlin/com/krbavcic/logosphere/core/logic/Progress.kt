package com.krbavcic.logosphere.core.logic

/** One phase of a lifecycle, with the timestamp it was reached (null until then). */
data class Step(val label: String, val reachedAt: String?)

/**
 * A lifecycle drawn as steps. [current] is the index of the phase reached; a cancelled lifecycle
 * keeps the phase it stopped at and is drawn as cancelled.
 */
data class Progress(val steps: List<Step>, val current: Int, val cancelled: Boolean) {
    val currentLabel: String get() = if (cancelled) "Cancelled" else steps.getOrNull(current)?.label.orEmpty()
}
