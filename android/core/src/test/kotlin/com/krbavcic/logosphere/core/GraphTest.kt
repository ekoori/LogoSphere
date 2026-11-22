package com.krbavcic.logosphere.core

import com.krbavcic.logosphere.core.api.LogoSphereApi
import com.krbavcic.logosphere.core.api.LogoSphereJson
import com.krbavcic.logosphere.core.logic.AppLink
import com.krbavcic.logosphere.core.logic.ForceLayout
import com.krbavcic.logosphere.core.logic.GraphScope
import com.krbavcic.logosphere.core.logic.GraphView
import com.krbavcic.logosphere.core.logic.Links
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.FranklMode
import com.krbavcic.logosphere.core.model.GraphEdge
import com.krbavcic.logosphere.core.model.GraphNode
import com.krbavcic.logosphere.core.model.GraphOwner
import com.krbavcic.logosphere.core.model.MeaningGraph
import com.krbavcic.logosphere.core.model.ValueCard
import kotlinx.coroutines.test.runTest
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class GraphTest {
    private fun node(id: String, mine: Boolean = false, near: Boolean = false, demo: Boolean = false) =
        GraphNode(id, ValueCard(title = "Card $id"), GraphOwner("o-$id", "Owner $id"), isDemo = demo, mine = mine, near = near)

    private val graph = MeaningGraph(
        nodes = listOf(node("a", mine = true, near = true), node("b", near = true), node("c", demo = true), node("d")),
        edges = listOf(GraphEdge("a", "b", 0.5), GraphEdge("b", "c", 0.3), GraphEdge("c", "d", 0.05)),
    )

    private fun ids(
        scope: GraphScope = GraphScope.Everyone,
        owner: String? = null,
        focus: String? = null,
        demos: Boolean = true,
        query: String = "",
    ) = GraphView.visible(graph, scope, owner, focus, demos, query, from = 0.12).nodes.joinToString("") { it.id }

    @Test
    fun showsWhatTheSiteShows() {
        assertEquals("abcd", ids())
        assertEquals("ab", ids(scope = GraphScope.Mine))
        assertEquals("ab", ids(scope = GraphScope.Near))
        assertEquals("abd", ids(demos = false))
        assertEquals("ab", ids(query = " card A "))
        assertEquals("bc", ids(focus = "c"))
        assertEquals("d", ids(owner = "o-d"))
    }

    @Test
    fun countsOnlyConnectionsShownAndListsTheClosestFirst() {
        val shown = GraphView.visible(graph, from = 0.12)
        assertEquals(2, shown.degree["b"])
        assertEquals(0, shown.degree["d"])
        assertEquals(listOf("a", "c"), GraphView.closestTo("b", graph.edges).map { it.other("b") })
        assertEquals("15%", GraphView.percent(0.151))
    }

    @Test
    fun settlesIntoTheSitesPicture() {
        // From frontend/src/utils/forceLayout.js, with the same cards and closeness.
        val expected = mapOf(
            "a" to (-28.87328038747274 to 69.4172321142023),
            "b" to (-33.13755026895057 to 35.22512411967771),
            "c" to (16.187682942698245 to 40.96469646822847),
            "d" to (71.48540116208191 to 30.277412597009338),
            "e" to (-28.375611046622133 to -89.89651696605684),
            "f" to (11.037736665252394 to -93.6338096473665),
        )
        val edges = listOf(
            GraphEdge("a", "b", 0.9), GraphEdge("b", "c", 0.3), GraphEdge("c", "d", 0.12),
            GraphEdge("a", "c", 0.2), GraphEdge("e", "f", 0.5),
        )
        val layout = ForceLayout(listOf("f", "e", "d", "c", "b", "a"), edges)
        layout.settle()
        for ((id, at) in expected) {
            assertEquals(at.first, layout.byId.getValue(id).x, 0.01)
            assertEquals(at.second, layout.byId.getValue(id).y, 0.01)
        }
    }

    @Test
    fun decodesTheServersGraph() {
        val json = """
            {"method_version":1,"shown_from":0.12,"nodes":[
              {"id":"r1","card":{"card_id":"c9","title":null,"care_about":"Seeds","frankl_mode":"attitudinal"},
               "owner":{"id":"s","name":"Garden","kind":"sphere","is_agent":false},
               "is_demo":true,"mine":false,"near":true,"can_judge":true}],
             "edges":[{"a":"r1","b":"r2","closeness":0.31,"words":0.31,"people":0,"lineage":false,"judges":0,
               "said_close":0,"my_judgement":null,
               "shared":[{"counts_as":"seeds","family":true,"here":["seed"],"there":["seeds"],"share":1.0}]}]}
        """.trimIndent()
        val decoded = LogoSphereJson.decodeFromString<MeaningGraph>(json)
        val card = decoded.nodes.single()
        assertEquals("Seeds", card.title)
        assertEquals(FranklMode.Attitudinal, card.mode)
        assertEquals(CommunityKind.Sphere, card.owner.communityKind)
        assertNull(decoded.edges.single().myJudgement)
        assertEquals(listOf("seeds"), decoded.edges.single().shared.single().there)

        val judged = decoded.withEdge(decoded.edges.single().copy(myJudgement = true))
        assertEquals(true, judged.edges.single().myJudgement)
    }

    @Test
    fun judgesAndTakesAJudgementBack() = runTest {
        val server = MockWebServer()
        server.start()
        try {
            repeat(2) {
                server.enqueue(MockResponse().setBody("""{"edge":{"a":"a","b":"b","closeness":0.4}}"""))
            }
            val base = server.url("/")
            val api = LogoSphereApi(OkHttpClient(), server = { base })
            assertEquals(0.4, api.judgeCloseness("a", "b", true).closeness, 0.0)
            assertEquals("""{"a":"a","b":"b","close":true}""", server.takeRequest().body.readUtf8())
            api.judgeCloseness("a", "b", null)
            val undo = server.takeRequest()
            assertEquals("/api/meaning_graph/judgement", undo.path)
            assertTrue(undo.body.readUtf8().contains("\"close\":null"))
        } finally {
            server.shutdown()
        }
    }

    @Test
    fun aGraphLinkOpensTheGraph() {
        assertEquals(AppLink.MeaningGraph(null), Links.parse("/meaning-graph"))
        assertEquals(AppLink.MeaningGraph("u1"), Links.parse("/meaning-graph?owner=u1"))
    }
}
