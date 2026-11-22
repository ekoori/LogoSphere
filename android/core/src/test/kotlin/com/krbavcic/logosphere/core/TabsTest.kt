package com.krbavcic.logosphere.core

import com.krbavcic.logosphere.core.logic.Tabs
import org.junit.Assert.assertEquals
import org.junit.Test

class TabsTest {
    private val tabs = listOf("trail", "openings", "people", "governance", "charter")

    @Test
    fun opensOnOpeningsWhileTrailStaysFirst() {
        assertEquals(1, Tabs.indexOf(null, tabs))
        assertEquals(1, Tabs.indexOf("nonsense", tabs))
    }

    @Test
    fun aLinkWinsInEitherVocabulary() {
        assertEquals(0, Tabs.indexOf("trail", tabs))
        assertEquals(0, Tabs.indexOf("meaning_trail", tabs))
        assertEquals(2, Tabs.indexOf("members", tabs))
        assertEquals(3, Tabs.indexOf("governance", tabs))
    }
}
