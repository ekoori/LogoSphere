package com.krbavcic.logosphere.core

import com.krbavcic.logosphere.core.api.BearerAuthInterceptor
import com.krbavcic.logosphere.core.api.LogoSphereApi
import com.krbavcic.logosphere.core.api.LogoSphereJson
import com.krbavcic.logosphere.core.logic.AppLink
import com.krbavcic.logosphere.core.logic.Links
import com.krbavcic.logosphere.core.logic.Messaging
import com.krbavcic.logosphere.core.model.DirectMessage
import com.krbavcic.logosphere.core.model.MessageAbout
import com.krbavcic.logosphere.core.model.Exchange
import com.krbavcic.logosphere.core.model.Opening
import com.krbavcic.logosphere.core.model.ReportOf
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test

class MessagingTest {
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

    private fun respond(body: String) = server.enqueue(MockResponse().setBody(body))

    private fun message(id: String, second: Int, mine: Boolean = false) =
        DirectMessage(id, id, "2026-11-23T10:00:0$second", mine)

    @Test
    fun pagesAndPollsMergeOldestFirstEachOnce() {
        val merged = Messaging.merge(
            listOf(message("b", 2), message("c", 3)),
            listOf(message("a", 1), message("c", 3).copy(text = "again"), message("d", 4, mine = true)),
        )
        assertEquals(listOf("a", "b", "c", "d"), merged.map { it.id })
        assertEquals("again", merged[2].text)
        assertEquals("c", Messaging.lastOfTheirs(merged))
        assertNull(Messaging.lastOfTheirs(listOf(message("d", 4, mine = true))))
    }

    @Test
    fun whoToWriteToAboutAnOpening() {
        val opening = Opening(id = "o", contactId = "ada")
        assertEquals("ada", Messaging.openingContact(opening, "ben"))
        assertNull(Messaging.openingContact(opening, "ada"))
        assertNull(Messaging.openingContact(opening.copy(providerIsAgent = true), "ben")) // personas don't read messages
    }

    @Test
    fun theHumanOnTheOtherSideOfAnExchange() {
        val x = Exchange(
            id = "x", initiatorId = "ada", otherUserId = "tools", otherKind = "alliance", recipientActingUserId = "ben",
        )
        assertEquals("ben", Messaging.otherSide(x, "ada", isInitiator = true, isOther = false))
        assertEquals("ada", Messaging.otherSide(x, "ben", isInitiator = false, isOther = true))
        assertNull(Messaging.otherSide(x, "cy", isInitiator = false, isOther = false))
        assertNull(Messaging.otherSide(x.copy(otherIsAgent = true), "ada", isInitiator = true, isOther = false))
        assertNull(Messaging.otherSide(x.copy(recipientActingUserId = null), "ada", isInitiator = true, isOther = false))
    }

    @Test
    fun notificationLinksOpenTheConversation() {
        assertEquals(AppLink.Messages("p1"), Links.parse("/messages?with=p1"))
        assertEquals(AppLink.Messages("p1", "o1"), Links.parse("/messages?with=p1&opening=o1"))
        assertEquals(AppLink.Messages("p1", about = "sphere:s1"), Links.parse("/messages?with=p1&about=sphere:s1"))
        assertEquals(AppLink.Messages(), Links.parse("/messages"))
    }

    @Test
    fun sendingNamesWhatItsAboutOnlyWhenGiven() = runTest {
        respond("""{"sent":{"id":"m1","text":"Hi","at":"2026-11-23T10:00:00","mine":true,""" +
            """"about":{"kind":"sphere","id":"s1","title":"Creekside","link":"/sphere?id=s1"},"opening":null}}""")
        respond("""{"sent":{"id":"m2","text":"Again","at":"2026-11-23T10:00:01","mine":true}}""")
        val sent = api.sendMessage("p", " Hi ", MessageAbout("s1", "Creekside", kind = "sphere"))
        assertEquals("/sphere?id=s1", sent.subject?.target)
        api.sendMessage("p", "Again", null)
        val first = LogoSphereJson.parseToJsonElement(server.takeRequest().body.readUtf8()).jsonObject
        assertEquals("Hi", first["text"]!!.jsonPrimitive.content)
        assertEquals("sphere", first["about"]!!.jsonObject["kind"]!!.jsonPrimitive.content)
        assertEquals("s1", first["about"]!!.jsonObject["id"]!!.jsonPrimitive.content)
        assertEquals(setOf("text"), LogoSphereJson.parseToJsonElement(server.takeRequest().body.readUtf8()).jsonObject.keys)
    }

    @Test
    fun olderMessagesNameAnOpening() {
        val old = LogoSphereJson.decodeFromString<DirectMessage>("""{"id":"m","opening":{"id":"o1","title":"Ladder"}}""")
        assertEquals("/opening?id=o1", old.subject?.target)
        assertEquals("opening:o1", old.subject?.key)
    }

    @Test
    fun aReportNamesTheThingNeverItsWords() = runTest {
        respond("""{"message":"Thank you."}""")
        assertEquals("Thank you.", api.report(ReportOf.message("m1", with = "p"), " rude "))
        val sent = LogoSphereJson.parseToJsonElement(server.takeRequest().body.readUtf8()).jsonObject
        assertEquals(setOf("kind", "id", "note", "person_id"), sent.keys)
        assertEquals("rude", sent["note"]!!.jsonPrimitive.content)
    }
}
