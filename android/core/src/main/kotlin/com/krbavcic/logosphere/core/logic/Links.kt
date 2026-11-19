package com.krbavcic.logosphere.core.logic

import com.krbavcic.logosphere.core.model.CommunityKind
import java.net.URLDecoder

/** Where a server link (from a notification or a search result) leads inside the app. */
sealed interface AppLink {
    data class Opening(val id: String) : AppLink
    data class Exchange(val id: String) : AppLink
    data class Community(val kind: CommunityKind, val id: String) : AppLink
    data class Person(val id: String) : AppLink
    data object Me : AppLink

    /** No screen for it on the phone: open the web page. */
    data class Web(val path: String) : AppLink
}

/**
 * Maps the web app's routes (`/opening?id=…`, `/exchange?id=…`, `/sphere?id=…`, `/user?id=…`) to
 * app screens. A link the app has no screen for — or one that names an entity only by `?name=` —
 * opens on the web instead.
 */
object Links {
    fun parse(link: String?): AppLink? {
        val text = link?.trim().orEmpty()
        if (text.isEmpty()) return null
        val path = text.substringBefore('?').substringBefore('#').trimEnd('/').ifEmpty { "/" }
        val query = text.substringAfter('?', "").substringBefore('#')
        val id = query.split('&')
            .map { it.split('=', limit = 2) }
            .firstOrNull { it.size == 2 && it[0] == "id" }
            ?.let { URLDecoder.decode(it[1], "UTF-8") }
            ?.takeIf { it.isNotBlank() }
        return when (path) {
            "/profile" -> AppLink.Me
            "/opening" -> id?.let { AppLink.Opening(it) }
            "/exchange" -> id?.let { AppLink.Exchange(it) }
            "/user" -> id?.let { AppLink.Person(it) }
            "/sphere" -> id?.let { AppLink.Community(CommunityKind.Sphere, it) }
            "/alliance" -> id?.let { AppLink.Community(CommunityKind.Alliance, it) }
            "/project" -> id?.let { AppLink.Community(CommunityKind.Project, it) }
            else -> null
        } ?: AppLink.Web(text)
    }
}
