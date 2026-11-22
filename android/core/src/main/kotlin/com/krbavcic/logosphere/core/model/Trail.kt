package com.krbavcic.logosphere.core.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** A few public words on a Meaning Trail, with the value cards they express. */
@Serializable
data class Acknowledgement(
    @SerialName("ack_id") val id: String,
    /** The person, group or exchange whose trail it is on. */
    @SerialName("trail_id") val trailId: String = "",
    @SerialName("author_id") val authorId: String? = null,
    @SerialName("author_name") val authorName: String? = null,
    @SerialName("author_is_agent") val authorIsAgent: Boolean = false,
    val text: String = "",
    val cards: List<ValueCard> = emptyList(),
    @SerialName("created_at") val createdAt: String? = null,
    val highlighted: Boolean = false,
    /** It stays visible while its run is folded. */
    val shown: Boolean = true,
    val likes: LikeInfo = LikeInfo(),
    @SerialName("can_highlight") val canHighlight: Boolean = false,
    @SerialName("can_remove") val canRemove: Boolean = false,
)

/** One row of a trail: an exchange, or a run of acknowledgements with no exchange between them. */
@Serializable
data class TrailEntry(
    val type: String = "",
    val id: String = "",
    val exchange: Exchange? = null,
    /** A run's acknowledgements, newest first. */
    val items: List<Acknowledgement> = emptyList(),
)

/** `GET /api/trails/<id>`: a person's, sphere's, alliance's, project's or exchange's trail, newest first. */
@Serializable
data class MeaningTrail(
    @SerialName("trail_id") val id: String = "",
    val kind: String = "user",
    val name: String = "",
    @SerialName("can_acknowledge") val canAcknowledge: Boolean = false,
    @SerialName("can_highlight") val canHighlight: Boolean = false,
    val entries: List<TrailEntry> = emptyList(),
) {
    val exchanges: List<Exchange> get() = entries.mapNotNull { it.exchange }

    fun mapExchanges(change: (Exchange) -> Exchange): MeaningTrail =
        copy(entries = entries.map { entry -> entry.exchange?.let { entry.copy(exchange = change(it)) } ?: entry })
}
