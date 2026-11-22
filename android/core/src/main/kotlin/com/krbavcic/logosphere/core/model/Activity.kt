package com.krbavcic.logosphere.core.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// What the people you follow did lately, and whom you both know (backend/app/utils/activity.py).

/** One thing someone did: "[who] [says] [title]", opening [link] when tapped. */
@Serializable
data class ActivityItem(
    val kind: String = "",
    val at: String? = null,
    val who: Correspondent,
    val says: String = "",
    val title: String = "",
    /** An acknowledgement's words. */
    val text: String? = null,
    val link: String = "",
    @SerialName("is_demo") val isDemo: Boolean = false,
)

@Serializable
data class ActivityPage(val activity: List<ActivityItem> = emptyList())

@Serializable
data class KnownPeople(val people: List<Correspondent> = emptyList())
