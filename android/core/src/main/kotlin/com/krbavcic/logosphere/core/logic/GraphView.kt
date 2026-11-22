package com.krbavcic.logosphere.core.logic

import com.krbavcic.logosphere.core.model.GraphEdge
import com.krbavcic.logosphere.core.model.GraphNode
import com.krbavcic.logosphere.core.model.MeaningGraph
import kotlin.math.roundToInt

enum class GraphScope(val label: String) {
    Everyone("Everyone"),
    Near("My spheres"),
    Mine("My values"),
}

/** What to draw: [degree] is connections shown, [found] what a search matched. */
data class ShownGraph(
    val nodes: List<GraphNode>,
    val edges: List<GraphEdge>,
    val degree: Map<String, Int>,
    val found: Set<String>,
)

/**
 * What the Meaning Graph shows for the current filters (the site's utils/graph.js does the same).
 * Closeness is the server's: nothing here changes a score, only what is drawn.
 */
object GraphView {
    /**
     * [owner]: one person's or group's cards and what they connect to; [focus]: one card's.
     * A search keeps what matches and what that connects to, so it isn't an island.
     */
    fun visible(
        graph: MeaningGraph,
        scope: GraphScope = GraphScope.Everyone,
        owner: String? = null,
        focus: String? = null,
        demos: Boolean = true,
        query: String = "",
        from: Double = 0.0,
    ): ShownGraph {
        var nodes = graph.nodes.filter { demos || !it.isDemo || it.mine }
        var ids = nodes.mapTo(HashSet()) { it.id }
        var edges = graph.edges.filter { it.closeness >= from && it.a in ids && it.b in ids }

        fun around(keep: (GraphNode) -> Boolean): Set<String> {
            val seeds = nodes.filter(keep).mapTo(HashSet()) { it.id }
            val out = HashSet(seeds)
            for (edge in edges) {
                if (edge.a in seeds) out += edge.b
                if (edge.b in seeds) out += edge.a
            }
            return out
        }

        fun narrow(keep: Set<String>) {
            nodes = nodes.filter { it.id in keep }
            ids = nodes.mapTo(HashSet()) { it.id }
            edges = edges.filter { it.a in ids && it.b in ids }
        }

        when {
            focus != null && focus in ids -> narrow(around { it.id == focus })
            owner != null -> narrow(around { it.owner.id == owner })
            scope == GraphScope.Mine -> narrow(around { it.mine })
            scope == GraphScope.Near -> narrow(nodes.filter { it.near }.mapTo(HashSet()) { it.id })
        }

        val term = query.trim().lowercase()
        val found = nodes.filter { matches(it, term) }.mapTo(HashSet()) { it.id }
        if (term.isNotEmpty()) narrow(around { it.id in found })

        val degree = nodes.associateTo(HashMap()) { it.id to 0 }
        for (edge in edges) {
            degree[edge.a] = degree.getValue(edge.a) + 1
            degree[edge.b] = degree.getValue(edge.b) + 1
        }
        return ShownGraph(nodes, edges, degree, found)
    }

    /** A card's connections, closest first. */
    fun closestTo(id: String, edges: List<GraphEdge>): List<GraphEdge> =
        edges.filter { it.touches(id) }.sortedWith(compareByDescending<GraphEdge> { it.closeness }.thenBy { it.other(id) })

    fun percent(x: Double): String = "${(x * 100).roundToInt()}%"

    private fun matches(node: GraphNode, term: String): Boolean {
        if (term.isEmpty()) return true
        val card = node.card
        val texts = listOfNotNull(card.title, card.careAbout, card.because, node.owner.name) + card.looksLike
        return texts.any { term in it.lowercase() }
    }
}
