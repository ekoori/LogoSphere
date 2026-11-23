package com.krbavcic.logosphere.core

import com.krbavcic.logosphere.core.api.BearerAuthInterceptor
import com.krbavcic.logosphere.core.api.LogoSphereApi
import com.krbavcic.logosphere.core.logic.OpeningsQuery
import kotlinx.coroutines.test.runTest
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test

class OpeningsPagingTest {
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

    @Test
    fun theFiltersAreTheServersToApply() {
        assertEquals(mapOf("limit" to "30"), OpeningsQuery().params())
        assertEquals(mapOf("limit" to "30", "type" to "need", "demo" to "demo", "km" to "5"),
            OpeningsQuery(type = 2, sphere = OpeningsQuery.DEMO, near = 5).params())
        assertEquals(mapOf("limit" to "30", "loans" to "1", "sphere" to "s1"), OpeningsQuery(type = 3, sphere = "s1").params())
    }

    @Test
    fun aPageAndWhereToCarryOn() = runTest {
        server.enqueue(MockResponse().setBody("""{"openings":[{"service_id":"o1","title":"Ladder"}],"next":"2026-11-23T10:00:00~o1"}"""))
        server.enqueue(MockResponse().setBody("""{"openings":[],"next":null}"""))
        val first = api.openingsPage(OpeningsQuery(type = 1))
        assertEquals(listOf("o1"), first.openings.map { it.id })
        assertEquals("2026-11-23T10:00:00~o1", first.next)
        assertNull(api.openingsPage(OpeningsQuery(type = 1), first.next).next)
        val asked = server.takeRequest().requestUrl!!
        assertEquals("30", asked.queryParameter("limit"))
        assertEquals("offer", asked.queryParameter("type"))
        assertNull(asked.queryParameter("before"))
        assertEquals("2026-11-23T10:00:00~o1", server.takeRequest().requestUrl!!.queryParameter("before"))
    }
}
