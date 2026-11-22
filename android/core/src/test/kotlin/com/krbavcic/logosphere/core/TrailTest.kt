package com.krbavcic.logosphere.core

import com.krbavcic.logosphere.core.api.LogoSphereJson
import com.krbavcic.logosphere.core.logic.AppLink
import com.krbavcic.logosphere.core.logic.Links
import com.krbavcic.logosphere.core.model.MeaningTrail
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TrailTest {
    private val json = """
        {"trail_id":"t","kind":"user","name":"Ana","can_acknowledge":true,"can_highlight":false,"entries":[
          {"type":"acknowledgements","id":"a1","folded":true,"items":[
            {"ack_id":"a2","trail_id":"t","author_id":"b","author_name":"Ben","text":"Thanks","highlighted":true,"shown":true,
             "likes":{"count":1,"liked":true,"own":false,"by":[{"id":"c","name":"Cy"}]},"can_remove":false,"cards":[]},
            {"ack_id":"a1","trail_id":"t","author_id":null,"text":"Older","shown":false,
             "likes":{"count":0,"liked":false,"own":false,"by":[]}}]},
          {"type":"exchange","id":"x","exchange":{"exchange_id":"x","exchange_description":"Pump repaired"}}]}
    """.trimIndent()

    @Test
    fun decodesTheTimelineInOrder() {
        val trail = LogoSphereJson.decodeFromString<MeaningTrail>(json)
        assertEquals(listOf("acknowledgements", "exchange"), trail.entries.map { it.type })
        val (newer, older) = trail.entries[0].items
        assertTrue(newer.highlighted && newer.shown && newer.likes.liked)
        assertFalse(older.shown)
        assertEquals(listOf("x"), trail.exchanges.map { it.id })
    }

    @Test
    fun changingAnExchangeLeavesTheRunsAlone() {
        val trail = LogoSphereJson.decodeFromString<MeaningTrail>(json)
        val changed = trail.mapExchanges { it.copy(title = "New") }
        assertEquals(trail.entries[0], changed.entries[0])
        assertEquals("New", changed.exchanges[0].title)
    }

    @Test
    fun aNotificationOpensThePersonsTrail() {
        assertEquals(AppLink.Person("p1", "trail"), Links.parse("/user?id=p1&tab=trail"))
    }
}
