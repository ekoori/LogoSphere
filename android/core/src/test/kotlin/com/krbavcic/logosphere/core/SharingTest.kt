package com.krbavcic.logosphere.core

import com.krbavcic.logosphere.core.api.BearerAuthInterceptor
import com.krbavcic.logosphere.core.api.LogoSphereApi
import com.krbavcic.logosphere.core.api.LogoSphereJson
import com.krbavcic.logosphere.core.logic.OpeningRules
import com.krbavcic.logosphere.core.logic.Sharing
import com.krbavcic.logosphere.core.model.Community
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.Exchange
import com.krbavcic.logosphere.core.model.GroupSummary
import com.krbavcic.logosphere.core.model.Member
import com.krbavcic.logosphere.core.model.NewOpening
import com.krbavcic.logosphere.core.model.Opening
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class SharingTest {
    private lateinit var server: MockWebServer
    private lateinit var api: LogoSphereApi

    @Before
    fun setUp() {
        server = MockWebServer()
        server.start()
        val base = server.url("/")
        val client = OkHttpClient.Builder().addInterceptor(BearerAuthInterceptor({ base }, { "tok" })).build()
        api = LogoSphereApi(client, server = { base })
    }

    @After
    fun tearDown() = server.shutdown()

    private fun sphere(id: String, role: String? = "member", demo: Boolean = false) = Community(
        sphereId = id,
        name = id,
        isDemo = demo,
        members = role?.let { listOf(Member("me", role = it)) }.orEmpty(),
        kind = CommunityKind.Sphere,
    )

    private val spheres =
        listOf(sphere("home"), sphere("hill"), sphere("demo", demo = true), sphere("asked", "pending"), sphere("theirs", null))

    @Test
    fun offersTheViewersOtherSpheresOfTheSameKind() {
        fun ids(homeId: String?, demo: Boolean, mayAdd: Boolean = true, already: List<GroupSummary> = emptyList()) =
            Sharing.choices(spheres, homeId, demo, "me", already, mayAdd).map { it.id }
        assertEquals(listOf("hill"), ids("home", demo = false))
        assertEquals(listOf("demo"), ids("elsewhere", demo = true))
        assertEquals(emptyList<String>(), ids(null, demo = false))
        assertEquals(listOf("theirs"), ids("home", false, mayAdd = false, already = listOf(GroupSummary("theirs", name = "theirs"))))
    }

    @Test
    fun aGroupInASphereItWasSharedWithMayTakeItUp() {
        val opening = Opening(id = "o", sphereId = "home", sharedWith = listOf(GroupSummary("hill", name = "Hill")))
        assertTrue(Sharing.isIn(opening, "hill"))
        assertFalse(Sharing.isIn(opening, "theirs"))
        val group = Community(allianceId = "a", sphereId = "hill", name = "Fixers", kind = CommunityKind.Alliance)
        assertEquals(listOf(group), OpeningRules.acceptAsOptions(opening, listOf(group)))
    }

    @Test
    fun aLoanSaysWhenToFinishIt() {
        assertNull(Sharing.loanNote(Exchange("x", status = "Initiated")))
        assertEquals("A loan. Mark the exchange finished when it's back.", Sharing.loanNote(Exchange("x", status = "In Progress", borrow = true)))
        assertEquals("This was a loan.", Sharing.loanNote(Exchange("x", status = "Receipted", borrow = true)))
    }

    @Test
    fun postingSendsTheLoanAndTheSpheres() = runTest {
        server.enqueue(MockResponse().setBody("""{"service_id":"o"}"""))
        val new = NewOpening("offer", "single", "Ladder", "", "home", "Home", null, borrow = true, alsoSphereIds = listOf("hill"))
        assertEquals("o", api.createOpening(new))
        val sent = LogoSphereJson.parseToJsonElement(server.takeRequest().body.readUtf8()).jsonObject
        assertEquals("true", sent["borrow"]!!.jsonPrimitive.content)
        assertEquals(listOf("hill"), sent["also_sphere_ids"]!!.jsonArray.map { it.jsonPrimitive.content })
    }

    @Test
    fun sharingWithNoneSendsAnEmptyList() = runTest {
        server.enqueue(MockResponse().setBody("""{"service_id":"o","shared_with":[]}"""))
        assertEquals(emptyList<GroupSummary>(), api.shareOpening("o", emptyList()).sharedWith)
        val request = server.takeRequest()
        assertEquals("/api/openings/o/spheres", request.path)
        assertEquals("""{"sphere_ids":[]}""", request.body.readUtf8())
    }

    @Test
    fun activityAndWhomYouBothKnowDecode() = runTest {
        server.enqueue(
            MockResponse().setBody(
                """{"activity":[{"kind":"opening","at":"2026-11-23T10:00:00","who":{"id":"a","name":"Ada","is_agent":false},
                   "says":"offers to lend","title":"Ladder","link":"/opening?id=o","is_demo":false}]}""",
            ),
        )
        assertEquals("offers to lend", api.activity().single().says)
        server.enqueue(MockResponse().setBody("""{"people":[{"id":"c","name":"Cy","is_agent":false}]}"""))
        assertEquals("Cy", api.known("a").single().name)
    }
}
