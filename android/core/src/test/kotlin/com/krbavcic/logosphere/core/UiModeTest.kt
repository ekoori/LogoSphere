package com.krbavcic.logosphere.core

import com.krbavcic.logosphere.core.api.LogoSphereApi
import com.krbavcic.logosphere.core.api.LogoSphereJson
import com.krbavcic.logosphere.core.logic.ShownTabs
import com.krbavcic.logosphere.core.logic.UiMode
import com.krbavcic.logosphere.core.model.SessionStatus
import kotlinx.coroutines.test.runTest
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Assert.assertEquals
import org.junit.Test

class UiModeTest {
    @Test
    fun takesTheAccountAtItsWordAndSilenceAsAdvanced() {
        fun modeIn(data: String) = LogoSphereJson
            .decodeFromString<SessionStatus>("""{"status":"active","user_id":"u","user_data":{"user_id":"u"$data}}""")
            .userData?.mode

        assertEquals(UiMode.Simple, modeIn(""","ui_mode":"simple""""))
        assertEquals(UiMode.Advanced, modeIn(""","ui_mode":"advanced""""))
        assertEquals(UiMode.Advanced, modeIn(""","ui_mode":null"""))
        assertEquals(UiMode.Advanced, modeIn(""))
    }

    @Test
    fun simpleLeavesOutGovernanceUnlessALinkOpenedIt() {
        val all = listOf("trail", "openings", "governance", "charter")
        val extra = setOf("governance")
        assertEquals(all, ShownTabs.of(all, extra, simple = false, open = "trail"))
        assertEquals(listOf("trail", "openings", "charter"), ShownTabs.of(all, extra, simple = true, open = "openings"))
        assertEquals(all, ShownTabs.of(all, extra, simple = true, open = "governance"))
    }

    @Test
    fun savesTheChoice() = runTest {
        val server = MockWebServer()
        server.start()
        try {
            server.enqueue(MockResponse().setBody("""{"ui_mode":"simple"}"""))
            val base = server.url("/")
            LogoSphereApi(OkHttpClient(), server = { base }).setUiMode(UiMode.Simple)
            val request = server.takeRequest()
            assertEquals("/api/account/preferences", request.path)
            assertEquals("""{"ui_mode":"simple"}""", request.body.readUtf8())
        } finally {
            server.shutdown()
        }
    }
}
