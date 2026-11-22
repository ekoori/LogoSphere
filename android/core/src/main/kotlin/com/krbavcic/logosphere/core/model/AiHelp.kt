package com.krbavcic.logosphere.core.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import java.util.Base64

/** One kind of AI help: whether it's switched on, and what is left of the member's day. */
@Serializable
data class AiAllowance(val on: Boolean = false, val left: Int = 0)

/** `GET /api/ai`. */
@Serializable
data class AiHelpStatus(
    @SerialName("value_cards") val valueCards: AiAllowance = AiAllowance(),
    val pictures: AiAllowance = AiAllowance(),
)

/** What AI help may put into a card. Shown first; never saved by itself. */
@Serializable
data class SuggestedCard(
    val title: String = "",
    @SerialName("care_about") val careAbout: String = "",
    val because: String = "",
    @SerialName("looks_like") val looksLike: List<String> = emptyList(),
    @SerialName("drift_looks_like") val driftLooksLike: String = "",
    @SerialName("in_conflict") val inConflict: String = "",
    @SerialName("never_do") val neverDo: String = "",
    @SerialName("frankl_mode") val franklMode: String? = null,
) {
    /** The words to show, by field; none when the AI only had a question. */
    val lines: List<Pair<String, String>>
        get() = listOf(
            "Title" to title,
            "Cares about" to careAbout,
            "Because" to because,
            "Looks like" to looksLike.joinToString("; "),
            "Drift looks like" to driftLooksLike,
            "In conflict" to inConflict,
            "Never" to neverDo,
        ).filter { it.second.isNotBlank() }

    /**
     * [draft] with this in it. An empty suggestion never wipes what was typed; [brief] (Simple)
     * changes only the three fields that show there.
     */
    fun into(draft: ValueCardDraft, brief: Boolean): ValueCardDraft {
        val short = draft.copy(
            title = title.ifBlank { draft.title },
            careAbout = careAbout.ifBlank { draft.careAbout },
            because = because.ifBlank { draft.because },
        )
        if (brief) return short
        return short.copy(
            looksLike = looksLike.joinToString("\n").ifBlank { draft.looksLike },
            driftLooksLike = driftLooksLike.ifBlank { draft.driftLooksLike },
            inConflict = inConflict.ifBlank { draft.inConflict },
            neverDo = neverDo.ifBlank { draft.neverDo },
            franklMode = franklMode ?: draft.franklMode,
        )
    }
}

@Serializable
data class CardSuggestion(
    val draft: SuggestedCard = SuggestedCard(),
    val question: String = "",
    val left: Int = 0,
)

/** A picture the AI drew, as base64. Upload it byte for byte: that keeps it known as AI-made. */
@Serializable
data class AiPicture(
    val image: String,
    @SerialName("content_type") val contentType: String = "image/jpeg",
    val left: Int = 0,
) {
    val bytes: ByteArray get() = Base64.getDecoder().decode(image)
}
