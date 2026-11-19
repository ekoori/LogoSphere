package com.krbavcic.logosphere.core

import com.krbavcic.logosphere.core.api.LogoSphereJson
import com.krbavcic.logosphere.core.logic.Parties
import com.krbavcic.logosphere.core.model.DemoStatus
import com.krbavcic.logosphere.core.model.Exchange
import com.krbavcic.logosphere.core.model.Opening
import com.krbavcic.logosphere.core.model.PublicUser
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** The demonstration's labels arrive as plain flags; older payloads without them still decode. */
class DemoFieldsTest {
    @Test
    fun openingsSayWhenTheyAreDemoAndWhoIsAPersona() {
        val o = LogoSphereJson.decodeFromString<Opening>(
            """{"service_id": "s1", "title": "Ladder", "is_demo": true, "provider_is_agent": true,
                "pending_acceptances": [{"accepter_id": "a1", "is_agent": true}]}""",
        )
        assertTrue(o.isDemo && o.providerIsAgent && o.pendingAcceptances.single().isAgent)
        val old = LogoSphereJson.decodeFromString<Opening>("""{"service_id": "s2", "title": "Old"}""")
        assertFalse(old.isDemo || old.providerIsAgent)
    }

    @Test
    fun exchangePartiesCarryThePersonaFlag() {
        val x = LogoSphereJson.decodeFromString<Exchange>(
            """{"exchange_id": "x1", "user_id": "me", "initiator_id": "me", "initiator_kind": "user",
                "other_user_id": "p1", "other_user_name": "Marie Kondo", "other_kind": "user",
                "is_demo": true, "initiator_is_agent": false, "other_is_agent": true}""",
        )
        assertTrue(x.isDemo)
        assertFalse(Parties.initiator(x, "me").isAgent)
        assertTrue(Parties.recipient(x, "me")!!.isAgent)
    }

    @Test
    fun theDemoInvitationDecodes() {
        val d = LogoSphereJson.decodeFromString<DemoStatus>(
            """{"spheres": [{"id": "s1", "name": "Riverside Commons", "joined": false, "member_count": 10}],
                "joined_any": false, "joined_all": false, "joined": []}""",
        )
        assertEquals("Riverside Commons", d.spheres.single().name)
        assertFalse(d.joinedAny)
        val person = LogoSphereJson.decodeFromString<PublicUser>("""{"user_id": "p1", "name": "Marie", "is_agent": true}""")
        assertTrue(person.isAgent)
    }
}
