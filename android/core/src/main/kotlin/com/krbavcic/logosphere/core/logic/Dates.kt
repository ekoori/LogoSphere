package com.krbavcic.logosphere.core.logic

import java.time.Duration
import java.time.Instant
import java.time.LocalDateTime
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.ZoneOffset
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import java.time.format.FormatStyle
import java.util.Locale

/**
 * The API sends timestamps two ways: model `to_dict()`s use ISO-8601 without a zone
 * ("2026-06-02T10:00:00", "2026-07-05T04:55:02.777000"), which are UTC, while raw datetimes that
 * Flask serialises itself arrive as RFC 1123 ("Tue, 02 Jun 2026 10:00:00 GMT").
 */
object Dates {
    fun parse(value: String?): Instant? {
        val text = value?.trim().orEmpty()
        if (text.isEmpty()) return null
        return runCatching { LocalDateTime.parse(text).toInstant(ZoneOffset.UTC) }.getOrNull()
            ?: runCatching { OffsetDateTime.parse(text).toInstant() }.getOrNull()
            ?: runCatching { ZonedDateTime.parse(text, DateTimeFormatter.RFC_1123_DATE_TIME).toInstant() }.getOrNull()
    }

    /** "Jun 2, 2026" in the reader's locale; empty when there is no date. */
    fun day(value: String?, zone: ZoneId = ZoneId.systemDefault(), locale: Locale = Locale.getDefault()): String =
        parse(value)?.let { DateTimeFormatter.ofLocalizedDate(FormatStyle.MEDIUM).withLocale(locale).format(it.atZone(zone)) }
            .orEmpty()

    /** "just now", "5m ago", "3h ago", "2d ago", then the date. */
    fun ago(
        value: String?,
        now: Instant = Instant.now(),
        zone: ZoneId = ZoneId.systemDefault(),
        locale: Locale = Locale.getDefault(),
    ): String {
        val then = parse(value) ?: return ""
        val minutes = Duration.between(then, now).toMinutes()
        return when {
            minutes < 1 -> "just now"
            minutes < 60 -> "${minutes}m ago"
            minutes < 24 * 60 -> "${minutes / 60}h ago"
            minutes < 7 * 24 * 60 -> "${minutes / (24 * 60)}d ago"
            else -> day(value, zone, locale)
        }
    }
}
