package com.krbavcic.logosphere.core.logic

import com.krbavcic.logosphere.core.model.CommunityKind
import java.net.URLDecoder

/** The site's information pages, which the app shows too. */
enum class InfoPage(val path: String, val title: String) {
    About("/about", "About LogoSphere"),
    HowItWorks("/how-it-works", "How it works"),
    Contribute("/contribute", "Contribute"),
    Privacy("/privacy", "Privacy policy"),
    Terms("/tos", "Terms of service"),
    ChildSafety("/child-safety", "Child safety standards");

    companion object {
        fun of(path: String): InfoPage? = entries.firstOrNull { it.path == path }
    }
}

/** Where a server link (from a notification or a search result) leads inside the app. */
sealed interface AppLink {
    data class Opening(val id: String) : AppLink
    data class Exchange(val id: String) : AppLink

    /** [tab] names a tab to open on (`governance` from a proposal's notification). */
    data class Community(val kind: CommunityKind, val id: String, val tab: String? = null) : AppLink
    data class Manage(val kind: CommunityKind, val id: String) : AppLink
    data class Person(val id: String, val tab: String? = null) : AppLink

    /** [owner]: opened on that person's or group's cards. */
    data class MeaningGraph(val owner: String? = null, val card: String? = null) : AppLink
    data object Me : AppLink
    data object EditProfile : AppLink
    data object Account : AppLink
    data object Nearby : AppLink
    data object Events : AppLink
    data class Event(val id: String) : AppLink

    /** [with]: that conversation, about [opening] if given. */
    data class Messages(val with: String? = null, val opening: String? = null, val about: String? = null) : AppLink
    data object Admin : AppLink
    data class Info(val page: InfoPage) : AppLink

    /** No screen for it on the phone: open the web page. */
    data class Web(val path: String) : AppLink
}

/**
 * Maps the web app's routes (`/opening?id=…`, `/exchange?id=…`, `/sphere?id=…`, `/user?id=…`,
 * management, settings, admin and the information pages) to app screens. A link the app has no
 * screen for — or one that names an entity only by `?name=` — opens on the web instead.
 */
object Links {
    fun parse(link: String?): AppLink? {
        val text = link?.trim().orEmpty()
        if (text.isEmpty()) return null
        val path = text.substringBefore('?').substringBefore('#').trimEnd('/').ifEmpty { "/" }
        val query = text.substringAfter('?', "").substringBefore('#')
        val params = query.split('&')
            .map { it.split('=', limit = 2) }
            .filter { it.size == 2 }
            .associate { it[0] to URLDecoder.decode(it[1], "UTF-8") }
        val id = params["id"]?.takeIf { it.isNotBlank() }
        val tab = params["tab"]?.takeIf { it.isNotBlank() }
        val kind = CommunityKind.of(path.removePrefix("/").removeSuffix("-management"))
        return when {
            path == "/profile" -> AppLink.Me
            // Where the email in an unsubscribe or notification message sends you.
            path == "/settings" && (text.endsWith("#email") || text.endsWith("#invitations")) -> AppLink.Account
            path == "/settings" -> AppLink.EditProfile
            path == "/nearby" -> AppLink.Nearby
            path == "/events" -> AppLink.Events
            path == "/event" -> id?.let { AppLink.Event(it) }
            path == "/messages" -> AppLink.Messages(
                with = params["with"]?.takeIf { it.isNotBlank() },
                opening = params["opening"]?.takeIf { it.isNotBlank() },
                about = params["about"]?.takeIf { it.contains(':') },
            )
            path == "/admin" -> AppLink.Admin
            path == "/meaning-graph" -> AppLink.MeaningGraph(
                params["owner"]?.takeIf { it.isNotBlank() },
                params["card"]?.takeIf { it.isNotBlank() },
            )
            path == "/opening" -> id?.let { AppLink.Opening(it) }
            path == "/exchange" -> id?.let { AppLink.Exchange(it) }
            path == "/user" -> id?.let { AppLink.Person(it, tab) }
            kind != null && path.endsWith("-management") -> id?.let { AppLink.Manage(kind, it) }
            kind != null -> id?.let { AppLink.Community(kind, it, tab) }
            else -> InfoPage.of(path)?.let { AppLink.Info(it) }
        } ?: AppLink.Web(text)
    }
}
