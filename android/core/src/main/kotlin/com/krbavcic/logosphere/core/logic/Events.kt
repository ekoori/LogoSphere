package com.krbavcic.logosphere.core.logic

import com.krbavcic.logosphere.core.model.CommunityEvent
import com.krbavcic.logosphere.core.model.EventTime
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import java.time.Instant
import java.time.LocalDate
import java.time.LocalTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.time.format.FormatStyle
import java.time.format.TextStyle
import java.util.Locale

enum class EventAnswer(val key: String, val label: String) {
    Going("going", "Going"),
    Maybe("maybe", "Maybe"),
    Cant("no", "Can't");

    companion object {
        fun of(key: String?): EventAnswer? = entries.firstOrNull { it.key == key }
    }
}

enum class Repeats(val key: String) {
    Never("never"),
    Weekly("weekly"),
    Fortnightly("fortnightly"),
    Monthly("monthly"),
    MonthlyWeekday("monthly_weekday");

    companion object {
        fun of(key: String?): Repeats = entries.firstOrNull { it.key == key } ?: Never
    }
}

/**
 * An event's times in words, as the site's utils/events.js has them. They are shown on the
 * event's own clock: that is the one on the hall's wall.
 */
object Events {
    private val LENGTHS = listOf(30, 60, 90, 120, 150, 180, 240, 300, 360, 480, 720, 1440, 2880, 4320, 10080)
    private val NTH = listOf("first", "second", "third", "fourth", "last")

    /** The phone's zone by its name, or UTC when it has none the server would know. */
    fun deviceZone(zone: ZoneId = ZoneId.systemDefault()): String =
        zone.id.takeIf { it in ZoneId.getAvailableZoneIds() } ?: "UTC"

    fun zone(name: String?): ZoneId? = name?.let { runCatching { ZoneId.of(it) }.getOrNull() }

    fun date(text: String?): LocalDate? = text?.let { runCatching { LocalDate.parse(it.take(10)) }.getOrNull() }

    fun clock(text: String?): LocalTime? = text?.let { runCatching { LocalTime.parse(it) }.getOrNull() }

    fun ordinal(n: Int): String = when {
        n % 100 in 11..13 -> "${n}th"
        n % 10 == 1 -> "${n}st"
        n % 10 == 2 -> "${n}nd"
        n % 10 == 3 -> "${n}rd"
        else -> "${n}th"
    }

    /** What "repeats" means for an event that first happens on [first]. */
    fun repeatText(repeats: Repeats, first: LocalDate?): String {
        if (repeats == Repeats.Never) return "Doesn't repeat"
        if (first == null) {
            return when (repeats) {
                Repeats.Weekly -> "Every week"
                Repeats.Fortnightly -> "Every two weeks"
                Repeats.Monthly -> "Every month, same date"
                else -> "Every month, same day of the week"
            }
        }
        val weekday = first.dayOfWeek.getDisplayName(TextStyle.FULL, Locale.ENGLISH)
        return when (repeats) {
            Repeats.Weekly -> "Every $weekday"
            Repeats.Fortnightly -> "Every second $weekday, fortnightly"
            Repeats.Monthly ->
                "Every month on the ${ordinal(first.dayOfMonth)}" + if (first.dayOfMonth > 28) ", or the month's last day" else ""
            else -> "Every month on the ${NTH[(first.dayOfMonth - 1) / 7]} $weekday"
        }
    }

    fun lengthText(minutes: Int): String {
        if (minutes % 1440 == 0) return if (minutes == 1440) "1 day" else "${minutes / 1440} days"
        val hours = minutes / 60
        val over = minutes % 60
        return when {
            hours == 0 -> "$minutes minutes"
            over == 30 -> "$hours½ hours"
            else -> "$hours ${if (hours == 1) "hour" else "hours"}" + if (over > 0) " $over minutes" else ""
        }
    }

    /** The usual lengths, and [current] when it's another. */
    fun lengthChoices(current: Int): List<Int> = (LENGTHS + current).distinct().sorted()

    /** "19:00" or "7:00 pm", as the reader's language writes it. */
    fun clockText(time: LocalTime, locale: Locale = Locale.getDefault()): String =
        DateTimeFormatter.ofLocalizedTime(FormatStyle.SHORT).withLocale(locale).format(time)

    fun dateText(day: LocalDate, locale: Locale = Locale.getDefault()): String =
        DateTimeFormatter.ofPattern("EEE d MMM yyyy", locale).format(day)

    /** [zoneNote] names the event's clock when the reader's shows something else. */
    data class When(val text: String, val zoneNote: String?)

    fun whenText(
        time: EventTime,
        tz: String,
        viewer: ZoneId = ZoneId.systemDefault(),
        now: Instant = Instant.now(),
        locale: Locale = Locale.getDefault(),
    ): When {
        val starts = Dates.parse(time.startsAt) ?: return When("", null)
        val there = zone(tz) ?: viewer
        val start = starts.atZone(there)
        val end = Dates.parse(time.endsAt)?.atZone(there)
        val pattern = if (start.year == now.atZone(viewer).year) "EEE d MMM" else "EEE d MMM yyyy"
        val days = DateTimeFormatter.ofPattern(pattern, locale)
        fun clock(at: LocalTime) = clockText(at, locale)
        var text = "${days.format(start)}, ${clock(start.toLocalTime())}"
        if (end != null) {
            text += if (end.toLocalDate() == start.toLocalDate()) "–${clock(end.toLocalTime())}"
            else " – ${days.format(end)}, ${clock(end.toLocalTime())}"
        }
        val differs = start.toLocalDateTime() != starts.atZone(viewer).toLocalDateTime()
        return When(text, if (differs) "${there.id.replace('_', ' ')} time" else null)
    }

    fun hasEnded(time: EventTime, now: Instant = Instant.now()): Boolean =
        Dates.parse(time.endsAt)?.let { !it.isAfter(now) } ?: false

    fun comingText(time: EventTime): String = listOfNotNull(
        "${time.going} going".takeIf { time.going > 0 },
        "${time.maybe} maybe".takeIf { time.maybe > 0 },
    ).joinToString(" · ")
}

/** An event as its form holds it: kept through rotation and a trip to the camera. */
@Serializable
data class EventDraft(
    val title: String = "",
    val description: String = "",
    /** ISO date. */
    val day: String? = null,
    /** "HH:MM", on [tz]'s clock. */
    val clock: String? = null,
    val lengthMin: Int = 120,
    val repeats: String = Repeats.Never.key,
    val until: String? = null,
    val tz: String = "UTC",
) {
    val problem: String?
        get() {
            val first = Events.date(day)
            val last = if (repeats == Repeats.Never.key) null else Events.date(until)
            return when {
                title.isBlank() -> "Give it a name."
                first == null || Events.clock(clock) == null -> "Say which day and time it starts."
                last != null && last.isBefore(first) -> "Its last date is before its first."
                else -> null
            }
        }

    /** [hostId]: the group putting it on, when making one. */
    fun body(hostId: String? = null): JsonObject = buildJsonObject {
        put("title", title.trim())
        put("description", description.trim())
        put("starts", "${day}T$clock")
        put("tz", tz)
        put("length_min", lengthMin)
        put("repeats", repeats)
        put("until", if (repeats == Repeats.Never.key) null else until)
        if (hostId != null) put("host_id", hostId)
    }

    companion object {
        fun of(event: CommunityEvent) = EventDraft(
            title = event.title,
            description = event.description,
            day = event.starts.substringBefore('T').takeIf { Events.date(it) != null },
            clock = event.starts.substringAfter('T', "").take(5).takeIf { Events.clock(it) != null },
            lengthMin = event.lengthMin,
            repeats = event.repeats,
            until = event.until,
            tz = event.tz,
        )
    }
}
