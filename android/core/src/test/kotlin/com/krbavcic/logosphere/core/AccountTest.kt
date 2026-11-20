package com.krbavcic.logosphere.core

import com.krbavcic.logosphere.core.api.ApiException
import com.krbavcic.logosphere.core.api.BearerAuthInterceptor
import com.krbavcic.logosphere.core.api.LogoSphereApi
import com.krbavcic.logosphere.core.api.LogoSphereJson
import com.krbavcic.logosphere.core.logic.Membership
import com.krbavcic.logosphere.core.model.Community
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.Member
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Before
import org.junit.Test

/** The member's own account: password, data export, deletion, leaving a group; admins' reset links. */
class AccountTest {
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

    private fun body(): JsonObject = LogoSphereJson.parseToJsonElement(server.takeRequest().body.readUtf8()) as JsonObject

    @Test
    fun changingThePasswordSendsBothAndSaysWhatHappened() = runTest {
        respond("""{"message":"Password changed. Your other devices were signed out.","signed_out":2}""")
        assertEquals("Password changed. Your other devices were signed out.", api.changePassword("old-one-1", "new-one-22"))
        val sent = body()
        assertEquals("old-one-1", sent["current_password"]?.jsonPrimitive?.content)
        assertEquals("new-one-22", sent["new_password"]?.jsonPrimitive?.content)
    }

    @Test
    fun aWrongPasswordIsTheServersMessage() = runTest {
        respond("""{"message":"That isn't your current password."}""", code = 403)
        try {
            api.changePassword("nope", "new-one-22")
            fail("expected a refusal")
        } catch (e: ApiException) {
            assertEquals(403, e.status)
            assertEquals("That isn't your current password.", e.message)
        }
    }

    @Test
    fun theExportComesBackAsTheFileItIs() = runTest {
        val file = """{
  "profile": {"email": "me@example.com"},
  "value_cards": []
}"""
        respond(file)
        assertEquals(file, api.exportData())
        assertEquals("/api/account/export", server.takeRequest().path)
    }

    @Test
    fun deletingAndLeaving() = runTest {
        respond("""{"message":"Your account was deleted."}""")
        api.deleteAccount("my-password")
        assertEquals("my-password", body()["password"]?.jsonPrimitive?.content)

        respond("""{"message":"You've left the alliance.","left":true}""")
        assertEquals("You've left the alliance.", api.leave(CommunityKind.Alliance, "a1"))
        assertEquals("/api/alliances/a1/leave", server.takeRequest().path)
    }

    @Test
    fun whoMayLeave() {
        val project = Community(
            projectId = "p1", sphereId = "s1", name = "P", kind = CommunityKind.Project,
            members = listOf(Member("boss", "B", "manager"), Member("c", "C", "contributor"), Member("q", "Q", "pending")),
        )
        assertFalse(Membership.canLeave(project, "boss"))
        assertTrue(Membership.canLeave(project, "c"))
        assertTrue(Membership.canLeave(project, "q"))      // withdrawing a request
        assertFalse(Membership.canLeave(project, "stranger"))
        val sphere = Community(
            sphereId = "s1", name = "S", admin1 = "f", kind = CommunityKind.Sphere,
            members = listOf(Member("f", "F", "admin"), Member("a2", "A", "admin")),
        )
        assertFalse(Membership.canLeave(sphere, "f"))
        assertTrue(Membership.canLeave(sphere, "a2"))       // a second admin isn't the founder
    }

    @Test
    fun anAdminGetsAResetLinksPath() = runTest {
        respond("""{"message":"A reset link for Marie Kondo, valid for 24 hours and once.","path":"/reset-password#token=abc","expires_at":"2026-11-22T10:00:00"}""")
        val link = api.adminResetLink("u2")
        assertTrue(link.path.startsWith("/reset-password#token="))
        assertEquals("/api/admin/users/u2/reset_link", server.takeRequest().path)
        // The site's address goes in front, fragment and all.
        assertTrue(api.webUrl(link.path).endsWith("/reset-password#token=abc"))
    }
}
