package com.krbavcic.logosphere.core

import com.krbavcic.logosphere.core.api.BearerAuthInterceptor
import com.krbavcic.logosphere.core.api.LogoSphereApi
import com.krbavcic.logosphere.core.api.LogoSphereJson
import com.krbavcic.logosphere.core.logic.AppLink
import com.krbavcic.logosphere.core.logic.EventAnswer
import com.krbavcic.logosphere.core.logic.EventDraft
import com.krbavcic.logosphere.core.logic.Events
import com.krbavcic.logosphere.core.logic.Links
import com.krbavcic.logosphere.core.logic.Repeats
import com.krbavcic.logosphere.core.model.CommunityEvent
import com.krbavcic.logosphere.core.model.EventTime
import com.krbavcic.logosphere.core.model.ReportOf
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
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
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.util.Locale

class EventsTest {
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

    private fun sentBody(): JsonObject = LogoSphereJson.parseToJsonElement(server.takeRequest().body.readUtf8()).jsonObject

    private val paris = ZoneId.of("Europe/Paris")
    private val newYear = Instant.parse("2027-01-01T12:00:00Z")
    private val evening = EventTime("2027-03-25", "2027-03-25T18:00:00", "2027-03-25T20:00:00")

    @Test
    fun repeatingInWords() {
        fun said(repeats: Repeats, day: String) = Events.repeatText(repeats, LocalDate.parse(day))
        assertEquals("Every Thursday", said(Repeats.Weekly, "2027-03-25"))
        assertEquals("Every month on the 12th", said(Repeats.Monthly, "2027-03-12"))
        assertEquals("Every month on the 31st, or the month's last day", said(Repeats.Monthly, "2027-03-31"))
        assertEquals("Every month on the second Tuesday", said(Repeats.MonthlyWeekday, "2027-01-12"))
        assertEquals("Every month on the last Wednesday", said(Repeats.MonthlyWeekday, "2027-03-31"))
        assertEquals("Every week", Events.repeatText(Repeats.Weekly, null))
        assertEquals("1½ hours", Events.lengthText(90))
        assertEquals("1 hour 40 minutes", Events.lengthText(100))
        assertEquals("3 days", Events.lengthText(4320))
    }

    @Test
    fun timesAreOnTheEventsClock() {
        val here = Events.whenText(evening, "Europe/Paris", paris, newYear, Locale.UK)
        assertTrue(here.text, here.text.endsWith("25 Mar, 19:00–21:00"))
        assertNull(here.zoneNote)
        val away = Events.whenText(evening, "Europe/Paris", ZoneId.of("America/New_York"), newYear, Locale.UK)
        assertEquals(here.text, away.text)
        assertEquals("Europe/Paris time", away.zoneNote)
        assertNull(Events.whenText(evening, "Asia/Calcutta", ZoneId.of("Asia/Kolkata"), newYear, Locale.UK).zoneNote)
        assertFalse(Events.hasEnded(evening, Instant.parse("2027-03-25T19:59:00Z")))
        assertTrue(Events.hasEnded(evening, Instant.parse("2027-03-25T20:00:00Z")))
    }

    @Test
    fun theFormsProblems() {
        val draft = EventDraft(title = "Mending", day = "2027-03-25", clock = "19:00")
        assertNull(draft.problem)
        assertEquals("Give it a name.", draft.copy(title = " ").problem)
        assertEquals("Say which day and time it starts.", draft.copy(clock = null).problem)
        assertEquals("Its last date is before its first.", draft.copy(repeats = "weekly", until = "2027-03-01").problem)
        assertNull(draft.copy(until = "2027-03-01").problem)     // it doesn't repeat, so there's no last
    }

    @Test
    fun aDraftIsWhatIsSentAndComesBack() = runTest {
        server.enqueue(MockResponse().setBody("""{"id":"e"}"""))
        val draft = EventDraft(title = " Mending ", day = "2027-03-25", clock = "19:00", tz = "Europe/Paris")
        assertEquals("e", api.createEvent(draft, "g").id)
        val sent = sentBody()
        assertEquals("2027-03-25T19:00", sent["starts"]!!.jsonPrimitive.content)
        assertEquals("Mending", sent["title"]!!.jsonPrimitive.content)
        assertEquals("g", sent["host_id"]!!.jsonPrimitive.content)
        assertEquals(JsonNull, sent["until"])
        val event = CommunityEvent(id = "e", title = "Mending", starts = "2027-03-25T19:00", tz = "Europe/Paris", lengthMin = 120)
        assertEquals(draft.copy(title = "Mending"), EventDraft.of(event))
    }

    @Test
    fun takingAnAnswerBackSendsNull() = runTest {
        repeat(2) { server.enqueue(MockResponse().setBody("""{"id":"e"}""")) }
        api.replyEvent("e", "2027-03-25", EventAnswer.Cant)
        assertEquals("no", sentBody()["answer"]!!.jsonPrimitive.content)
        api.replyEvent("e", "2027-03-25", null)
        assertEquals(JsonNull, sentBody()["answer"])        // the server wants it said
    }

    @Test
    fun anEventsPageDecodes() = runTest {
        server.enqueue(
            MockResponse().setBody(
                """{"id":"e","title":"Mending","host":{"id":"g","kind":"alliance","name":"Fixers"},"starts":"2027-03-25T19:00",
                   "tz":"Europe/Paris","length_min":120,"repeats":"weekly","until":null,"cancelled":false,"can_manage":true,
                   "creator":{"id":"a","name":"Ada"},"point":null,"over":false,
                   "times":[{"day":"2027-03-25","starts_at":"2027-03-25T18:00:00","ends_at":"2027-03-25T20:00:00","skipped":false,
                             "going":1,"maybe":0,"my_answer":null,"people":[{"id":"b","name":"Ben","answer":"going"}]}]}""",
            ),
        )
        val event = api.event("e")
        assertEquals("Fixers", event.host?.name)
        assertEquals("Ben", event.times.single().people.single().name)
        assertEquals("1 going", Events.comingText(event.times.single()))
    }

    @Test
    fun announcementsAndInvitations() = runTest {
        server.enqueue(MockResponse().setBody("""{"can_announce":false,"announcements":[{"id":"w","text":"Key","at":"2027-03-25T10:00:00"}]}"""))
        assertEquals("Key", api.announcements("g").announcements.single().text)
        server.takeRequest()
        server.enqueue(MockResponse().setBody("""{"id":"h","path":"/invite#code","expires_at":"2027-04-08T10:00:00","most_uses":25,"group":null}"""))
        assertEquals("/invite#code", api.makeInvite(null).path)
        assertTrue(sentBody().isEmpty())
        assertTrue(api.webUrl("/invite#code").endsWith("/invite#code"))     // the code stays in the fragment
    }

    @Test
    fun linksAndReports() = runTest {
        assertEquals(AppLink.Event("e1"), Links.parse("/event?id=e1"))
        assertEquals(AppLink.Events, Links.parse("/events"))
        assertEquals(AppLink.Account, Links.parse("/settings#invitations"))
        server.enqueue(MockResponse().setBody("""{"message":"Thank you."}"""))
        api.report(ReportOf.announcement("w", groupId = "g"), "")
        assertEquals("g", sentBody()["group_id"]!!.jsonPrimitive.content)
    }
}
