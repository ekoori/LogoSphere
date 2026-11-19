package com.krbavcic.logosphere.core

import com.krbavcic.logosphere.core.api.ApiException
import com.krbavcic.logosphere.core.api.BearerAuthInterceptor
import com.krbavcic.logosphere.core.api.LogoSphereApi
import com.krbavcic.logosphere.core.api.LogoSphereJson
import com.krbavcic.logosphere.core.api.UnauthorizedException
import com.krbavcic.logosphere.core.api.userMessage
import com.krbavcic.logosphere.core.model.CommentType
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.FranklMode
import com.krbavcic.logosphere.core.model.NewComment
import com.krbavcic.logosphere.core.model.ValueCard
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okio.buffer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Before
import org.junit.Test

class LogoSphereApiTest {
    private lateinit var server: MockWebServer
    private var token: String? = "tok-123"
    private var unauthorizedCalls = 0
    private lateinit var client: OkHttpClient
    private lateinit var api: LogoSphereApi

    @Before
    fun setUp() {
        server = MockWebServer()
        server.start()
        val base = server.url("/")
        client = OkHttpClient.Builder()
            .addInterceptor(BearerAuthInterceptor(server = { base }, token = { token }))
            .build()
        api = LogoSphereApi(client, server = { base }, onUnauthorized = { unauthorizedCalls++ })
    }

    @After
    fun tearDown() {
        server.shutdown()
    }

    private fun respond(body: String, code: Int = 200) {
        server.enqueue(MockResponse().setResponseCode(code).setHeader("Content-Type", "application/json").setBody(body))
    }

    @Test
    fun sendsTheSessionAsABearerToken() = runTest {
        respond(Fixtures.text("check_session.json"))
        val session = api.checkSession()
        assertTrue(session.isActive)
        val request = server.takeRequest()
        assertEquals("/api/check_session", request.path)
        assertEquals("Bearer tok-123", request.getHeader("Authorization"))
    }

    @Test
    fun noTokenNoHeader() = runTest {
        token = null
        respond("""{"status":"inactive","user_id":null}""")
        assertFalse(api.checkSession().isActive)
        assertNull(server.takeRequest().getHeader("Authorization"))
    }

    @Test
    fun theTokenNeverGoesToAnotherHost() {
        val other = MockWebServer()
        other.start()
        try {
            other.enqueue(MockResponse().setBody("ok"))
            // Same port on a different host name: "127.0.0.1" vs the server's "localhost".
            val url = other.url("/x").newBuilder().host(if (server.hostName == "localhost") "127.0.0.1" else "localhost").build()
            client.newCall(Request.Builder().url(url).build()).execute().close()
            assertNull(other.takeRequest().getHeader("Authorization"))
        } finally {
            other.shutdown()
        }
    }

    @Test
    fun errorsCarryTheServersMessage() = runTest {
        respond("""{"message":"This opening is no longer open"}""", code = 409)
        try {
            api.acceptOpening("o1")
            fail("expected ApiException")
        } catch (e: ApiException) {
            assertEquals(409, e.status)
            assertEquals("This opening is no longer open", e.userMessage())
        }
        assertEquals(0, unauthorizedCalls)
    }

    @Test
    fun oldStyleErrorEnvelopeToo() = runTest {
        respond("""{"error":"Something old"}""", code = 400)
        try {
            api.register("A", "a@example.com", "password1")
            fail("expected ApiException")
        } catch (e: ApiException) {
            assertEquals("Something old", e.message)
        }
    }

    @Test
    fun aRevokedSessionSignsOut() = runTest {
        respond("""{"message":"Invalid or expired session"}""", code = 401)
        try {
            api.openings()
            fail("expected UnauthorizedException")
        } catch (e: UnauthorizedException) {
            assertEquals(1, unauthorizedCalls)
        }
    }

    @Test
    fun aWrongPasswordDoesNotSignOut() = runTest {
        token = null
        respond("""{"message":"Invalid email or password"}""", code = 401)
        try {
            api.login("joe@example.com", "nope")
            fail("expected UnauthorizedException")
        } catch (e: UnauthorizedException) {
            assertEquals("Invalid email or password", e.message)
            assertEquals(0, unauthorizedCalls)
        }
    }

    @Test
    fun communitiesAreStampedWithTheirKind() = runTest {
        respond(Fixtures.text("alliances.json"))
        val alliances = api.communities(CommunityKind.Alliance)
        assertTrue(alliances.all { it.kind == CommunityKind.Alliance })
        assertEquals("/api/alliances", server.takeRequest().path)
    }

    @Test
    fun receiptBodyNamesCardsModeAndContext() = runTest {
        respond("""{"message":"Comment added"}""")
        api.addComment(
            "x1",
            NewComment(
                type = CommentType.Receipt,
                text = "  Thank you  ",
                cards = listOf(ValueCard(id = "c1", title = "Care")),
                franklMode = FranklMode.Experiential,
                context = "Time: 2 hours",
            ),
        )
        val request = server.takeRequest()
        assertEquals("/api/exchange/x1/comment", request.path)
        val body = LogoSphereJson.parseToJsonElement(request.body.readUtf8()) as JsonObject
        assertEquals("gratitude", body["type"]!!.jsonPrimitive.content)
        assertEquals("Thank you", body["text"]!!.jsonPrimitive.content)
        assertEquals("c1", body["card_ids"]!!.jsonArray.single().jsonPrimitive.content)
        assertEquals("experiential", body["frankl_mode"]!!.jsonPrimitive.content)
        assertEquals("Time: 2 hours", body["context"]!!.jsonPrimitive.content)
    }

    @Test
    fun searchSendsQueryAndKind() = runTest {
        respond(Fixtures.text("search_text.json"))
        api.search("garden", kind = "sphere")
        val url = server.takeRequest().requestUrl!!
        assertEquals("/api/search", url.encodedPath)
        assertEquals("garden", url.queryParameter("q"))
        assertEquals("sphere", url.queryParameter("kinds"))
    }

    /**
     * Android forbids network reads on the main thread. OkHttp delivers the response at the
     * headers; the body must then be read on the IO dispatcher, not on whatever thread called.
     */
    @Test
    fun bodiesAreReadOffTheCallersThread() {
        val readOn = java.util.Collections.synchronizedSet(mutableSetOf<String>())
        val recording = client.newBuilder().addNetworkInterceptor { chain ->
            val response = chain.proceed(chain.request())
            val body = response.body!!
            val source = object : okio.ForwardingSource(body.source()) {
                override fun read(sink: okio.Buffer, byteCount: Long): Long {
                    readOn += Thread.currentThread().name
                    return super.read(sink, byteCount)
                }
            }
            response.newBuilder()
                .body(object : okhttp3.ResponseBody() {
                    override fun contentType() = body.contentType()
                    override fun contentLength() = body.contentLength()
                    override fun source() = source.buffer()
                })
                .build()
        }.build()
        val base = server.url("/")
        val recordingApi = LogoSphereApi(recording, server = { base })
        respond(Fixtures.text("check_session.json"))
        @OptIn(kotlinx.coroutines.DelicateCoroutinesApi::class, kotlinx.coroutines.ExperimentalCoroutinesApi::class)
        val fakeMain = kotlinx.coroutines.newSingleThreadContext("fake-main")
        try {
            kotlinx.coroutines.runBlocking(fakeMain) { recordingApi.checkSession() }
        } finally {
            fakeMain.close()
        }
        assertTrue("the body was read", readOn.isNotEmpty())
        // Under test, coroutine debug mode suffixes thread names (" @coroutine#1"): match the prefix.
        assertTrue("the body was read on the caller's thread: $readOn", readOn.none { it.startsWith("fake-main") })
    }

    @Test
    fun likeSendsTheTargetState() = runTest {
        respond("""{"liked":true,"likes":3,"liked_by":[{"id":"u1","name":"A"}]}""")
        val result = api.likeOpening("o1", liked = true)
        assertTrue(result.liked)
        assertEquals(3, result.likes)
        val body = server.takeRequest().body.readUtf8()
        assertEquals("""{"liked":true}""", body)
    }
}
