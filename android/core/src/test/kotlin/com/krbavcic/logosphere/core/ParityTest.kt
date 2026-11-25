package com.krbavcic.logosphere.core

import com.krbavcic.logosphere.core.api.BearerAuthInterceptor
import com.krbavcic.logosphere.core.api.LogoSphereApi
import com.krbavcic.logosphere.core.api.LogoSphereJson
import com.krbavcic.logosphere.core.api.Upload
import com.krbavcic.logosphere.core.logic.Membership
import com.krbavcic.logosphere.core.logic.Policies
import com.krbavcic.logosphere.core.logic.Roles
import com.krbavcic.logosphere.core.model.AdminGroups
import com.krbavcic.logosphere.core.model.AdminOpenings
import com.krbavcic.logosphere.core.model.AdminOverview
import com.krbavcic.logosphere.core.model.AdminUsers
import com.krbavcic.logosphere.core.model.Community
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.GroupGovernance
import com.krbavcic.logosphere.core.model.Member
import com.krbavcic.logosphere.core.model.NewCommunity
import com.krbavcic.logosphere.core.model.NewProposal
import com.krbavcic.logosphere.core.model.OwnProfile
import com.krbavcic.logosphere.core.model.ValueCard
import com.krbavcic.logosphere.core.model.ValueCardDraft
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/** The features that came over from the web in the parity pass: their decoding, rules and requests. */
class ParityTest {
    // ── Decoding ────────────────────────────────────────────────────────────

    @Test
    fun governanceDecodes() {
        val g = Fixtures.decode<GroupGovernance>("governance.json")
        assertEquals(listOf("join_policy", "decision_policy", "is_public"), g.policies.keys.toList())
        assertNull(g.policies.getValue("join_policy").value)
        assertEquals("Marie Konda", g.myDelegate?.name)
        assertEquals(1, g.delegatedToMe.size)
        assertEquals(1, g.open.size)
        assertEquals(1, g.decided.size)
        val open = g.open.single()
        assertTrue(open.isPolicy)
        assertEquals("yes", open.myVote)
        assertTrue(open.wouldPass)
        assertEquals(2, open.tally?.yes)
        assertEquals(1, open.tally?.unrepresented)
        assertEquals("rejected", g.decided.single().status)
        assertFalse(g.decided.single().wouldPass)
    }

    @Test
    fun ownProfileAndAdminListsDecode() {
        val me = Fixtures.decode<OwnProfile>("own_profile.json")
        assertEquals("Sam K", me.displayName)
        assertTrue(me.hasPicture)

        val overview = Fixtures.decode<AdminOverview>("admin_overview.json")
        assertEquals(31, overview.counts.users)
        assertEquals(22, overview.counts.openingsOpen)
        assertEquals("Sam K", overview.platformAdmins.single().name)

        val users = Fixtures.decode<AdminUsers>("admin_users.json").users
        assertTrue(users[0].isYou && users[0].isPlatformAdmin)
        assertTrue(users[1].isAgent)
        assertEquals("Marie Konda", users[1].label)

        val sphere = Fixtures.decode<AdminGroups>("admin_spheres.json").items.single()
        assertEquals(CommunityKind.Sphere, sphere.communityKind)
        assertEquals(1, sphere.pendingCount)
        assertTrue(sphere.isDemo)
        assertNull(sphere.policy("join_policy"))
        assertEquals("majority", sphere.policy("decision_policy"))

        val openings = Fixtures.decode<AdminOpenings>("admin_openings.json").items
        assertTrue(openings[0].isOpen)
        assertFalse(openings[0].isOffer)
        assertEquals("Marie Konda for Riverside Commons", openings[1].providerLabel)
    }

    @Test
    fun detailCarriesPoliciesAndPendingRequestsForManagers() {
        val c = LogoSphereJson.decodeFromString<Community>(
            """{"alliance_id":"a1","sphere_id":"s1","name":"Tool library","decision_policy":"consensus",
               "pm_policy":"board","confirm_policy":"lead","pending_members":[{"id":"u9","name":"New Person"}]}""",
        ).copy(kind = CommunityKind.Alliance)
        assertEquals("consensus", Policies.valueOf(c, "decision_policy"))
        assertEquals("board", Policies.valueOf(c, "pm_policy"))
        assertEquals("lead", Policies.valueOf(c, "confirm_policy"))
        assertEquals("open", Policies.valueOf(c, "join_policy")) // unset: the server's default
        assertEquals("New Person", c.pendingMembers.single().name)
    }

    // ── Rules ───────────────────────────────────────────────────────────────

    private val project = Community(
        projectId = "p1", sphereId = "s1", name = "Repair café", kind = CommunityKind.Project,
        members = listOf(Member("boss", "Boss", "manager"), Member("st", "Steward", "steward"), Member("c", "Contributor", "contributor")),
    )

    @Test
    fun onlyTheTopRoleOrAPlatformAdminSetsRoles() {
        assertTrue(Membership.canSetRoles(project, "boss", isPlatformAdmin = false))
        assertTrue(Membership.isFounder(project, "boss"))
        // A steward manages the project but doesn't change roles.
        assertTrue(Membership.canManage(project, "st", isPlatformAdmin = false))
        assertFalse(Membership.canSetRoles(project, "st", isPlatformAdmin = false))
        assertTrue(Membership.canSetRoles(project, "c", isPlatformAdmin = true))
        assertFalse(Membership.managesItself(project, "c"))
        // A sphere's founder is admin1 even without a role row.
        val sphere = Community(sphereId = "s1", name = "S", admin1 = "f", kind = CommunityKind.Sphere)
        assertTrue(Membership.canSetRoles(sphere, "f", isPlatformAdmin = false))
        assertFalse(Membership.canSetRoles(sphere, null, isPlatformAdmin = true))
    }

    @Test
    fun roleActionsFollowTheWeb() {
        val steward = Member("st", "S", "steward")
        val contributor = Member("c", "C", "contributor")
        assertEquals(listOf("contributor"), Roles.actions(CommunityKind.Project, steward).map { it.role })
        assertEquals(listOf("steward"), Roles.actions(CommunityKind.Project, contributor).map { it.role })
        assertEquals(listOf("member"), Roles.actions(CommunityKind.Alliance, Member("b", "B", "steward")).map { it.role })
        assertEquals(listOf("admin"), Roles.actions(CommunityKind.Sphere, Member("m", "M", "member")).map { it.role })
        assertFalse(Roles.canRemove(CommunityKind.Project, Member("boss", "B", "manager")))
        assertTrue(Roles.canRemove(CommunityKind.Alliance, Member("b", "B", "steward")))
        assertEquals("Lead", Roles.label(CommunityKind.Alliance, "admin"))
        assertEquals("Board member", Roles.label(CommunityKind.Alliance, "steward"))
        assertEquals("contributor", Roles.defaultRole(CommunityKind.Project))
    }

    @Test
    fun policiesPerKind() {
        assertEquals(listOf("join_policy", "decision_policy"), Policies.fields(CommunityKind.Sphere).map { it.key })
        assertEquals(listOf("join_policy", "decision_policy", "pm_policy", "confirm_policy"), Policies.fields(CommunityKind.Alliance).map { it.key })
        assertEquals(listOf("join_policy", "decision_policy", "phase"), Policies.fields(CommunityKind.Project).map { it.key })
        val g = Fixtures.decode<GroupGovernance>("governance.json")
        // An unset join policy is open: the proposal can only make it "approval".
        assertEquals(listOf("approval"), Policies.proposalOptions("join_policy", g.policies.getValue("join_policy")))
        assertEquals(listOf("supermajority", "consensus"), Policies.proposalOptions("decision_policy", g.policies.getValue("decision_policy")))
        assertEquals("Off", Policies.valueLabel("false"))
        assertEquals("Lead and Board members", Policies.valueLabel("board"))
        assertTrue(Policies.decisionCopy("consensus").startsWith("consensus"))
    }

    @Test
    fun aDraftKeepsOneBehaviourPerLine() {
        val card = ValueCard(id = "c1", title = "Care", careAbout = "People", looksLike = listOf("Listening", "Showing up"), franklMode = "experiential", colorKey = "moss")
        val draft = ValueCardDraft.of(card)
        assertEquals("Listening\nShowing up", draft.looksLike)
        assertEquals("experiential", draft.franklMode)
        assertEquals(listOf("a", "b"), draft.copy(looksLike = " a \n\n b\n").looksLikeLines)
    }

    // ── Requests ────────────────────────────────────────────────────────────

    private lateinit var server: MockWebServer
    private lateinit var api: LogoSphereApi

    @Before
    fun setUp() {
        server = MockWebServer()
        server.start()
        val base = server.url("/")
        val client = OkHttpClient.Builder().addInterceptor(BearerAuthInterceptor(server = { base }, token = { "tok" })).build()
        api = LogoSphereApi(client, server = { base })
    }

    @After
    fun tearDown() {
        server.shutdown()
    }

    private fun respond(body: String = "{}", code: Int = 200) {
        server.enqueue(MockResponse().setResponseCode(code).setHeader("Content-Type", "application/json").setBody(body))
    }

    private fun RecordedRequest.json(): JsonObject = LogoSphereJson.parseToJsonElement(body.readUtf8()) as JsonObject

    private val cardJson = """{"card_id":"new","user_id":"me","title":"T","care_about":"C"}"""

    @Test
    fun writingValueCardsUsesTheOwnersEndpoints() = runTest {
        val draft = ValueCardDraft(title = " Honest dialogue ", careAbout = "Truth", looksLike = "Listening\nAsking", colorKey = "leaf")
        respond(cardJson)
        api.saveValueCard(null, null, draft)
        server.takeRequest().let {
            assertEquals("POST", it.method)
            assertEquals("/api/value_cards", it.path)
            val body = it.json()
            assertEquals("Honest dialogue", body["title"]?.jsonPrimitive?.content)
            assertEquals(2, body["looks_like"]?.jsonArray?.size)
            assertEquals("leaf", body["color_key"]?.jsonPrimitive?.content)
        }
        respond(cardJson)
        api.saveValueCard("g1", "c1", draft)
        server.takeRequest().let {
            assertEquals("PATCH", it.method)
            assertEquals("/api/entity_value_cards/g1/c1", it.path)
        }
        respond()
        api.deleteValueCard("g1", "c1")
        server.takeRequest().let {
            assertEquals("DELETE", it.method)
            assertEquals("/api/entity_value_cards/g1/c1", it.path)
        }
        respond(cardJson)
        api.endorseValueCard(null, "c1")
        assertEquals("/api/value_cards/c1/endorse", server.takeRequest().path)
        respond(cardJson)
        api.cloneValueCard(ValueCard(id = "x", title = "T", careAbout = "C"), targetId = "g1")
        server.takeRequest().json().let {
            assertEquals("g1", it["target_id"]?.jsonPrimitive?.content)
            assertEquals("C", it["source"]?.jsonObject?.get("care_about")?.jsonPrimitive?.content)
        }
    }

    @Test
    fun aProfilePhotoGoesUpAsMultipart() = runTest {
        respond("""{"user_id":"me"}""")
        api.updateProfile("Sam", "K", Upload(byteArrayOf(1, 2, 3), "me.jpg", "image/jpeg"))
        val request = server.takeRequest()
        assertEquals("/api/updateuser", request.path)
        assertTrue(request.getHeader("Content-Type")!!.startsWith("multipart/form-data"))
        val body = request.body.readUtf8()
        assertTrue(body.contains("name=\"name\""))
        // Where you are is saved as a place: sent here, new words would drop the point.
        assertFalse(body.contains("name=\"location\""))
        assertTrue(body.contains("name=\"profile_picture\"; filename=\"me.jpg\""))
    }

    @Test
    fun receiptPhotosAreCappedAtThree() = runTest {
        respond("""{"count":3}""")
        val photos = List(5) { Upload(byteArrayOf(it.toByte()), "p$it.jpg") }
        assertEquals(3, api.addReceiptPhotos("x1", photos))
        val body = server.takeRequest().body.readUtf8()
        assertEquals(3, Regex("name=\"photos\"").findAll(body).count())
    }

    @Test
    fun aNewAllianceSetsItsJoinPolicyAfterwards() = runTest {
        respond("""{"alliance_id":"a9","sphere_id":"s1","name":"Tool library"}""", code = 201)
        respond("""{"alliance_id":"a9","sphere_id":"s1","name":"Tool library","join_policy":"approval"}""")
        val created = api.createCommunity(
            NewCommunity(CommunityKind.Alliance, "Tool library", "Shared tools", sphereId = "s1", sphereName = "Riverside", joinPolicy = "approval"),
        )
        assertEquals("a9", created.id)
        assertEquals("approval", created.joinPolicy)
        server.takeRequest().let {
            assertEquals("/api/alliances", it.path)
            assertTrue(it.body.readUtf8().contains("name=\"sphere_id\""))
        }
        server.takeRequest().let {
            assertEquals("PATCH", it.method)
            assertEquals("/api/alliances/a9", it.path)
            assertEquals("approval", it.json()["join_policy"]?.jsonPrimitive?.content)
        }
    }

    @Test
    fun governanceRequests() = runTest {
        respond()
        api.propose(CommunityKind.Project, "p1", NewProposal("policy", "", "", 5, "phase", "closed"))
        server.takeRequest().let {
            assertEquals("/api/projects/p1/proposals", it.path)
            val body = it.json()
            assertEquals("phase", body["policy_key"]?.jsonPrimitive?.content)
            assertEquals(5, body["days"]?.jsonPrimitive?.content?.toInt())
        }
        respond()
        api.propose(CommunityKind.Sphere, "s1", NewProposal("motion", "Swap on Saturdays", "", 7))
        assertFalse(server.takeRequest().json().containsKey("policy_key"))
        respond()
        api.vote(CommunityKind.Alliance, "a1", "pr1", "abstain")
        server.takeRequest().let {
            assertEquals("/api/alliances/a1/proposals/pr1/vote", it.path)
            assertEquals("abstain", it.json()["choice"]?.jsonPrimitive?.content)
        }
        respond()
        api.delegateVote(CommunityKind.Sphere, "s1", null)
        assertEquals(JsonNull, server.takeRequest().json()["delegate_id"])
        respond()
        api.setMemberRole(CommunityKind.Sphere, "s1", "u9", Roles.REMOVE)
        server.takeRequest().let {
            assertEquals("/api/spheres/s1/members/u9/role", it.path)
            assertEquals("remove", it.json()["role"]?.jsonPrimitive?.content)
        }
    }

    @Test
    fun anEditedOpeningMayComeBackAsANewVersion() = runTest {
        respond("""{"message":"A new version of the opening was created","versioned":true,"service":{"service_id":"o2","title":"New"}}""")
        val result = api.editOpening("o1", "New", "")
        assertTrue(result.versioned)
        assertEquals("o2", result.service?.id)
        assertEquals("PATCH", server.takeRequest().method)
    }

    @Test
    fun adminRequests() = runTest {
        respond(Fixtures.text("admin_spheres.json"))
        assertEquals(1, api.adminGroups(CommunityKind.Sphere).size)
        assertEquals("/api/admin/spheres", server.takeRequest().path)
        respond()
        api.adminSetUserFlags("u2", isAgent = false)
        server.takeRequest().let {
            assertEquals("PATCH", it.method)
            val body = it.json()
            assertEquals("false", body["is_agent"]?.jsonPrimitive?.content)
            assertFalse(body.containsKey("is_platform_admin"))
        }
        respond()
        api.adminDeleteOpening("o1")
        server.takeRequest().let {
            assertEquals("DELETE", it.method)
            assertEquals("/api/admin/openings/o1", it.path)
        }
        respond()
        api.setSphereFlags("s1", isPublic = true)
        assertEquals("true", server.takeRequest().json()["is_public"]?.jsonPrimitive?.content)
    }
}
