package com.krbavcic.logosphere.core

import com.krbavcic.logosphere.core.model.Community
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.Exchange
import com.krbavcic.logosphere.core.model.ExchangeDetail
import com.krbavcic.logosphere.core.model.LikeTarget
import com.krbavcic.logosphere.core.model.LoginResponse
import com.krbavcic.logosphere.core.model.NotificationInbox
import com.krbavcic.logosphere.core.model.Opening
import com.krbavcic.logosphere.core.model.PublicUser
import com.krbavcic.logosphere.core.model.SearchResults
import com.krbavcic.logosphere.core.model.SessionStatus
import com.krbavcic.logosphere.core.model.ValueCard
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Every recorded API response decodes into the app's models, with the fields screens rely on. */
class FixturesDecodeTest {
    @Test
    fun login() {
        val login = Fixtures.decode<LoginResponse>("login.json")
        assertEquals("00000000-0000-4000-8000-000000000000", login.sessionId)
        assertEquals("Joe Rogan", login.data.displayName)
        assertTrue(login.data.isPlatformAdmin)
    }

    @Test
    fun checkSession() {
        val session = Fixtures.decode<SessionStatus>("check_session.json")
        assertTrue(session.isActive)
        assertEquals(session.userId, session.userData?.userId)
    }

    @Test
    fun inactiveSession() {
        val session = com.krbavcic.logosphere.core.api.LogoSphereJson
            .decodeFromString<SessionStatus>("""{"status":"inactive","user_id":null}""")
        assertFalse(session.isActive)
    }

    @Test
    fun meaningTrail() {
        val trail = Fixtures.decode<List<Exchange>>("meaning_trail.json")
        assertEquals(5, trail.size)
        val solar = trail.first { it.id == "10000000-0000-0000-0000-000000000005" }
        assertEquals("Neighbourhood Solar Microgrid", solar.projectName)
        assertEquals("user", solar.initiatorKind)
        assertNotNull(solar.likes["exchange"])
        assertEquals(0, solar.likesFor(LikeTarget.Receipt).count)
        assertTrue(trail.any { it.receipt != null })
        assertTrue(trail.any { it.acknowledgement != null && it.acknowledgementAuthorName != null })
    }

    @Test
    fun othersTrail() {
        val trail = Fixtures.decode<List<Exchange>>("meaning_trail_other.json")
        assertTrue(trail.isNotEmpty())
    }

    @Test
    fun exchangeDetail() {
        val detail = Fixtures.decode<ExchangeDetail>("exchange_detail.json")
        assertTrue(detail.isInitiator)
        assertEquals("Initiated", detail.exchange.status)
        assertEquals(0, detail.exchange.receiptPhotoCount)
        assertFalse(detail.exchange.isFinished)
        assertEquals("Steve Wozniak", detail.exchange.otherUserName)
    }

    @Test
    fun openings() {
        val openings = Fixtures.decode<List<Opening>>("openings.json")
        assertEquals(47, openings.size)
        assertTrue(openings.any { it.isPerpetual && it.activity != null })
        assertTrue(openings.any { !it.isOffer })
        val gpu = openings.first { it.id == "05b5666a-b78f-5af7-ae5c-718922e0deba" }
        assertEquals("Earthsong Gardens", gpu.sphereName)
        assertEquals("Morgan Freeman", gpu.provider)
    }

    @Test
    fun openingDetail() {
        val opening = Fixtures.decode<Opening>("opening_detail.json")
        assertTrue(opening.exchanges.isEmpty())
        assertTrue(opening.isCurrent)
        assertEquals(1, opening.version)
    }

    @Test
    fun communities() {
        val spheres = Fixtures.decode<List<Community>>("spheres.json").map { it.copy(kind = CommunityKind.Sphere) }
        val alliances = Fixtures.decode<List<Community>>("alliances.json").map { it.copy(kind = CommunityKind.Alliance) }
        val projects = Fixtures.decode<List<Community>>("projects.json").map { it.copy(kind = CommunityKind.Project) }
        assertEquals(3, spheres.size)
        assertEquals(3, alliances.size)
        assertEquals(4, projects.size)

        val ai = spheres.first { it.name == "AI Commons" }
        assertEquals("22222222-2222-2222-2222-222222222222", ai.id)
        assertNull(ai.parentSphereId)

        // An alliance's sphere_id is its parent, not its own id.
        val repair = alliances.first { it.name.startsWith("Repair") }
        assertEquals("aaaaaaaa-0000-0000-0000-000000000001", repair.id)
        assertEquals("11111111-1111-1111-1111-111111111111", repair.parentSphereId)

        val solar = projects.first { it.name == "Neighbourhood Solar Microgrid" }
        assertEquals("bbbbbbbb-0000-0000-0000-000000000002", solar.id)
        assertEquals("manager", solar.members.first { it.name == "Joe Rogan" }.role)
        assertTrue(solar.valueCards.isNotEmpty())
    }

    @Test
    fun sphereDetail() {
        val sphere = Fixtures.decode<Community>("sphere_detail.json").copy(kind = CommunityKind.Sphere)
        assertEquals("Riverside Commons", sphere.name)
        assertEquals(1, sphere.allianceList.size)
        assertEquals(2, sphere.projectList.size)
        assertTrue(sphere.canManage)
    }

    @Test
    fun allianceAndProjectDetail() {
        val alliance = Fixtures.decode<Community>("alliance_detail.json").copy(kind = CommunityKind.Alliance)
        val project = Fixtures.decode<Community>("project_detail.json").copy(kind = CommunityKind.Project)
        assertEquals("aaaaaaaa-0000-0000-0000-000000000001", alliance.id)
        assertEquals("bbbbbbbb-0000-0000-0000-000000000002", project.id)
    }

    @Test
    fun publicUser() {
        val user = Fixtures.decode<PublicUser>("public_user.json")
        assertEquals("Steve Wozniak", user.displayName)
        assertFalse(user.isFollowing)
    }

    @Test
    fun valueCards() {
        val cards = Fixtures.decode<List<ValueCard>>("value_cards.json")
        assertTrue(cards.isNotEmpty())
        assertTrue(cards.all { it.title.isNotBlank() && it.id != null })
    }

    @Test
    fun notifications() {
        val inbox = Fixtures.decode<NotificationInbox>("notifications.json")
        assertEquals(50, inbox.notifications.size)
        assertEquals(inbox.notifications.count { !it.isRead }, inbox.unreadCount)
        assertTrue(inbox.notifications.all { it.createdAt.isNotBlank() })
    }

    @Test
    fun search() {
        val text = Fixtures.decode<SearchResults>("search_text.json")
        assertEquals(setOf("sphere", "alliance", "project", "opening", "card"), text.groups.map { it.kind }.toSet())
        assertNotNull(text.groups.first { it.kind == "card" }.items.first().ownerName)

        val near = Fixtures.decode<SearchResults>("search_vicinity.json")
        assertTrue(near.groups.flatMap { it.items }.all { it.why.isNotEmpty() })
    }
}
