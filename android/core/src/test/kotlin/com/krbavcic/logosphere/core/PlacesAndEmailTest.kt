package com.krbavcic.logosphere.core

import com.krbavcic.logosphere.core.api.BearerAuthInterceptor
import com.krbavcic.logosphere.core.api.LogoSphereApi
import com.krbavcic.logosphere.core.api.LogoSphereJson
import com.krbavcic.logosphere.core.logic.AppLink
import com.krbavcic.logosphere.core.logic.Links
import com.krbavcic.logosphere.core.logic.PinPrecision
import com.krbavcic.logosphere.core.logic.PlaceDraft
import com.krbavcic.logosphere.core.logic.Places
import com.krbavcic.logosphere.core.model.EmailSettings
import com.krbavcic.logosphere.core.model.FoundPlace
import com.krbavcic.logosphere.core.model.Opening
import com.krbavcic.logosphere.core.model.Place
import com.krbavcic.logosphere.core.model.PlaceSettings
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class PlacesAndEmailTest {
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

    private fun sent() = LogoSphereJson.parseToJsonElement(server.takeRequest().body.readUtf8()).jsonObject

    private val pin = Place("By the pond", 64.146582, -21.942635, "1km", fresh = true)
    private val town = Place("Bigton", 64.1355, -21.8954, "town")

    // ── Rules ───────────────────────────────────────────────────────────────

    /** The site sent exactly this for the same spot (and the server keeps it). */
    @Test
    fun roundsIntoTheSameSquareAsTheSite() {
        val at = Places.coarsened(64.146582, -21.942635, 1.0)
        assertEquals(64.143909, at.lat, 1e-9)
        assertEquals(-21.939994, at.lon, 1e-9)
        assertEquals(at, Places.coarsened(at.lat, at.lon, 1.0))
    }

    @Test
    fun onlyExactLeavesThePhoneExact() {
        val rounded = Places.payload(pin)!!.jsonObject
        assertEquals("64.143909", rounded["lat"]!!.jsonPrimitive.content)
        assertEquals("1km", rounded["precision"]!!.jsonPrimitive.content)
        assertNull(rounded["fresh"])
        val exact = Places.payload(pin.copy(precision = "exact"))!!.jsonObject
        assertEquals("64.146582", exact["lat"]!!.jsonPrimitive.content)
    }

    @Test
    fun wordsAloneNoneAndASearchedPlace() {
        assertEquals("The hills", Places.payload(Place(" The hills "))!!.jsonObject["label"]!!.jsonPrimitive.content)
        assertEquals(JsonNull, Places.payload(Place("  ")))
        assertEquals(JsonNull, Places.payload(null))
        assertNull(Places.payload(town)) // stored earlier: can't be sent again, and hasn't changed
        val found = Places.found(FoundPlace(7, "Bigton", "Bigton, Exampleland", "town", 1.0, 2.0))
        assertEquals("7", Places.payload(found)!!.jsonObject["id"]!!.jsonPrimitive.content)
    }

    @Test
    fun typingKeepsAPinAndLetsGoOfATown() {
        assertEquals(pin.copy(label = "By the bridge"), Places.withWords(pin, "By the bridge"))
        assertEquals(Place("Smallton"), Places.withWords(town, "Smallton"))
        assertEquals(Places.LABEL_MAX, Places.withWords(null, "x".repeat(500)).label!!.length)
    }

    @Test
    fun aDraftSendsOnlyWhatChanged() {
        val stored = PlaceDraft.of(PlaceSettings(town, findable = false), person = true)
        assertFalse(stored.changed)
        val switched = stored.copy(findableChosen = true)
        assertTrue(switched.changed)
        assertNull(switched.body()["place"]) // the switch alone leaves the place
        assertEquals("true", switched.body()["findable"]!!.jsonPrimitive.content)

        val gone = switched.copy(place = null)
        assertEquals(JsonNull, gone.body()["place"])
        assertFalse(gone.findable) // nothing to be found by

        assertNotNull(stored.copy(place = pin.copy(label = " ")).problem)
        assertNull(PlaceDraft.of(PlaceSettings(town)).problem)
    }

    @Test
    fun finerIsFinerAndCountriesMeasureNothing() {
        assertTrue(PinPrecision.Exact.isFinerThan(PinPrecision.Km1))
        assertFalse(PinPrecision.Km10.isFinerThan(PinPrecision.Km5))
        assertTrue(PinPrecision.Km1.needsFineLocation)
        assertFalse(PinPrecision.Km5.needsFineLocation)
        assertFalse(Places.canMeasure(town.copy(precision = "country")))
        assertEquals("On the map, to about 1 km", Places.linkedTo(pin))
    }

    @Test
    fun openingsSayWhere() {
        val o = LogoSphereJson.decodeFromString<Opening>(
            """{"service_id":"s1","location":"Grandi","distance":{"km":5,"text":"Within 5 km"},"point":null}""",
        )
        assertEquals(5, o.distance?.km)
        assertEquals("Grandi", o.location)
        assertNull(o.point)
    }

    @Test
    fun linksToNearbyAndEmailSettings() {
        assertEquals(AppLink.Nearby, Links.parse("/nearby"))
        assertEquals(AppLink.Account, Links.parse("/settings#email"))
        assertEquals(AppLink.EditProfile, Links.parse("/settings#place"))
    }

    // ── Requests ────────────────────────────────────────────────────────────

    @Test
    fun searchingKeepsWordsOutOfTheUrl() = runTest {
        respond("""{"available":true,"results":[{"id":1,"label":"Bigton","precision":"town","lat":1,"lon":2}]}""")
        assertEquals("Bigton", api.searchPlaces("big").results.single().label)
        val request = server.takeRequest()
        assertEquals("/api/places/search", request.path)
        assertTrue(request.body.readUtf8().contains("\"q\":\"big\""))
    }

    @Test
    fun savingAnOpeningsPlaceCanMakeANewVersion() = runTest {
        respond("""{"id":"v2","place":{"label":"The pier"}}""")
        val saved = api.savePlace(Places.OPENINGS, "v1", PlaceDraft(place = Place("The pier")))
        assertEquals("v2", saved.id)
        assertEquals("The pier", sent()["place"]!!.jsonObject["label"]!!.jsonPrimitive.content)
    }

    @Test
    fun joiningByEmailSendsNoPassword() = runTest {
        respond("""{"reg_success":true,"confirm_email":true}""")
        assertTrue(api.register("Sam", "sam@example.com").confirmEmail)
        assertEquals(setOf("name", "email"), sent().keys)
    }

    @Test
    fun personasOnlyWidenTheOtherTopics() {
        assertFalse(EmailSettings().mayToggle("personas"))
        assertTrue(EmailSettings(topics = listOf("thanks")).mayToggle("personas"))
        assertTrue(EmailSettings(topics = listOf("personas")).mayToggle("personas")) // to switch it off
        assertEquals(emptyList<String>(), EmailSettings(topics = listOf("thanks")).toggled("thanks"))
    }
}
