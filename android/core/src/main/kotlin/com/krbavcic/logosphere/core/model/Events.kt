package com.krbavcic.logosphere.core.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// Events, a group's announcements and invitation links
// (backend/app/utils/events.py, announcements.py and invites.py).

/** A sphere, alliance or project, by name: an event's host, or what an invitation is to. */
@Serializable
data class GroupSummary(val id: String, val kind: String = "sphere", val name: String = "") {
    val communityKind: CommunityKind get() = CommunityKind.of(kind) ?: CommunityKind.Sphere
}

@Serializable
data class EventPerson(val id: String, val name: String = "", val answer: String = "")

/** One date of an event. [day] is its local date; the times are UTC. */
@Serializable
data class EventTime(
    val day: String,
    @SerialName("starts_at") val startsAt: String = "",
    @SerialName("ends_at") val endsAt: String = "",
    val skipped: Boolean = false,
    val going: Int = 0,
    val maybe: Int = 0,
    @SerialName("my_answer") val myAnswer: String? = null,
    /** Who is coming: in an event's own page only. */
    val people: List<EventPerson> = emptyList(),
)

@Serializable
data class CommunityEvent(
    val id: String,
    val title: String = "",
    val description: String = "",
    /** Null: it's for everyone signed in. */
    val host: GroupSummary? = null,
    /** The wall-clock start, in [tz]. */
    val starts: String = "",
    val tz: String = "UTC",
    @SerialName("length_min") val lengthMin: Int = 60,
    val repeats: String = "never",
    val until: String? = null,
    val cancelled: Boolean = false,
    @SerialName("has_image") val hasImage: Boolean = false,
    @SerialName("image_is_ai") val imageIsAi: Boolean = false,
    @SerialName("is_demo") val isDemo: Boolean = false,
    val location: String? = null,
    val distance: Distance? = null,
    @SerialName("can_manage") val canManage: Boolean = false,
    /** In a list: its next date. */
    val upcoming: EventTime? = null,
    // The rest are in its own page only.
    val creator: PersonRef? = null,
    val point: GeoPoint? = null,
    val over: Boolean = false,
    val times: List<EventTime> = emptyList(),
)

@Serializable
data class EventsPage(val events: List<CommunityEvent> = emptyList())

@Serializable
data class Announcement(
    val id: String,
    val text: String = "",
    val at: String = "",
    val author: PersonRef? = null,
    @SerialName("can_remove") val canRemove: Boolean = false,
)

@Serializable
data class Announcements(
    @SerialName("can_announce") val canAnnounce: Boolean = false,
    val announcements: List<Announcement> = emptyList(),
)

/** One of the member's own links, which never includes its code. */
@Serializable
data class Invite(
    val id: String,
    val group: GroupSummary? = null,
    @SerialName("expires_at") val expiresAt: String = "",
    val joined: Int = 0,
    val works: Boolean = true,
)

/** A link just made. [path] carries its code, and is shown only now. */
@Serializable
data class NewInvite(
    val id: String,
    val path: String,
    @SerialName("expires_at") val expiresAt: String = "",
    @SerialName("most_uses") val mostUses: Int = 25,
    val group: GroupSummary? = null,
)
