package com.krbavcic.logosphere.core.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// Private messages, always between two people; blocking and reporting
// (backend/app/utils/messaging.py and safety.py).

@Serializable
data class MessageAbout(val id: String, val title: String = "")

@Serializable
data class DirectMessage(
    val id: String,
    val text: String = "",
    val at: String = "",
    val mine: Boolean = false,
    /** The opening it was written about. */
    val opening: MessageAbout? = null,
)

@Serializable
data class Correspondent(
    val id: String,
    val name: String = "",
    @SerialName("is_agent") val isAgent: Boolean = false,
)

@Serializable
data class LastMessage(val text: String = "", val at: String = "", val mine: Boolean = false)

@Serializable
data class ConversationSummary(
    val person: Correspondent,
    val last: LastMessage = LastMessage(),
    val unread: Boolean = false,
)

@Serializable
data class Conversations(
    val conversations: List<ConversationSummary> = emptyList(),
    @SerialName("unread_count") val unreadCount: Int = 0,
)

/** `GET /api/messages/<person>`: a page, oldest first, and whether the viewer may write. */
@Serializable
data class Conversation(
    val person: Correspondent,
    val messages: List<DirectMessage> = emptyList(),
    val more: Boolean = false,
    val about: MessageAbout? = null,
    @SerialName("can_send") val canSend: Boolean = false,
    @SerialName("why_not") val whyNot: String? = null,
    /** The viewer blocked them. */
    val blocked: Boolean = false,
)

@Serializable
data class SentMessage(val sent: DirectMessage)

/** `POST /api/openings/<id>/message_respondents`. */
@Serializable
data class RespondentsResult(val sent: Int = 0, val skipped: Int = 0)

@Serializable
data class BlockedPerson(val id: String, val name: String = "")

/** What is being reported. The server reads its words itself. */
data class ReportOf(
    val kind: String,
    val id: String,
    /** A message: who the conversation is with. */
    val personId: String? = null,
    /** An acknowledgement: whose trail it's on. */
    val trailId: String? = null,
    /** An announcement: whose group's. */
    val groupId: String? = null,
) {
    /** A person needs a word on what happened. */
    val needsNote: Boolean get() = kind == PERSON

    companion object {
        private const val PERSON = "person"

        fun person(id: String) = ReportOf(PERSON, id)

        fun message(id: String, with: String) = ReportOf("message", id, personId = with)

        fun opening(id: String) = ReportOf("opening", id)

        fun acknowledgement(id: String, trailId: String) = ReportOf("acknowledgement", id, trailId = trailId)

        fun event(id: String) = ReportOf("event", id)

        fun announcement(id: String, groupId: String) = ReportOf("announcement", id, groupId = groupId)
    }
}

@Serializable
data class Report(
    val id: String,
    val kind: String = "",
    @SerialName("item_id") val itemId: String? = null,
    val reporter: PersonRef? = null,
    val subject: PersonRef? = null,
    val excerpt: String = "",
    val note: String = "",
    val status: String = "open",
    @SerialName("made_at") val madeAt: String? = null,
    @SerialName("handled_by") val handledBy: PersonRef? = null,
    val outcome: String = "",
    val removable: Boolean = false,
) {
    val what: String
        get() = when (kind) {
            "person" -> "A person"
            "message" -> "A private message"
            "acknowledgement" -> "An acknowledgement"
            "opening" -> "An opening"
            "event" -> "An event"
            "announcement" -> "An announcement"
            else -> kind
        }
}

@Serializable
data class Reports(val open: Int = 0, val reports: List<Report> = emptyList())
