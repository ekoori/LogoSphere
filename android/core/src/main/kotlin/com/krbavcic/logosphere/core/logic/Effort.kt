package com.krbavcic.logosphere.core.logic

import kotlin.math.roundToInt

/** How long help took, as a receipt says it (the server's routes/meaning_trail.py, effort_hours). */
object Effort {
    const val MIN = 0.25
    const val MAX = 100.0

    /** What was typed, to the nearest quarter hour; null when it isn't a number in range. */
    fun parse(typed: String): Double? {
        val hours = typed.trim().replace(',', '.').toDoubleOrNull() ?: return null
        if (hours.isNaN() || hours < MIN || hours > MAX) return null
        return (hours * 4).roundToInt() / 4.0
    }

    /** "About 2 hours", "About 45 minutes"; short: "2 h", "45 min". Null for none. */
    fun text(hours: Double?, short: Boolean = false): String? {
        val h = hours?.takeIf { it > 0 } ?: return null
        val number = if (h == h.toLong().toDouble()) h.toLong().toString() else h.toString()
        return when {
            short && h < 1 -> "${(h * 60).roundToInt()} min"
            short -> "$number h"
            h < 1 -> "About ${(h * 60).roundToInt()} minutes"
            else -> "About $number hour" + if (h == 1.0) "" else "s"
        }
    }
}
