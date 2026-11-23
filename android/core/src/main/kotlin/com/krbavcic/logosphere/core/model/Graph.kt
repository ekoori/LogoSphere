package com.krbavcic.logosphere.core.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** Whose card a node is: a person's, or a sphere's, alliance's or project's. */
@Serializable
data class GraphOwner(
    val id: String = "",
    val name: String = "",
    val kind: String = "user",
    @SerialName("is_agent") val isAgent: Boolean = false,
) {
    val isGroup: Boolean get() = kind != "user"

    /** The group's kind; null for a person. */
    val communityKind: CommunityKind? get() = if (isGroup) CommunityKind.of(kind) else null
}

/** One value card, through all its edits: [id] is the first version's. */
@Serializable
data class GraphNode(
    val id: String,
    val card: ValueCard = ValueCard(),
    val owner: GraphOwner = GraphOwner(),
    @SerialName("is_demo") val isDemo: Boolean = false,
    val mine: Boolean = false,
    /** In one of the viewer's spheres. */
    val near: Boolean = false,
    @SerialName("can_judge") val canJudge: Boolean = false,
) {
    val title: String get() = card.title.ifBlank { card.careAbout.orEmpty() }.ifBlank { "Untitled value" }
    val mode: FranklMode get() = FranklMode.of(card.franklMode) ?: FranklMode.Creative
}

/** A word two cards share, as each of them wrote it. */
@Serializable
data class SharedWord(
    @SerialName("counts_as") val countsAs: String = "",
    val family: Boolean = false,
    val here: List<String> = emptyList(),
    val there: List<String> = emptyList(),
)

/** How close two cards are, with every part of the score. */
@Serializable
data class GraphEdge(
    val a: String,
    val b: String,
    val closeness: Double = 0.0,
    val words: Double = 0.0,
    val shared: List<SharedWord> = emptyList(),
    val people: Int = 0,
    val lineage: Boolean = false,
    val judges: Int = 0,
    @SerialName("said_close") val saidClose: Int = 0,
    /** The viewer's own: close, not close, or null for none. */
    @SerialName("my_judgement") val myJudgement: Boolean? = null,
) {
    fun touches(id: String) = a == id || b == id
    fun other(id: String) = if (a == id) b else a
    fun joinsSameCards(edge: GraphEdge) = a == edge.a && b == edge.b
}

/** `GET /api/meaning_graph`: the cards the viewer may read, and how close they are. */
@Serializable
data class MeaningGraph(
    val nodes: List<GraphNode> = emptyList(),
    val edges: List<GraphEdge> = emptyList(),
    @SerialName("shown_from") val shownFrom: Double = 0.12,
) {
    fun withEdge(edge: GraphEdge): MeaningGraph =
        copy(edges = edges.map { if (it.joinsSameCards(edge)) edge else it })
}

@Serializable
data class JudgementResult(val edge: GraphEdge)

@Serializable
data class FieldWeight(@SerialName("field") val key: String, val weight: Double = 0.0) {
    val label: String get() = labelOf(key)

    companion object {
        fun labelOf(field: String): String = when (field) {
            "care_about" -> "What you care about"
            "looks_like" -> "What it looks like"
            "title" -> "Title"
            "because" -> "Because"
            "never_do" -> "What you would never do"
            "drift_looks_like" -> "What drift looks like"
            "in_conflict" -> "When in conflict"
            else -> field
        }
    }
}

@Serializable
data class MethodSource(val title: String = "", val url: String = "")

/** `GET /api/meaning_graph/method`: everything needed to work a score out by hand. */
@Serializable
data class ClosenessMethod(
    val idea: String = "",
    val formula: List<String> = emptyList(),
    val fields: List<FieldWeight> = emptyList(),
    @SerialName("not_counted") val notCounted: List<String> = emptyList(),
    @SerialName("never_inputs") val neverInputs: List<String> = emptyList(),
    val rules: List<String> = emptyList(),
    val limits: List<String> = emptyList(),
    @SerialName("stop_words") val stopWords: List<String> = emptyList(),
    val families: Map<String, List<String>> = emptyMap(),
    val sources: List<MethodSource> = emptyList(),
)

/** `GET /api/meaning_graph/card/<id>`: which dot a value card is. */
@Serializable
data class GraphNodeRef(val id: String)
