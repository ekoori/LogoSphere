package com.krbavcic.logosphere.core

import com.krbavcic.logosphere.core.logic.AppLink
import com.krbavcic.logosphere.core.logic.Dates
import com.krbavcic.logosphere.core.logic.InfoPage
import com.krbavcic.logosphere.core.logic.Links
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.NotificationInbox
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.Instant
import java.time.ZoneOffset
import java.util.Locale

class LinksTest {
    @Test
    fun webRoutesMapToScreens() {
        assertEquals(AppLink.Opening("o1"), Links.parse("/opening?id=o1"))
        assertEquals(AppLink.Exchange("x1"), Links.parse("/exchange?id=x1"))
        assertEquals(AppLink.Person("u1"), Links.parse("/user?id=u1"))
        assertEquals(AppLink.Community(CommunityKind.Sphere, "s1"), Links.parse("/sphere?id=s1"))
        assertEquals(AppLink.Community(CommunityKind.Alliance, "a1", tab = "governance"), Links.parse("/alliance?tab=governance&id=a1"))
        assertEquals(AppLink.Community(CommunityKind.Project, "p1"), Links.parse("/project?id=p1#top"))
        assertEquals(AppLink.Me, Links.parse("/profile"))
        // What used to open on the web now has screens of its own.
        assertEquals(AppLink.Manage(CommunityKind.Alliance, "a1"), Links.parse("/alliance-management?id=a1"))
        assertEquals(AppLink.EditProfile, Links.parse("/settings"))
        assertEquals(AppLink.Admin, Links.parse("/admin?tab=users"))
        assertEquals(AppLink.Info(InfoPage.HowItWorks), Links.parse("/how-it-works"))
        assertEquals(AppLink.Info(InfoPage.Terms), Links.parse("/tos"))
    }

    @Test
    fun anythingElseOpensOnTheWeb() {
        assertEquals(AppLink.Web("/sphere?name=Riverside%20Commons"), Links.parse("/sphere?name=Riverside%20Commons"))
        assertEquals(AppLink.Web("/alliance-management"), Links.parse("/alliance-management"))
        assertEquals(AppLink.Web("/somewhere-new"), Links.parse("/somewhere-new"))
        assertNull(Links.parse(""))
        assertNull(Links.parse(null))
    }

    @Test
    fun everyRecordedNotificationLinkResolves() {
        val inbox = Fixtures.decode<NotificationInbox>("notifications.json")
        val links = inbox.notifications.mapNotNull { Links.parse(it.link) }
        assertTrue(links.isNotEmpty())
        assertTrue(links.none { it is AppLink.Web })
    }
}

class DatesTest {
    @Test
    fun parsesBothServerFormats() {
        val expected = Instant.parse("2026-06-02T10:00:00Z")
        assertEquals(expected, Dates.parse("2026-06-02T10:00:00"))
        assertEquals(expected, Dates.parse("Tue, 02 Jun 2026 10:00:00 GMT"))
        assertEquals(Instant.parse("2026-07-05T04:55:02.777Z"), Dates.parse("2026-07-05T04:55:02.777000"))
        assertEquals(expected, Dates.parse("2026-06-02T12:00:00+02:00"))
        assertNull(Dates.parse("not a date"))
        assertNull(Dates.parse(null))
    }

    @Test
    fun formatsDaysAndAges() {
        assertEquals("Jun 2, 2026", Dates.day("2026-06-02T10:00:00", ZoneOffset.UTC, Locale.US))
        assertEquals("", Dates.day(null, ZoneOffset.UTC, Locale.US))
        val now = Instant.parse("2026-06-02T12:00:00Z")
        assertEquals("just now", Dates.ago("2026-06-02T11:59:40", now, ZoneOffset.UTC, Locale.US))
        assertEquals("5m ago", Dates.ago("2026-06-02T11:55:00", now, ZoneOffset.UTC, Locale.US))
        assertEquals("2h ago", Dates.ago("2026-06-02T10:00:00", now, ZoneOffset.UTC, Locale.US))
        assertEquals("3d ago", Dates.ago("2026-05-30T12:00:00", now, ZoneOffset.UTC, Locale.US))
        assertEquals("May 1, 2026", Dates.ago("2026-05-01T12:00:00", now, ZoneOffset.UTC, Locale.US))
    }
}
