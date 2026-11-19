package com.krbavcic.logosphere.core

import com.krbavcic.logosphere.core.logic.ExchangeRules
import com.krbavcic.logosphere.core.logic.Membership
import com.krbavcic.logosphere.core.logic.OpeningRules
import com.krbavcic.logosphere.core.logic.Parties
import com.krbavcic.logosphere.core.model.Acceptance
import com.krbavcic.logosphere.core.model.Community
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.Exchange
import com.krbavcic.logosphere.core.model.ExchangeDetail
import com.krbavcic.logosphere.core.model.Member
import com.krbavcic.logosphere.core.model.Opening
import com.krbavcic.logosphere.core.model.OpeningActivity
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

private const val ME = "me"
private const val THEM = "them"

class OpeningRulesTest {
    private fun opening(
        status: String = "Posted",
        cadence: String = "single",
        providerId: String = THEM,
        isProvider: Boolean = false,
        canManage: Boolean = false,
        mine: Acceptance? = null,
        isCurrent: Boolean = true,
        sphereId: String? = null,
    ) = Opening(
        id = "o1", status = status, cadence = cadence, providerId = providerId, isProvider = isProvider,
        canManage = canManage, myAcceptance = mine, isCurrent = isCurrent, sphereId = sphereId,
        createdAt = "2026-06-25T09:19:00",
    )

    @Test
    fun othersOpenOpeningCanBeAccepted() {
        assertTrue(OpeningRules.canAccept(opening(), ME))
        assertTrue(OpeningRules.canAccept(opening(status = "Open"), ME))
        // A one-time opening stays open to everyone until the provider confirms someone.
        assertTrue(OpeningRules.canAccept(opening(status = "Accepted"), ME))
    }

    @Test
    fun cannotAcceptOwnTwiceOrClosed() {
        assertFalse(OpeningRules.canAccept(opening(providerId = ME), ME))
        assertFalse(OpeningRules.canAccept(opening(isProvider = true), ME))
        assertFalse(OpeningRules.canAccept(opening(mine = Acceptance(accepterId = ME)), ME))
        assertFalse(OpeningRules.canAccept(opening(status = "Cancelled"), ME))
        assertFalse(OpeningRules.canAccept(opening(status = "Completed"), ME))
        assertFalse(OpeningRules.canAccept(opening(status = "In Progress"), ME))
        assertFalse(OpeningRules.canAccept(opening(isCurrent = false), ME))
        assertFalse(OpeningRules.canAccept(opening(), null))
    }

    @Test
    fun perpetualStaysOpenWhileInProgress() {
        assertTrue(OpeningRules.canAccept(opening(status = "In Progress", cadence = "perpetual"), ME))
    }

    @Test
    fun platformAdminCanManageButStillAccept() {
        val o = opening(canManage = true)
        assertTrue(OpeningRules.mayManage(o, ME))
        assertTrue(OpeningRules.canAccept(o, ME))
    }

    @Test
    fun aPendingAcceptanceCanBeTakenBack() {
        assertTrue(OpeningRules.canTakeBack(opening(status = "Accepted", mine = Acceptance(accepterId = ME, status = "pending"))))
        assertFalse(OpeningRules.canTakeBack(opening(mine = Acceptance(accepterId = ME, status = "confirmed"))))
        assertFalse(OpeningRules.canTakeBack(opening(status = "Cancelled", mine = Acceptance(accepterId = ME, status = "pending"))))
        assertFalse(OpeningRules.canTakeBack(opening()))
    }

    @Test
    fun withdrawFollowsTheServerGuard() {
        assertTrue(OpeningRules.canWithdraw(opening(providerId = ME), ME))
        assertTrue(OpeningRules.canWithdraw(opening(providerId = ME, status = "Accepted"), ME))
        assertFalse(OpeningRules.canWithdraw(opening(providerId = ME, status = "In Progress"), ME))
        assertTrue(OpeningRules.canWithdraw(opening(providerId = ME, status = "In Progress", cadence = "perpetual"), ME))
        assertFalse(OpeningRules.canWithdraw(opening(providerId = ME, status = "Cancelled"), ME))
        assertFalse(OpeningRules.canWithdraw(opening(providerId = ME, isCurrent = false), ME))
        assertFalse(OpeningRules.canWithdraw(opening(), ME))
    }

    @Test
    fun singleProgressFollowsStatus() {
        val p = OpeningRules.progress(opening(status = "In Progress").copy(acceptedAt = "2026-07-01T10:00:00"))
        assertEquals(2, p.current)
        assertEquals("In Progress", p.currentLabel)
        assertEquals("2026-06-25T09:19:00", p.steps[0].reachedAt)
        assertEquals("2026-07-01T10:00:00", p.steps[1].reachedAt)
        assertNull(p.steps[3].reachedAt)
    }

    @Test
    fun perpetualProgressFollowsActivity() {
        val o = opening(cadence = "perpetual").copy(
            activity = OpeningActivity(acceptedCount = 2, acceptedLastAt = "2026-07-02T10:00:00", inProgressCount = 1),
        )
        val p = OpeningRules.progress(o)
        assertEquals(2, p.current)
        assertEquals("In Progress (multiple)", p.steps[2].label)
    }

    @Test
    fun cancelledProgress() {
        val p = OpeningRules.progress(opening(status = "Cancelled"))
        assertTrue(p.cancelled)
        assertEquals("Cancelled", p.currentLabel)
    }

    @Test
    fun acceptAsOnlyGroupsInTheOpeningsSphere() {
        val inSphere = Community(allianceId = "a1", sphereId = "s1", name = "A", kind = CommunityKind.Alliance)
        val elsewhere = Community(projectId = "p2", sphereId = "s2", name = "P", kind = CommunityKind.Project)
        val sphere = Community(sphereId = "s1", name = "S", kind = CommunityKind.Sphere)
        val provider = Community(allianceId = THEM, sphereId = "s1", name = "Provider", kind = CommunityKind.Alliance)
        val options = OpeningRules.acceptAsOptions(opening(sphereId = "s1"), listOf(inSphere, elsewhere, sphere, provider))
        assertEquals(listOf("a1"), options.map { it.id })
        // A standalone opening may be accepted by any group the viewer manages.
        assertEquals(2, OpeningRules.acceptAsOptions(opening(), listOf(inSphere, elsewhere, sphere)).size)
    }
}

class ExchangeRulesTest {
    private fun detail(
        status: String = "Initiated",
        initiator: Boolean = false,
        other: Boolean = false,
        receipt: String? = null,
        note: String? = null,
        initiatorFollowUp: String? = null,
        recipientFollowUp: String? = null,
        acknowledgement: String? = null,
    ) = ExchangeDetail(
        exchange = Exchange(
            id = "x1", status = status, receipt = receipt, initiatorNote = note,
            initiatorFollowUp = initiatorFollowUp, recipientFollowUp = recipientFollowUp,
            acknowledgement = acknowledgement, startedAt = "2026-06-24T09:00:00",
        ),
        isInitiator = initiator, isOther = other, isParticipant = initiator || other,
    )

    @Test
    fun statusOnlyAdvancesToFinishedByHand() {
        assertEquals("In Progress", ExchangeRules.nextStatus(detail().exchange))
        assertEquals("Finished", ExchangeRules.nextStatus(detail(status = "In Progress").exchange))
        // Receipted is reached by adding the receipt; the server refuses Finished → Receipted.
        assertNull(ExchangeRules.nextStatus(detail(status = "Finished").exchange))
        assertNull(ExchangeRules.nextStatus(detail(status = "Cancelled").exchange))
    }

    @Test
    fun onlyParticipantsAdvance() {
        assertTrue(ExchangeRules.canAdvance(detail(other = true)))
        assertFalse(ExchangeRules.canAdvance(detail()))
    }

    @Test
    fun onlyTheInitiatorCancelsAndOnlyBeforeFinished() {
        assertTrue(ExchangeRules.canCancel(detail(initiator = true)))
        assertTrue(ExchangeRules.canCancel(detail(status = "In Progress", initiator = true)))
        assertFalse(ExchangeRules.canCancel(detail(status = "Finished", initiator = true)))
        assertFalse(ExchangeRules.canCancel(detail(status = "Receipted", initiator = true)))
        assertFalse(ExchangeRules.canCancel(detail(other = true)))
    }

    @Test
    fun receiptIsTheRecipientsAndNoteTheInitiators() {
        assertTrue(ExchangeRules.canAddReceipt(detail(other = true)))
        assertFalse(ExchangeRules.canAddReceipt(detail(initiator = true)))
        assertFalse(ExchangeRules.canAddReceipt(detail(other = true, receipt = "thanks")))
        assertFalse(ExchangeRules.canAddReceipt(detail(status = "Cancelled", other = true)))
        assertTrue(ExchangeRules.canAddNote(detail(initiator = true)))
        assertFalse(ExchangeRules.canAddNote(detail(initiator = true, note = "gave")))
        assertFalse(ExchangeRules.canAddNote(detail(other = true)))
    }

    @Test
    fun followUpOnceBothSidesHaveWritten() {
        assertFalse(ExchangeRules.canAddFollowUp(detail(initiator = true, receipt = "r")))
        assertTrue(ExchangeRules.canAddFollowUp(detail(initiator = true, receipt = "r", note = "n")))
        assertFalse(ExchangeRules.canAddFollowUp(detail(initiator = true, receipt = "r", note = "n", initiatorFollowUp = "f")))
        assertTrue(ExchangeRules.canAddFollowUp(detail(other = true, receipt = "r", note = "n", initiatorFollowUp = "f")))
        assertFalse(ExchangeRules.canAddFollowUp(detail(receipt = "r", note = "n")))
    }

    @Test
    fun acknowledgementIsFirstCome() {
        assertTrue(ExchangeRules.canAcknowledge(detail()))
        assertFalse(ExchangeRules.canAcknowledge(detail(acknowledgement = "well done")))
    }

    @Test
    fun progressGainsAFollowUpStep() {
        val plain = ExchangeRules.progress(detail(status = "Receipted").exchange)
        assertEquals(4, plain.steps.size)
        assertEquals(3, plain.current)
        val followed = ExchangeRules.progress(detail(status = "Receipted", initiatorFollowUp = "f").exchange)
        assertEquals(5, followed.steps.size)
        assertEquals(4, followed.current)
        assertTrue(ExchangeRules.progress(detail(status = "Cancelled").exchange).cancelled)
    }

    @Test
    fun partiesNameTheViewerYou() {
        val x = Exchange(
            id = "x", initiatorId = ME, initiatorName = "Joe", initiatorKind = "user",
            otherUserId = "a1", otherUserName = "Repair Café", otherKind = "alliance",
            recipientActingUserId = THEM, recipientActingUserName = "Steve",
        )
        assertEquals("You", Parties.initiator(x, ME).label)
        val recipient = Parties.recipient(x, ME)!!
        assertEquals("Repair Café", recipient.label)
        assertEquals(CommunityKind.Alliance, recipient.group)
        assertEquals("Steve", recipient.actingUserName)
        assertEquals("Joe", Parties.initiator(x, THEM).label)
        // A group is never "You", even when its id were to match.
        assertFalse(Parties.recipient(x, "a1")!!.isViewer)
    }
}

class MembershipTest {
    private val alliance = Community(
        allianceId = "a1", sphereId = "s1", name = "A", kind = CommunityKind.Alliance,
        members = listOf(
            Member(ME, "Me", "steward"),
            Member("m2", "M2", "member"),
            Member("m3", "M3", "pending"),
        ),
    )

    @Test
    fun rolesDecideManagement() {
        assertTrue(Membership.canManage(alliance, ME, isPlatformAdmin = false))
        assertFalse(Membership.canManage(alliance, "m2", isPlatformAdmin = false))
        assertTrue(Membership.canManage(alliance, "m2", isPlatformAdmin = true))
        assertFalse(Membership.canManage(alliance, null, isPlatformAdmin = true))
    }

    @Test
    fun pendingIsNotAMember() {
        assertTrue(Membership.isMember(alliance, "m2"))
        assertFalse(Membership.isMember(alliance, "m3"))
        assertFalse(Membership.isMember(alliance, "stranger"))
    }

    @Test
    fun publicSphereActivityIsOpen() {
        val publicSphere = Community(sphereId = "s1", name = "S", isPublic = true, kind = CommunityKind.Sphere)
        assertTrue(Membership.canViewActivity(publicSphere, "stranger", isPlatformAdmin = false))
        assertFalse(Membership.canViewActivity(alliance, "stranger", isPlatformAdmin = false))
    }

    @Test
    fun sphereAdmin1Manages() {
        val sphere = Community(sphereId = "s1", name = "S", admin1 = ME, kind = CommunityKind.Sphere)
        assertTrue(Membership.canManage(sphere, ME, isPlatformAdmin = false))
    }
}
