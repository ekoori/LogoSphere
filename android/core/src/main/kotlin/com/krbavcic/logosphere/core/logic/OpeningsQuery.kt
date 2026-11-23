package com.krbavcic.logosphere.core.logic

/**
 * What the Openings tab asks the server for, a page at a time (the server's app/utils/openings_feed.py,
 * and the site's utils/openingsQuery.js). [type]: 0 all, 1 offers, 2 needs, 3 loans. [sphere]: one sphere's id,
 * [REAL] or [DEMO]. [near]: within that many km of the member's place.
 */
data class OpeningsQuery(val type: Int = 0, val sphere: String? = null, val near: Int? = null) {
    fun params(): Map<String, String> = buildMap {
        put("limit", PAGE.toString())
        when (type) {
            1 -> put("type", "offer")
            2 -> put("type", "need")
            3 -> put("loans", "1")
        }
        when (sphere) {
            null -> Unit
            REAL -> put("demo", "real")
            DEMO -> put("demo", "demo")
            else -> put("sphere", sphere)
        }
        near?.let { put("km", it.toString()) }
    }

    companion object {
        const val PAGE = 30
        const val REAL = "real-spheres"
        const val DEMO = "demo-spheres"
    }
}
