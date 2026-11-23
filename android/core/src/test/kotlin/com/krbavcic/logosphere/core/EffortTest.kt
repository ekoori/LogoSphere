package com.krbavcic.logosphere.core

import com.krbavcic.logosphere.core.logic.Effort
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class EffortTest {
    @Test
    fun readsWhatWasTypedToTheQuarterHour() {
        assertEquals(2.5, Effort.parse(" 2.4 ")!!, 0.0)
        assertEquals(1.25, Effort.parse("1,3")!!, 0.0)
        assertEquals(100.0, Effort.parse("100")!!, 0.0)
        listOf("", "0", "0.1", "101", "lots", "-2", "NaN").forEach { assertNull(it, Effort.parse(it)) }
    }

    @Test
    fun saysItPlainly() {
        assertEquals("About 2 hours", Effort.text(2.0))
        assertEquals("About 1 hour", Effort.text(1.0))
        assertEquals("About 2.5 hours", Effort.text(2.5))
        assertEquals("About 45 minutes", Effort.text(0.75))
        assertEquals("1.25 h", Effort.text(1.25, short = true))
        assertEquals("30 min", Effort.text(0.5, short = true))
        assertNull(Effort.text(null))
        assertNull(Effort.text(0.0))
    }
}
