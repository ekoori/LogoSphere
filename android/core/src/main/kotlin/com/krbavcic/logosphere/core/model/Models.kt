package com.krbavcic.logosphere.core.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.Transient
import com.krbavcic.logosphere.core.logic.UiMode

// Shapes of the LogoSphere API's JSON, as the Flask routes actually return them (recorded
// responses live in the test fixtures). Every field the server may omit or null has a default,
// and unknown fields are ignored, so an additive server change never breaks the app.

/** A person or group referred to by id and display name: followers, likers, list entries. */
@Serializable
data class PersonRef(
    val id: String,
    val name: String? = null,
)

@Serializable
data class User(
    @SerialName("user_id") val userId: String,
    val name: String? = null,
    val surname: String? = null,
    val email: String? = null,
    val location: String? = null,
    @SerialName("is_platform_admin") val isPlatformAdmin: Boolean = false,
    /** Told only about yourself. */
    @SerialName("ui_mode") val uiMode: String? = null,
) {
    val displayName: String
        get() = listOfNotNull(name, surname).joinToString(" ").trim().ifEmpty { email ?: "Member" }

    val mode: UiMode get() = UiMode.of(uiMode)
}

@Serializable
data class LoginResponse(
    val message: String? = null,
    @SerialName("session_id") val sessionId: String,
    val data: User,
)

@Serializable
data class SessionStatus(
    val status: String = "inactive",
    @SerialName("user_id") val userId: String? = null,
    @SerialName("user_data") val userData: User? = null,
) {
    val isActive: Boolean get() = status == "active" && userId != null && userData != null
}

/** Another member's public profile (`GET /api/users/<id>`). */
@Serializable
data class PublicUser(
    @SerialName("user_id") val userId: String,
    val name: String? = null,
    val surname: String? = null,
    val location: String? = null,
    @SerialName("is_following") val isFollowing: Boolean = false,
    @SerialName("following_count") val followingCount: Int = 0,
    @SerialName("is_platform_admin") val isPlatformAdmin: Boolean = false,
    /** An AI persona: a famous name playing an everyday neighbour in the demo spheres. */
    @SerialName("is_agent") val isAgent: Boolean = false,
    /** The viewer blocked them. Whether they blocked the viewer is never told. */
    val blocked: Boolean = false,
    @SerialName("can_message") val canMessage: Boolean = false,
) {
    val displayName: String
        get() = listOfNotNull(name, surname).joinToString(" ").trim().ifEmpty { "Member" }
}

// ── Value cards (the Meaning Graph) ─────────────────────────────────────────

@Serializable
data class ValueCard(
    @SerialName("card_id") val id: String? = null,
    @SerialName("user_id") val ownerId: String? = null,
    val title: String = "",
    @SerialName("care_about") val careAbout: String? = null,
    val because: String? = null,
    @SerialName("looks_like") val looksLike: List<String> = emptyList(),
    @SerialName("drift_looks_like") val driftLooksLike: String? = null,
    @SerialName("in_conflict") val inConflict: String? = null,
    @SerialName("never_do") val neverDo: String? = null,
    @SerialName("frankl_mode") val franklMode: String? = null,
    @SerialName("color_key") val colorKey: String? = null,
    val endorsed: Boolean? = null,
    @SerialName("needs_review") val needsReview: Boolean = false,
    @SerialName("endorsed_at") val endorsedAt: String? = null,
    @SerialName("reviewed_at") val reviewedAt: String? = null,
    @SerialName("created_at") val createdAt: String? = null,
)

/**
 * A value card as its editor holds it, for `POST`/`PATCH` (a person's or a group's). Editing never
 * overwrites: the server writes a new card and marks the old one superseded, so anything that
 * quoted the old wording keeps it.
 */
data class ValueCardDraft(
    val title: String = "",
    val careAbout: String = "",
    val because: String = "",
    /** One behaviour per line, as typed. */
    val looksLike: String = "",
    val driftLooksLike: String = "",
    val inConflict: String = "",
    val neverDo: String = "",
    val franklMode: String = "creative",
    val colorKey: String = "honey",
) {
    /** The behaviours, one per non-blank line. */
    val looksLikeLines: List<String> get() = looksLike.lines().map { it.trim() }.filter { it.isNotEmpty() }

    companion object {
        val COLOURS = listOf("honey", "leaf", "terracotta", "sage", "moss")

        fun of(card: ValueCard) = ValueCardDraft(
            title = card.title,
            careAbout = card.careAbout.orEmpty(),
            because = card.because.orEmpty(),
            looksLike = card.looksLike.joinToString("\n"),
            driftLooksLike = card.driftLooksLike.orEmpty(),
            inConflict = card.inConflict.orEmpty(),
            neverDo = card.neverDo.orEmpty(),
            franklMode = card.franklMode ?: "creative",
            colorKey = card.colorKey ?: "honey",
        )
    }
}

/** The signed-in member's own profile (`GET /api/user/profile`): unlike [PublicUser], it has the email. */
@Serializable
data class OwnProfile(
    @SerialName("user_id") val userId: String,
    val name: String? = null,
    val surname: String? = null,
    val email: String? = null,
    val location: String? = null,
    @SerialName("has_picture") val hasPicture: Boolean = false,
    @SerialName("is_platform_admin") val isPlatformAdmin: Boolean = false,
) {
    val displayName: String
        get() = listOfNotNull(name, surname).joinToString(" ").trim().ifEmpty { email ?: "Member" }
}

// ── Openings (offers and needs) ─────────────────────────────────────────────

@Serializable
data class Acceptance(
    @SerialName("accepter_id") val accepterId: String,
    @SerialName("accepter_name") val accepterName: String? = null,
    val status: String = "pending",
    @SerialName("exchange_id") val exchangeId: String? = null,
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("acting_user_id") val actingUserId: String? = null,
    @SerialName("acting_user_name") val actingUserName: String? = null,
    /** The human behind it is an AI persona. */
    @SerialName("is_agent") val isAgent: Boolean = false,
)

/** A perpetual opening's many acceptances, folded into one date per phase. */
@Serializable
data class OpeningActivity(
    @SerialName("accepted_count") val acceptedCount: Int = 0,
    @SerialName("accepted_last_at") val acceptedLastAt: String? = null,
    @SerialName("in_progress_count") val inProgressCount: Int = 0,
    @SerialName("in_progress_last_at") val inProgressLastAt: String? = null,
    @SerialName("completed_last_at") val completedLastAt: String? = null,
)

@Serializable
data class Opening(
    @SerialName("service_id") val id: String,
    val type: String = "offer",
    val title: String = "",
    val description: String? = null,
    val status: String = "Posted",
    val cadence: String = "single",
    val provider: String? = null,
    @SerialName("provider_id") val providerId: String? = null,
    /** Set when the opening was posted on behalf of an entity: the human who acted. */
    @SerialName("acting_user") val actingUser: String? = null,
    @SerialName("acting_user_id") val actingUserId: String? = null,
    @SerialName("sphere_id") val sphereId: String? = null,
    val spheres: List<String> = emptyList(),
    @SerialName("project_name") val projectName: String? = null,
    @SerialName("project_id") val projectId: String? = null,
    val values: List<String> = emptyList(),
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("accepted_at") val acceptedAt: String? = null,
    @SerialName("in_progress_at") val inProgressAt: String? = null,
    @SerialName("completed_at") val completedAt: String? = null,
    @SerialName("accepted_by_name") val acceptedByName: String? = null,
    val likes: Int = 0,
    @SerialName("liked_by") val likedBy: List<PersonRef> = emptyList(),
    @SerialName("liked_by_current_user") val likedByMe: Boolean = false,
    @SerialName("has_image") val hasImage: Boolean = false,
    /** Made with AI: labelled wherever it shows. */
    @SerialName("image_is_ai") val imageIsAi: Boolean = false,
    /** The viewer is the provider, posted it for an entity, or manages the providing entity. */
    @SerialName("is_provider") val isProvider: Boolean = false,
    /** [isProvider], or a platform admin. */
    @SerialName("can_manage") val canManage: Boolean = false,
    @SerialName("pending_acceptances") val pendingAcceptances: List<Acceptance> = emptyList(),
    @SerialName("my_acceptance") val myAcceptance: Acceptance? = null,
    val activity: OpeningActivity? = null,
    /** Confirmed acceptances, each with the exchange it created (detail endpoint only). */
    val exchanges: List<Acceptance> = emptyList(),
    val version: Int = 1,
    @SerialName("is_current") val isCurrent: Boolean = true,
    /** From a demo sphere, where the members are AI personas. */
    @SerialName("is_demo") val isDemo: Boolean = false,
    @SerialName("provider_is_agent") val providerIsAgent: Boolean = false,
    /** Where, in words. */
    val location: String? = null,
    /** From the viewer's own place, to it or else to its sphere. */
    val distance: Distance? = null,
    /** Detail only, and only where it was shown exactly. */
    val point: GeoPoint? = null,
    /** Detail only: who to write to about it (a group's opening: its poster). */
    @SerialName("contact_id") val contactId: String? = null,
    /** A loan: an offer to lend, or a need to borrow. */
    val borrow: Boolean = false,
    /** Spheres it's shared with beside its own: those the viewer is in (all, for who runs it). */
    @SerialName("shared_with") val sharedWith: List<GroupSummary> = emptyList(),
) {
    val isOffer: Boolean get() = type != "need"
    val isPerpetual: Boolean get() = cadence == "perpetual"
    val sphereName: String? get() = spheres.firstOrNull()
}

@Serializable
data class OpeningLikeResult(val liked: Boolean, val likes: Int)

@Serializable
data class ConfirmResult(val message: String? = null, @SerialName("exchange_id") val exchangeId: String? = null)

/** A new opening, as `POST /api/openings` takes it. */
data class NewOpening(
    val type: String,
    val cadence: String,
    val title: String,
    val description: String,
    val sphereId: String?,
    val sphereName: String?,
    val projectName: String?,
    /** Posted on behalf of a sphere, alliance or project the member manages. */
    val actingAsId: String? = null,
    val borrow: Boolean = false,
    /** Spheres to share it with beside its own. */
    val alsoSphereIds: List<String> = emptyList(),
)

/** `PATCH /api/openings/<id>`: once an exchange links to an opening, an edit makes a new version. */
@Serializable
data class OpeningEditResult(
    val message: String? = null,
    val versioned: Boolean = false,
    val service: Opening? = null,
)

// ── Exchanges (Meaning Trail rows) ──────────────────────────────────────────

@Serializable
data class LikeInfo(
    val count: Int = 0,
    val liked: Boolean = false,
    val by: List<PersonRef> = emptyList(),
    /** The viewer made this (their exchange, note, receipt or acknowledgement): not theirs to like. */
    val own: Boolean = false,
) {
    /** A like button, or only the count: an old self-like can still be taken off. */
    val canLike: Boolean get() = !own || liked
}

/**
 * One exchange. The Meaning Trail endpoints return a list of these; `GET /api/exchange/<id>`
 * wraps one in [ExchangeDetail] and adds [receiptPhotoCount] and [isFinished].
 */
@Serializable
data class Exchange(
    @SerialName("exchange_id") val id: String,
    @SerialName("exchange_description") val title: String? = null,
    @SerialName("exchange_long_description") val longDescription: String? = null,
    @SerialName("exchange_status") val status: String? = null,
    /** The trail partition the exchange lives in: the initiator (a person or an entity). */
    @SerialName("user_id") val userId: String? = null,
    @SerialName("initiator_id") val initiatorId: String? = null,
    @SerialName("initiator_name") val initiatorName: String? = null,
    @SerialName("initiator_kind") val initiatorKind: String? = null,
    @SerialName("initiator_acting_user_id") val initiatorActingUserId: String? = null,
    @SerialName("initiator_acting_user_name") val initiatorActingUserName: String? = null,
    @SerialName("other_user_id") val otherUserId: String? = null,
    @SerialName("other_user_name") val otherUserName: String? = null,
    @SerialName("other_kind") val otherKind: String? = null,
    @SerialName("recipient_acting_user_id") val recipientActingUserId: String? = null,
    @SerialName("recipient_acting_user_name") val recipientActingUserName: String? = null,
    @SerialName("project_id") val projectId: String? = null,
    @SerialName("project_name") val projectName: String? = null,
    @SerialName("source_service_id") val sourceOpeningId: String? = null,
    @SerialName("project_start_timestamp") val startedAt: String? = null,
    @SerialName("in_progress_at") val inProgressAt: String? = null,
    @SerialName("finished_at") val finishedAt: String? = null,
    @SerialName("receipted_at") val receiptedAt: String? = null,
    // The receipt: always written by the recipient.
    @SerialName("gratitude_comment") val receipt: String? = null,
    @SerialName("gratitude_comment_timestamp") val receiptAt: String? = null,
    @SerialName("gratitude_comment_cards") val receiptCards: List<ValueCard> = emptyList(),
    @SerialName("gratitude_comment_context") val receiptContext: String? = null,
    @SerialName("gratitude_frankl_mode") val receiptFranklMode: String? = null,
    // The initiator's personal note.
    @SerialName("user_comment") val initiatorNote: String? = null,
    @SerialName("user_comment_timestamp") val initiatorNoteAt: String? = null,
    @SerialName("user_comment_cards") val initiatorNoteCards: List<ValueCard> = emptyList(),
    // The first acknowledgement, as the older single slot; [acknowledgements] has them all.
    @SerialName("other_comment") val acknowledgement: String? = null,
    @SerialName("other_comment_timestamp") val acknowledgementAt: String? = null,
    @SerialName("other_comment_author_id") val acknowledgementAuthorId: String? = null,
    @SerialName("other_comment_author_name") val acknowledgementAuthorName: String? = null,
    @SerialName("other_comment_cards") val acknowledgementCards: List<ValueCard> = emptyList(),
    /** Any number, newest first. */
    val acknowledgements: List<Acknowledgement> = emptyList(),
    // One lighter follow-up per side, once both sides have written.
    @SerialName("initiator_comment") val initiatorFollowUp: String? = null,
    @SerialName("initiator_comment_timestamp") val initiatorFollowUpAt: String? = null,
    @SerialName("recipient_comment") val recipientFollowUp: String? = null,
    @SerialName("recipient_comment_timestamp") val recipientFollowUpAt: String? = null,
    /** Like counts keyed by what was liked: exchange, gratitude, user, other. */
    val likes: Map<String, LikeInfo> = emptyMap(),
    @SerialName("has_image") val hasImage: Boolean = false,
    /** Made with AI: labelled wherever it shows. */
    @SerialName("image_is_ai") val imageIsAi: Boolean = false,
    @SerialName("receipt_photo_count") val receiptPhotoCount: Int = 0,
    @SerialName("is_finished") val isFinished: Boolean = false,
    @SerialName("is_demo") val isDemo: Boolean = false,
    @SerialName("initiator_is_agent") val initiatorIsAgent: Boolean = false,
    @SerialName("other_is_agent") val otherIsAgent: Boolean = false,
    /** A loan. Only a single exchange's own page says. */
    val borrow: Boolean = false,
) {
    fun likesFor(target: LikeTarget): LikeInfo = likes[target.key] ?: LikeInfo()
}

/** What a like on an exchange is attached to; the API's `comment_type`. */
enum class LikeTarget(val key: String) {
    Exchange("exchange"),
    Receipt("gratitude"),
    InitiatorNote("user"),
    Acknowledgement("other"),
}

@Serializable
data class ExchangeDetail(
    val exchange: Exchange,
    @SerialName("is_initiator") val isInitiator: Boolean = false,
    @SerialName("is_other") val isOther: Boolean = false,
    @SerialName("is_participant") val isParticipant: Boolean = false,
    /** In its sphere, or a side of it. */
    @SerialName("can_acknowledge") val canAcknowledge: Boolean = false,
)

@Serializable
data class ExchangeLikeResult(val liked: Boolean, val count: Int)

/** The kinds of text that can be added to an exchange; the API's comment `type`. */
enum class CommentType(val key: String) {
    Receipt("gratitude"),
    InitiatorNote("user"),
    Acknowledgement("other"),
    FollowUp("comment"),
}

/** Frankl's three routes to meaning, which a receipt may name. */
enum class FranklMode(val key: String, val glyph: String, val label: String, val hint: String) {
    Creative("creative", "✶", "Creative", "something was made or given"),
    Experiential("experiential", "❍", "Experiential", "something was received or shared"),
    Attitudinal("attitudinal", "△", "Attitudinal", "a stance taken under constraint");

    companion object {
        fun of(key: String?): FranklMode? = entries.firstOrNull { it.key == key }
    }
}

data class NewComment(
    val type: CommentType,
    val text: String,
    val cards: List<ValueCard> = emptyList(),
    val franklMode: FranklMode? = null,
    val context: String? = null,
)

// ── Communities: spheres, alliances, projects ───────────────────────────────

enum class CommunityKind(val path: String, val noun: String, val plural: String, val glyph: String) {
    Sphere("spheres", "Sphere", "Spheres", "✦"),
    Alliance("alliances", "Alliance", "Alliances", "◈"),
    // U+FE0E asks for the text glyph: some phones (Samsung) draw ◻ as a white emoji tile otherwise.
    Project("projects", "Project", "Projects", "◻︎");

    companion object {
        fun of(key: String?): CommunityKind? = when (key) {
            "sphere" -> Sphere
            "alliance" -> Alliance
            "project" -> Project
            else -> null
        }
    }
}

@Serializable
data class Member(
    val id: String,
    val name: String? = null,
    val role: String? = null,
    @SerialName("is_agent") val isAgent: Boolean = false,
)

/**
 * A sphere, alliance or project. The three share one JSON shape apart from their id column —
 * and a sphere's `sphere_id` is its own id while an alliance's or project's is its parent sphere —
 * so the API client stamps [kind] on every decoded row and [id] reads the right column.
 */
@Serializable
data class Community(
    @SerialName("sphere_id") val sphereId: String? = null,
    @SerialName("alliance_id") val allianceId: String? = null,
    @SerialName("project_id") val projectId: String? = null,
    @SerialName("id") val plainId: String? = null,
    val name: String = "",
    val description: String? = null,
    val location: String? = null,
    val distance: Distance? = null,
    /** Detail only: the exact spot, for who may look inside, when its people chose to show it. */
    val point: GeoPoint? = null,
    @SerialName("sphere_name") val sphereName: String? = null,
    val members: List<Member> = emptyList(),
    /** A sphere's size; its [members] are empty for someone outside a private one. */
    @SerialName("member_count") val memberCount: Int? = null,
    val values: List<String> = emptyList(),
    @SerialName("value_cards") val valueCards: List<ValueCard> = emptyList(),
    @SerialName("has_image") val hasImage: Boolean = false,
    /** Made with AI: labelled wherever it shows. */
    @SerialName("image_is_ai") val imageIsAi: Boolean = false,
    @SerialName("is_public") val isPublic: Boolean = false,
    /** A demo sphere, or a group inside one: its members are AI personas. */
    @SerialName("is_demo") val isDemo: Boolean = false,
    @SerialName("join_policy") val joinPolicy: String? = null,
    @SerialName("decision_policy") val decisionPolicy: String? = null,
    /** Alliance: who manages its projects (single-pm, board). */
    @SerialName("pm_policy") val pmPolicy: String? = null,
    /** Alliance: who confirms acceptances of its openings (lead, board, any-member). */
    @SerialName("confirm_policy") val confirmPolicy: String? = null,
    /** Sphere: every new member is enrolled in it. */
    @SerialName("is_sandbox") val isSandbox: Boolean = false,
    /** Detail endpoint, managers only: join requests awaiting approval. */
    @SerialName("pending_members") val pendingMembers: List<PersonRef> = emptyList(),
    val admin1: String? = null,
    /** Sphere: its alliances' names. */
    val alliances: List<String> = emptyList(),
    /** Sphere or alliance: its projects' names. */
    val projects: List<String> = emptyList(),
    /** Sphere detail only: its alliances and projects with ids. */
    @SerialName("alliance_list") val allianceList: List<PersonRef> = emptyList(),
    @SerialName("project_list") val projectList: List<PersonRef> = emptyList(),
    /** Project: Initiated / In Progress / Completed; [phase] is ongoing or closed. */
    val status: String? = null,
    val phase: String? = null,
    @SerialName("owner_alliance") val ownerAlliance: String? = null,
    @SerialName("owner_id") val ownerId: String? = null,
    @SerialName("owner_name") val ownerName: String? = null,
    /** Detail endpoint only: whether the viewer may manage it (server-side rule). */
    @SerialName("can_manage") val canManage: Boolean = false,
    @Transient val kind: CommunityKind = CommunityKind.Sphere,
) {
    val id: String
        get() = when (kind) {
            CommunityKind.Sphere -> sphereId
            CommunityKind.Alliance -> allianceId ?: plainId
            CommunityKind.Project -> projectId ?: plainId
        }.orEmpty()

    /** The sphere an alliance or project belongs to; null for a sphere. */
    val parentSphereId: String? get() = if (kind == CommunityKind.Sphere) null else sphereId

    val isClosed: Boolean get() = kind == CommunityKind.Project && phase == "closed"

    /** How many are in it, whether or not the viewer may see who. */
    val peopleCount: Int get() = memberCount ?: members.count { it.role != "pending" }
}

@Serializable
data class JoinResult(
    val message: String? = null,
    val pending: Boolean = false,
    @SerialName("already_member") val alreadyMember: Boolean = false,
)

/** A new sphere, alliance or project. An alliance or project lives in a sphere its founder belongs to. */
data class NewCommunity(
    val kind: CommunityKind,
    val name: String,
    val description: String,
    val sphereId: String? = null,
    val sphereName: String? = null,
    /** A project may be run on behalf of an alliance its founder manages. */
    val ownerAllianceId: String? = null,
    val joinPolicy: String = "open",
)

// ── Notifications ───────────────────────────────────────────────────────────

@Serializable
data class AppNotification(
    @SerialName("notification_id") val id: String,
    val type: String? = null,
    val message: String = "",
    val link: String? = null,
    @SerialName("actor_id") val actorId: String? = null,
    @SerialName("actor_name") val actorName: String? = null,
    @SerialName("actor_is_agent") val actorIsAgent: Boolean = false,
    /** Kept verbatim: marking one read sends it back as part of the row's key. */
    @SerialName("created_at") val createdAt: String,
    @SerialName("is_read") val isRead: Boolean = false,
)

@Serializable
data class NotificationInbox(
    val notifications: List<AppNotification> = emptyList(),
    @SerialName("unread_count") val unreadCount: Int = 0,
)

// ── Search ──────────────────────────────────────────────────────────────────

@Serializable
data class SearchItem(
    val id: String? = null,
    val kind: String,
    val name: String = "",
    val summary: String? = null,
    val link: String? = null,
    @SerialName("sphere_name") val sphereName: String? = null,
    @SerialName("member_count") val memberCount: Int? = null,
    @SerialName("card_count") val cardCount: Int? = null,
    /** Value-card hits: whose card it is. */
    @SerialName("owner_name") val ownerName: String? = null,
    /** "Near my values": the words that made it similar. */
    val why: List<String> = emptyList(),
    val similarity: Double? = null,
    @SerialName("is_demo") val isDemo: Boolean = false,
    @SerialName("is_agent") val isAgent: Boolean = false,
)

@Serializable
data class SearchGroup(
    val kind: String,
    val label: String = "",
    val count: Int = 0,
    val items: List<SearchItem> = emptyList(),
)

@Serializable
data class SearchAround(
    val id: String? = null,
    val kind: String? = null,
    val name: String? = null,
    @SerialName("card_count") val cardCount: Int = 0,
)

@Serializable
data class SearchResults(
    val query: String? = null,
    val total: Int = 0,
    val groups: List<SearchGroup> = emptyList(),
    val note: String? = null,
    val around: SearchAround? = null,
)


// ── The demonstration ───────────────────────────────────────────────────────

@Serializable
data class DemoSphere(
    val id: String,
    val name: String = "",
    val description: String? = null,
    val joined: Boolean = false,
    @SerialName("member_count") val memberCount: Int = 0,
)

/** `GET /api/demo`: the demo spheres and whether you're in each. */
@Serializable
data class DemoStatus(
    val spheres: List<DemoSphere> = emptyList(),
    @SerialName("joined_any") val joinedAny: Boolean = false,
    @SerialName("joined_all") val joinedAll: Boolean = false,
)
