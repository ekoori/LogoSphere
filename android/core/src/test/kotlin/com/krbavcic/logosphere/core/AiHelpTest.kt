package com.krbavcic.logosphere.core

import com.krbavcic.logosphere.core.api.LogoSphereApi
import com.krbavcic.logosphere.core.api.LogoSphereJson
import com.krbavcic.logosphere.core.model.AiHelpStatus
import com.krbavcic.logosphere.core.model.NewOpening
import com.krbavcic.logosphere.core.model.Opening
import com.krbavcic.logosphere.core.model.SuggestedCard
import com.krbavcic.logosphere.core.model.ValueCardDraft
import kotlinx.coroutines.test.runTest
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class AiHelpTest {
    private lateinit var server: MockWebServer
    private lateinit var api: LogoSphereApi

    @Before
    fun setUp() {
        server = MockWebServer()
        server.start()
        val base = server.url("/")
        api = LogoSphereApi(OkHttpClient(), server = { base })
    }

    @After
    fun tearDown() {
        server.shutdown()
    }

    private val typed = ValueCardDraft(title = "Mending", looksLike = "Darning\n Asking", driftLooksLike = "Buying new")

    @Test
    fun offUntilTheServerSaysOn() {
        assertFalse(LogoSphereJson.decodeFromString<AiHelpStatus>("{}").pictures.on)
        val status = LogoSphereJson.decodeFromString<AiHelpStatus>("""{"pictures":{"on":true,"left":4}}""")
        assertTrue(status.pictures.on)
        assertEquals(4, status.pictures.left)
        assertFalse(status.valueCards.on)
    }

    @Test
    fun neverWipesWhatWasTyped() {
        val next = SuggestedCard(careAbout = "I care about mending.").into(typed, brief = false)
        assertEquals(typed.copy(careAbout = "I care about mending."), next)
    }

    @Test
    fun changesNothingHiddenInSimple() {
        val suggested = SuggestedCard(title = "Mend first", looksLike = listOf("x"), neverDo = "Bin it", franklMode = "attitudinal")
        assertEquals(typed.copy(title = "Mend first"), suggested.into(typed, brief = true))
        val full = suggested.into(typed, brief = false)
        assertEquals("x", full.looksLike)
        assertEquals("attitudinal", full.franklMode)
    }

    @Test
    fun sendsOnlyWhatShows() = runTest {
        repeat(2) { server.enqueue(MockResponse().setBody("""{"draft":{"title":"Mend"},"question":"Why?","left":3}""")) }
        assertEquals("Why?", api.draftCard("old socks", typed, brief = true, group = false).question)
        assertEquals(
            """{"notes":"old socks","draft":{"title":"Mending"},"brief":true,"group":false}""",
            server.takeRequest().body.readUtf8(),
        )
        api.draftCard("", typed, brief = false, group = true)
        assertEquals(
            """{"notes":"","draft":{"title":"Mending","looks_like":["Darning","Asking"],"drift_looks_like":"Buying new"},""" +
                """"brief":false,"group":true}""",
            server.takeRequest().body.readUtf8(),
        )
    }

    @Test
    fun keepsADrawnPictureByteForByte() = runTest {
        server.enqueue(MockResponse().setBody("""{"image":"/9gAAQI=","content_type":"image/jpeg","left":2}"""))
        val picture = api.drawPicture("opening", "Loppers", "To lend", "autumn")
        assertArrayEquals(byteArrayOf(0xFF.toByte(), 0xD8.toByte(), 0, 1, 2), picture.bytes)
        assertEquals(
            """{"purpose":"opening","title":"Loppers","description":"To lend","hint":"autumn"}""",
            server.takeRequest().body.readUtf8(),
        )
    }

    @Test
    fun aNewOpeningTellsItsIdForItsPicture() = runTest {
        server.enqueue(MockResponse().setResponseCode(201).setBody("""{"service_id":"s-1","message":"created"}"""))
        assertEquals("s-1", api.createOpening(NewOpening(type = "offer", title = "Loppers", description = "", cadence = "single", sphereId = null, sphereName = null, projectName = null)))
    }

    @Test
    fun picturesSayWhenTheyAreAi() {
        assertTrue(LogoSphereJson.decodeFromString<Opening>("""{"service_id":"s","image_is_ai":true}""").imageIsAi)
    }
}
