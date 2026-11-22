package com.krbavcic.logosphere.core.logic

/** The tab a screen opens on: Openings, though Trail comes first; a link's `?tab=` wins. */
object Tabs {
    const val TRAIL = "trail"
    const val OPENINGS = "openings"

    private val webNames = mapOf("meaning_trail" to TRAIL, "offers-needs" to OPENINGS, "members" to "people")

    /** The position in [tabs] of [name] (the app's name or the site's), else of Openings. */
    fun indexOf(name: String?, tabs: List<String>): Int {
        val key = webNames[name] ?: name
        val index = tabs.indexOf(key)
        return if (index >= 0) index else tabs.indexOf(OPENINGS).coerceAtLeast(0)
    }
}
