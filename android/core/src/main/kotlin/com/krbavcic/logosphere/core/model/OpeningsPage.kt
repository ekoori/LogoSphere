package com.krbavcic.logosphere.core.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** `GET /api/openings?limit=…`: a page, and where to carry on from (null at the end). */
@Serializable
data class OpeningsPage(
    val openings: List<Opening> = emptyList(),
    val next: String? = null,
    /** Asked for what's near, without a place of one's own to measure from. */
    @SerialName("no_place") val noPlace: Boolean = false,
)
