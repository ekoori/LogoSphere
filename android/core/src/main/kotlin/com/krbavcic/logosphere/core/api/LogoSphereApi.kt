package com.krbavcic.logosphere.core.api

import com.krbavcic.logosphere.core.model.AdminGroup
import com.krbavcic.logosphere.core.model.AdminGroups
import com.krbavcic.logosphere.core.model.AdminOpening
import com.krbavcic.logosphere.core.model.AdminOpenings
import com.krbavcic.logosphere.core.model.AdminOverview
import com.krbavcic.logosphere.core.model.AdminUser
import com.krbavcic.logosphere.core.model.AdminUsers
import com.krbavcic.logosphere.core.model.AppNotification
import com.krbavcic.logosphere.core.model.ClosenessMethod
import com.krbavcic.logosphere.core.model.Community
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.DemoStatus
import com.krbavcic.logosphere.core.model.ConfirmResult
import com.krbavcic.logosphere.core.model.Exchange
import com.krbavcic.logosphere.core.model.ExchangeDetail
import com.krbavcic.logosphere.core.model.ExchangeLikeResult
import com.krbavcic.logosphere.core.model.GraphEdge
import com.krbavcic.logosphere.core.model.GroupGovernance
import com.krbavcic.logosphere.core.model.JoinResult
import com.krbavcic.logosphere.core.model.JudgementResult
import com.krbavcic.logosphere.core.model.LikeTarget
import com.krbavcic.logosphere.core.model.LoginResponse
import com.krbavcic.logosphere.core.model.MeaningGraph
import com.krbavcic.logosphere.core.model.NewComment
import com.krbavcic.logosphere.core.model.NewCommunity
import com.krbavcic.logosphere.core.model.NewOpening
import com.krbavcic.logosphere.core.model.NewProposal
import com.krbavcic.logosphere.core.model.NotificationInbox
import com.krbavcic.logosphere.core.model.Opening
import com.krbavcic.logosphere.core.model.OpeningEditResult
import com.krbavcic.logosphere.core.model.OpeningLikeResult
import com.krbavcic.logosphere.core.model.OwnProfile
import com.krbavcic.logosphere.core.model.PersonRef
import com.krbavcic.logosphere.core.model.PublicUser
import com.krbavcic.logosphere.core.model.ResetLink
import com.krbavcic.logosphere.core.model.SearchResults
import com.krbavcic.logosphere.core.model.SessionStatus
import com.krbavcic.logosphere.core.model.ValueCard
import com.krbavcic.logosphere.core.model.ValueCardDraft
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.encodeToJsonElement
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put
import kotlinx.serialization.json.JsonPrimitive
import okhttp3.Call
import okhttp3.Callback
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import java.io.IOException
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException
import com.krbavcic.logosphere.core.model.MeaningTrail
import com.krbavcic.logosphere.core.logic.PlaceDraft
import com.krbavcic.logosphere.core.model.EmailSettings
import com.krbavcic.logosphere.core.model.MailStatus
import com.krbavcic.logosphere.core.model.Nearby
import com.krbavcic.logosphere.core.model.PlaceSearch
import com.krbavcic.logosphere.core.model.PlaceSettings
import com.krbavcic.logosphere.core.model.RegisterResult
import com.krbavcic.logosphere.core.model.BlockedPerson
import com.krbavcic.logosphere.core.model.Conversation
import com.krbavcic.logosphere.core.model.Conversations
import com.krbavcic.logosphere.core.model.DirectMessage
import com.krbavcic.logosphere.core.model.ReportOf
import com.krbavcic.logosphere.core.model.Reports
import com.krbavcic.logosphere.core.model.RespondentsResult
import com.krbavcic.logosphere.core.model.SentMessage
import com.krbavcic.logosphere.core.logic.UiMode
import com.krbavcic.logosphere.core.logic.EventAnswer
import com.krbavcic.logosphere.core.logic.EventDraft
import com.krbavcic.logosphere.core.model.ActivityItem
import com.krbavcic.logosphere.core.model.ActivityPage
import com.krbavcic.logosphere.core.model.Announcements
import com.krbavcic.logosphere.core.model.Correspondent
import com.krbavcic.logosphere.core.model.KnownPeople
import com.krbavcic.logosphere.core.model.CommunityEvent
import com.krbavcic.logosphere.core.model.EventsPage
import com.krbavcic.logosphere.core.model.Invite
import com.krbavcic.logosphere.core.model.NewInvite
import com.krbavcic.logosphere.core.model.AiHelpStatus
import com.krbavcic.logosphere.core.model.AiPicture
import com.krbavcic.logosphere.core.model.CardSuggestion
import com.krbavcic.logosphere.core.model.MessageAbout
import java.util.concurrent.TimeUnit

/** Lenient on input: unknown fields are ignored and a null where a default exists takes the default. */
val LogoSphereJson: Json = Json {
    ignoreUnknownKeys = true
    explicitNulls = false
    coerceInputValues = true
}

/**
 * Adds `Authorization: Bearer <session>` — the API's documented contract for non-browser
 * clients — to every request bound for the LogoSphere server, and to nothing else. The same
 * OkHttp client loads images, so authenticated images (exchange banners, receipt photos) work.
 */
class BearerAuthInterceptor(
    private val server: () -> HttpUrl,
    private val token: () -> String?,
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        val session = token()
        if (session.isNullOrBlank() || request.header("Authorization") != null ||
            request.url.host != server().host || request.url.port != server().port
        ) {
            return chain.proceed(request)
        }
        return chain.proceed(request.newBuilder().header("Authorization", "Bearer $session").build())
    }
}

/** The smaller copies the server makes of a picture (`?size=`). */
val PICTURE_SIDES = listOf(160, 320, 640)

/** The smallest copy that still looks sharp at [px] pixels, or null for the full picture. */
fun pictureSideFor(px: Int): Int? = PICTURE_SIDES.firstOrNull { it >= px }

/**
 * The LogoSphere REST API (backend/app/main.py). Every call is a suspend function that returns the
 * decoded body or throws: [UnauthorizedException] for a `401` on an authenticated request (after
 * telling [onUnauthorized]), [ApiException] for any other error status, [IOException] when the
 * server can't be reached.
 */
class LogoSphereApi(
    private val client: OkHttpClient,
    private val server: () -> HttpUrl,
    private val onUnauthorized: () -> Unit = {},
) {
    private val jsonType = "application/json; charset=utf-8".toMediaType()

    // ── Auth ────────────────────────────────────────────────────────────────

    suspend fun login(email: String, password: String): LoginResponse = post(
        "/api/login",
        buildJsonObject { put("email", email); put("password", password) },
    )

    /**
     * With email working, only name and address ([password] null): the answer says to look in the
     * inbox, and the account is made from the link there. Without, the password makes it at once.
     */
    suspend fun register(name: String, email: String, password: String? = null): RegisterResult = post(
        "/api/register",
        buildJsonObject {
            put("name", name)
            put("email", email)
            password?.let { put("password", it) }
        },
    )

    // ── Email ───────────────────────────────────────────────────────────────

    suspend fun mailOn(): Boolean = get<MailStatus>("/api/mail").on

    /** The same answer whether or not the address has an account. */
    suspend fun forgotPassword(email: String): String = said(
        post("/api/password/forgot", buildJsonObject { put("email", email.trim()) }),
        "If that address has an account, a link is on its way.",
    )

    suspend fun emailSettings(): EmailSettings = get("/api/account/email")

    suspend fun chooseEmailTopics(topics: List<String>): EmailSettings = post(
        "/api/account/email",
        buildJsonObject { put("topics", buildJsonArray { topics.forEach { add(JsonPrimitive(it)) } }) },
    )

    suspend fun sendEmailConfirmation(): String =
        said(post("/api/account/email/confirm", JsonObject(emptyMap())), "A link is on its way.")

    // ── Messages, blocking and reporting ────────────────────────────────────

    suspend fun conversations(): Conversations = get("/api/messages")

    /** A page, oldest first; [before] (a message's id) for older ones. [about]: what it's about, as "kind:id". */
    suspend fun conversation(personId: String, about: String? = null, before: String? = null): Conversation =
        get(url("/api/messages/$personId") {
            about?.let { addQueryParameter("about", it) }
            before?.let { addQueryParameter("before", it) }
        })

    suspend fun sendMessage(personId: String, text: String, about: MessageAbout?): DirectMessage = post<SentMessage>(
        "/api/messages/$personId",
        buildJsonObject {
            put("text", text.trim())
            about?.let {
                put("about", buildJsonObject { put("kind", it.kind); put("id", it.id) })
            }
        },
    ).sent

    suspend fun readConversation(personId: String, upTo: String) {
        post<JsonElement>("/api/messages/$personId/read", buildJsonObject { put("up_to", upTo) })
    }

    /** Privately to each who responded: they don't learn who else did. */
    suspend fun messageRespondents(openingId: String, text: String): RespondentsResult =
        post("/api/openings/$openingId/message_respondents", buildJsonObject { put("text", text.trim()) })

    suspend fun blockedPeople(): List<BlockedPerson> = get("/api/blocks")

    suspend fun setBlocked(personId: String, blocked: Boolean) {
        post<JsonElement>("/api/blocks/$personId", buildJsonObject { put("blocked", blocked) })
    }

    /** Returns what to tell the one reporting. */
    suspend fun report(what: ReportOf, note: String): String = said(
        post(
            "/api/reports",
            buildJsonObject {
                put("kind", what.kind)
                put("id", what.id)
                put("note", note.trim())
                what.personId?.let { put("person_id", it) }
                what.trailId?.let { put("trail_id", it) }
                what.groupId?.let { put("group_id", it) }
            },
        ),
        "Thank you. The platform's administrators will look at it.",
    )

    suspend fun adminReports(status: String): Reports = get(url("/api/admin/reports") { addQueryParameter("status", status) })

    suspend fun settleReport(id: String, status: String, note: String, remove: Boolean) {
        post<JsonElement>(
            "/api/admin/reports/$id",
            buildJsonObject {
                put("status", status)
                put("note", note.trim())
                put("remove", remove)
            },
        )
    }

    // ── Events, announcements and invitations ───────────────────────────────

    /** What's on, soonest first: everywhere the member may look, or in one group. */
    suspend fun events(groupId: String? = null): List<CommunityEvent> =
        get<EventsPage>(url("/api/events") { groupId?.let { addQueryParameter("group", it) } }).events

    suspend fun event(id: String): CommunityEvent = get("/api/events/$id")

    /** [hostId]: the group putting it on; none is for everyone. */
    suspend fun createEvent(draft: EventDraft, hostId: String?): CommunityEvent = post("/api/events", draft.body(hostId))

    suspend fun editEvent(id: String, draft: EventDraft): CommunityEvent = patch("/api/events/$id", draft.body())

    /** [answer] null takes the answer back, which has to be said. */
    suspend fun replyEvent(id: String, day: String, answer: EventAnswer?): CommunityEvent =
        post("/api/events/$id/reply", buildJsonObject { put("day", day); put("answer", answer?.key) })

    /** All of it, or only [day]; [cancelled] false puts that date back on. */
    suspend fun cancelEvent(id: String, day: String? = null, cancelled: Boolean = true): CommunityEvent = post(
        "/api/events/$id/cancel",
        buildJsonObject {
            if (day != null) put("day", day)
            put("cancelled", cancelled)
        },
    )

    suspend fun setEventImage(id: String, picture: Upload) {
        multipart<JsonElement>("/api/events/$id/image") { addPicture("image", picture) }
    }

    fun eventImageUrl(id: String, side: Int? = null): String =
        url("/api/events/$id/image") { side?.let { addQueryParameter("size", it.toString()) } }.toString()

    suspend fun announcements(groupId: String): Announcements = get("/api/announcements/$groupId")

    suspend fun announce(groupId: String, text: String) {
        post<JsonElement>("/api/announcements/$groupId", buildJsonObject { put("text", text.trim()) })
    }

    suspend fun removeAnnouncement(groupId: String, id: String) {
        delete<JsonElement>("/api/announcements/$groupId/$id")
    }

    suspend fun invites(): List<Invite> = get("/api/invites")

    /** A new link: into [groupId], or just to LogoSphere. */
    suspend fun makeInvite(groupId: String?): NewInvite =
        post("/api/invites", buildJsonObject { if (groupId != null) put("group_id", groupId) })

    suspend fun revokeInvite(id: String) {
        post<JsonElement>("/api/invites/$id/revoke", JsonObject(emptyMap()))
    }

    // ── Places ──────────────────────────────────────────────────────────────

    /** A place, whole: only for whoever may change it. [kind]: users, openings, or a group's path. */
    suspend fun place(kind: String, id: String): PlaceSettings = get("/api/places/$kind/$id")

    suspend fun savePlace(kind: String, id: String, draft: PlaceDraft): PlaceSettings =
        post("/api/places/$kind/$id", draft.body())

    /** In the body, so what people look for stays out of URLs. */
    suspend fun searchPlaces(text: String): PlaceSearch =
        post("/api/places/search", buildJsonObject { put("q", text) })

    suspend fun nearestPlaces(lat: Double, lon: Double): PlaceSearch =
        post("/api/places/nearest", buildJsonObject { put("lat", lat); put("lon", lon) })

    suspend fun nearby(km: Int): Nearby = get(url("/api/nearby") { addQueryParameter("km", km.toString()) })

    /** Revokes the session on the server; the caller forgets it locally either way. */
    suspend fun logout() {
        post<JsonElement>("/api/logout", JsonObject(emptyMap()))
    }

    /** This phone gets the signed-in member's notifications, until this session ends. */
    suspend fun registerDevice(token: String) {
        post<JsonElement>("/api/push/devices", buildJsonObject { put("token", token); put("platform", "android") })
    }

    /** This phone stops getting the member's notifications (before signing out). */
    suspend fun forgetDevice(token: String) {
        post<JsonElement>("/api/push/devices/forget", buildJsonObject { put("token", token) })
    }

    suspend fun checkSession(): SessionStatus = get("/api/check_session")

    /** Simple or Advanced, for this account everywhere. */
    suspend fun setUiMode(mode: UiMode) {
        post<JsonElement>("/api/account/preferences", buildJsonObject { put("ui_mode", mode.key) })
    }

    // ── People ──────────────────────────────────────────────────────────────

    suspend fun user(id: String): PublicUser = get("/api/users/$id")

    /** Toggles following [id]; returns whether the viewer now follows them. */
    suspend fun toggleFollow(id: String): Boolean =
        post<JsonObject>("/api/users/$id/follow", JsonObject(emptyMap()))["following"]
            ?.jsonPrimitive?.content == "true"

    suspend fun following(): List<PersonRef> = get("/api/following")

    /** What the people you follow did lately: only what you could open anyway. */
    suspend fun activity(): List<ActivityItem> = get<ActivityPage>("/api/activity").activity

    /** Whom you and [personId] both know, from exchanges you can see. */
    suspend fun known(personId: String): List<Correspondent> = get<KnownPeople>("/api/users/$personId/known").people

    /** The value cards on a person's, sphere's, alliance's or project's Meaning Graph. */
    suspend fun valueCards(ownerId: String): List<ValueCard> = get("/api/value_cards/$ownerId")

    // ── AI help (only when the member asks) ─────────────────────────────────

    suspend fun aiStatus(): AiHelpStatus = get("/api/ai")

    /** A draft from the member's notes. Sends only fields they can see ([brief]: Simple's three). */
    suspend fun draftCard(notes: String, draft: ValueCardDraft, brief: Boolean, group: Boolean): CardSuggestion = postSlowly(
        "/api/ai/value_card",
        buildJsonObject {
            put("notes", notes)
            put("draft", buildJsonObject {
                fun field(key: String, value: String) {
                    if (value.isNotBlank()) put(key, value.trim())
                }
                field("title", draft.title)
                field("care_about", draft.careAbout)
                field("because", draft.because)
                if (!brief) {
                    val lines = draft.looksLikeLines
                    if (lines.isNotEmpty()) put("looks_like", buildJsonArray { lines.forEach { add(JsonPrimitive(it)) } })
                    field("drift_looks_like", draft.driftLooksLike)
                    field("in_conflict", draft.inConflict)
                    field("never_do", draft.neverDo)
                }
            })
            put("brief", brief)
            put("group", group)
        },
    )

    /** A picture for an opening or group: nothing is saved until it's uploaded like any other. */
    suspend fun drawPicture(purpose: String, title: String, description: String, hint: String): AiPicture = postSlowly(
        "/api/ai/picture",
        buildJsonObject { put("purpose", purpose); put("title", title); put("description", description); put("hint", hint) },
    )

    // ── The Meaning Graph ───────────────────────────────────────────────────

    /** Every card the member may read, and how close they are. */
    suspend fun meaningGraph(): MeaningGraph = get("/api/meaning_graph")

    /** How closeness is worked out, in full. */
    suspend fun meaningGraphMethod(): ClosenessMethod = get("/api/meaning_graph/method")

    /** The member's judgement of a pair; null takes it back. */
    suspend fun judgeCloseness(a: String, b: String, close: Boolean?): GraphEdge = post<JudgementResult>(
        "/api/meaning_graph/judgement",
        buildJsonObject { put("a", a); put("b", b); put("close", close) },
    ).edge

    // ── Your profile ────────────────────────────────────────────────────────

    suspend fun ownProfile(): OwnProfile = get("/api/user/profile")

    /** Name and surname; a new photo too when [picture] is given. Where you are is [savePlace]'s. */
    suspend fun updateProfile(name: String, surname: String, picture: Upload? = null) {
        multipart<JsonElement>("/api/updateuser") {
            addFormDataPart("name", name.trim())
            addFormDataPart("surname", surname.trim())
            picture?.let { addPicture("profile_picture", it) }
        }
    }

    // ── Your account ────────────────────────────────────────────────────────

    /** Changes your password; your other sessions end. Returns the server's message. */
    suspend fun changePassword(current: String, new: String): String =
        post<JsonObject>(
            "/api/account/password",
            buildJsonObject {
                put("current_password", current)
                put("new_password", new)
            },
        )["message"]?.jsonPrimitive?.content ?: "Password changed."

    /** Everything LogoSphere holds about you, as the JSON file the server makes. */
    suspend fun exportData(): String = text(url("/api/account/export"))

    /** Deletes your account (your password confirms it); the session ends with it. */
    suspend fun deleteAccount(password: String) {
        post<JsonElement>("/api/account/delete", buildJsonObject { put("password", password) })
    }

    // ── Writing value cards: your own (groupId null) or a group's you manage ─

    /** Writes a new card, or — with [cardId] — edits one (the server keeps the old wording as history). */
    suspend fun saveValueCard(groupId: String?, cardId: String?, draft: ValueCardDraft): ValueCard {
        val base = cardsPath(groupId)
        return if (cardId == null) post(base, draft.toJson()) else patch("$base/$cardId", draft.toJson())
    }

    suspend fun deleteValueCard(groupId: String?, cardId: String) {
        delete<JsonElement>("${cardsPath(groupId)}/$cardId")
    }

    /** CLEAR's E: re-read it, and if it still holds after reflection, endorse it. */
    suspend fun endorseValueCard(groupId: String?, cardId: String): ValueCard =
        post("${cardsPath(groupId)}/$cardId/endorse", JsonObject(emptyMap()))

    /** CLEAR's R: it still holds — reviewed (the server asks again after 90 days). */
    suspend fun reviewValueCard(groupId: String?, cardId: String): ValueCard =
        post("${cardsPath(groupId)}/$cardId/review", JsonObject(emptyMap()))

    /** Copies someone else's card onto your Meaning Graph ([targetId] = you) or a group's you manage. */
    suspend fun cloneValueCard(card: ValueCard, targetId: String): ValueCard = post(
        "/api/value_cards/clone",
        buildJsonObject {
            put("source", LogoSphereJson.encodeToJsonElement(card))
            put("target_id", targetId)
        },
    )

    private fun cardsPath(groupId: String?) = if (groupId == null) "/api/value_cards" else "/api/entity_value_cards/$groupId"

    // ── Meaning Trail and exchanges ─────────────────────────────────────────

    /** The signed-in member's own trail. */
    suspend fun myTrail(): List<Exchange> = get("/api/meaning_trail")

    /** Someone else's trail — a person's, or an entity's own (sphere, alliance, project). */
    suspend fun trailOf(ownerId: String): List<Exchange> =
        post("/api/meaning_trail", buildJsonObject { put("userId", ownerId) })

    /** Exchanges anyone tagged with a project. */
    suspend fun projectTrail(projectId: String): List<Exchange> = get("/api/meaning_trail/by_project/$projectId")

    /** A trail as one timeline: a person's, sphere's, alliance's, project's or exchange's. */
    suspend fun trail(id: String): MeaningTrail = get("/api/trails/$id")

    /** Anyone may, except in spheres they aren't in. */
    suspend fun acknowledge(trailId: String, text: String, cardIds: List<String>) {
        post<JsonElement>(
            "/api/trails/$trailId/acknowledgements",
            buildJsonObject {
                put("text", text.trim())
                put("card_ids", buildJsonArray { cardIds.forEach { add(JsonPrimitive(it)) } })
            },
        )
    }

    /** Sets (not toggles) the like. */
    suspend fun likeAcknowledgement(trailId: String, ackId: String, liked: Boolean): ExchangeLikeResult =
        post("/api/trails/$trailId/acknowledgements/$ackId/like", buildJsonObject { put("liked", liked) })

    /** The trail's owner's: two at most in a run (the server answers 409 for a third). */
    suspend fun highlightAcknowledgement(trailId: String, ackId: String, highlighted: Boolean) {
        post<JsonElement>("/api/trails/$trailId/acknowledgements/$ackId/highlight", buildJsonObject { put("highlighted", highlighted) })
    }

    suspend fun removeAcknowledgement(trailId: String, ackId: String) {
        delete<JsonElement>("/api/trails/$trailId/acknowledgements/$ackId")
    }

    suspend fun exchange(id: String): ExchangeDetail = get("/api/exchange/$id")

    suspend fun setExchangeStatus(id: String, status: String) {
        post<JsonElement>("/api/exchange/$id/status", buildJsonObject { put("status", status) })
    }

    suspend fun addComment(exchangeId: String, comment: NewComment) {
        val body = buildJsonObject {
            put("type", comment.type.key)
            put("text", comment.text.trim())
            put("card_ids", buildJsonArray { comment.cards.mapNotNull { it.id }.forEach { add(JsonPrimitive(it)) } })
            put("cards", LogoSphereJson.encodeToJsonElement(comment.cards))
            comment.franklMode?.let { put("frankl_mode", it.key) }
            comment.context?.trim()?.takeIf { it.isNotEmpty() }?.let { put("context", it) }
        }
        post<JsonElement>("/api/exchange/$exchangeId/comment", body)
    }

    suspend fun likeExchange(id: String, target: LikeTarget): ExchangeLikeResult =
        post("/api/exchange/$id/like", buildJsonObject { put("comment_type", target.key) })

    /** Title, description and (with [banner]) the picture — by either side, until it's finished. */
    suspend fun editExchange(id: String, title: String, description: String, banner: Upload? = null) {
        multipart<JsonElement>("/api/exchange/$id/edit") {
            addFormDataPart("title", title.trim())
            addFormDataPart("description", description.trim())
            banner?.let { addPicture("image", it) }
        }
    }

    /** Up to three photos with the receipt (the recipient's). Returns how many were kept. */
    suspend fun addReceiptPhotos(id: String, photos: List<Upload>): Int {
        require(photos.isNotEmpty()) { "no photos" }
        val result = multipart<JsonObject>("/api/exchange/$id/receipt_photos") {
            photos.take(3).forEach { addPicture("photos", it) }
        }
        return result["count"]?.jsonPrimitive?.intOrNull ?: 0
    }

    // ── Openings ────────────────────────────────────────────────────────────

    suspend fun openings(): List<Opening> = get("/api/openings")

    suspend fun opening(id: String): Opening = get("/api/openings/$id")

    /** Posts an opening; returns its id (for its picture). */
    suspend fun createOpening(opening: NewOpening): String {
        val body = buildJsonObject {
            put("type", opening.type)
            put("cadence", opening.cadence)
            put("title", opening.title.trim())
            put("description", opening.description.trim())
            put("sphere_id", opening.sphereId)
            put("sphere_name", opening.sphereName)
            put("project_name", opening.projectName)
            put("status", "Posted")
            put("borrow", opening.borrow)
            if (opening.alsoSphereIds.isNotEmpty()) {
                put("also_sphere_ids", buildJsonArray { opening.alsoSphereIds.forEach { add(JsonPrimitive(it)) } })
            }
            opening.actingAsId?.let { put("acting_as_id", it) }
        }
        return post<JsonObject>("/api/openings", body)["service_id"]?.jsonPrimitive?.content.orEmpty()
    }

    /** Title, description, whether it's a loan. Once an exchange links to the opening, this makes a new version. */
    suspend fun editOpening(id: String, title: String, description: String, borrow: Boolean? = null): OpeningEditResult = patch(
        "/api/openings/$id",
        buildJsonObject {
            put("title", title.trim())
            put("description", description)
            if (borrow != null) put("borrow", borrow)
        },
    )

    /** [sphereIds]: all the spheres it's shared with beside its own; none unshares it. */
    suspend fun shareOpening(id: String, sphereIds: List<String>): Opening = post(
        "/api/openings/$id/spheres",
        buildJsonObject { put("sphere_ids", buildJsonArray { sphereIds.forEach { add(JsonPrimitive(it)) } }) },
    )

    suspend fun setOpeningImage(id: String, picture: Upload) {
        multipart<JsonElement>("/api/openings/$id/image") { addPicture("image", picture) }
    }

    /** Step one of two: signal acceptance, as yourself or as an alliance/project you manage. */
    suspend fun acceptOpening(id: String, actingAsId: String? = null) {
        post<JsonElement>(
            "/api/openings/$id/accept",
            buildJsonObject { if (actingAsId != null) put("acting_as_id", actingAsId) },
        )
    }

    /** Step two: the provider confirms one acceptance, which creates the exchange. */
    suspend fun confirmAcceptance(id: String, accepterId: String): ConfirmResult =
        post("/api/openings/$id/confirm", buildJsonObject { put("accepter_id", accepterId) })

    suspend fun declineAcceptance(id: String, accepterId: String) {
        post<JsonElement>("/api/openings/$id/reject", buildJsonObject { put("accepter_id", accepterId) })
    }

    suspend fun withdrawOpening(id: String) {
        post<JsonElement>("/api/openings/$id/cancel", JsonObject(emptyMap()))
    }

    /** Sets (not toggles) the like, so a retried request changes nothing. */
    suspend fun likeOpening(id: String, liked: Boolean): OpeningLikeResult =
        post("/api/openings/$id/like", buildJsonObject { put("liked", liked) })

    // ── Spheres, alliances, projects ────────────────────────────────────────

    suspend fun communities(kind: CommunityKind): List<Community> =
        get<List<Community>>("/api/${kind.path}").map { it.copy(kind = kind) }

    suspend fun community(kind: CommunityKind, id: String): Community =
        get<Community>("/api/${kind.path}/$id").copy(kind = kind)

    suspend fun join(kind: CommunityKind, id: String): JoinResult =
        post("/api/${kind.path}/$id/join", JsonObject(emptyMap()))

    /** Leaves a group, or withdraws a request to join it (the founder can't leave). */
    suspend fun leave(kind: CommunityKind, id: String): String =
        post<JsonObject>("/api/${kind.path}/$id/leave", JsonObject(emptyMap()))["message"]?.jsonPrimitive?.content
            ?: "You've left."

    /** Starts a group (the create call takes the core fields; a join policy other than open follows). */
    suspend fun createCommunity(new: NewCommunity, banner: Upload? = null): Community {
        val created = multipart<Community>("/api/${new.kind.path}") {
            addFormDataPart("name", new.name.trim())
            addFormDataPart("description", new.description.trim())
            if (new.kind != CommunityKind.Sphere) {
                addFormDataPart("sphere_id", new.sphereId.orEmpty())
                addFormDataPart("sphere_name", new.sphereName.orEmpty())
            }
            if (new.kind == CommunityKind.Project) new.ownerAllianceId?.let { addFormDataPart("owner_alliance_id", it) }
            banner?.let { addPicture("image", it) }
        }.copy(kind = new.kind)
        if (new.joinPolicy != "open" && created.id.isNotEmpty()) {
            return updateCommunity(new.kind, created.id, mapOf("join_policy" to new.joinPolicy))
        }
        return created
    }

    /** Name, description and policies (join_policy, decision_policy, pm_policy, confirm_policy, phase). */
    suspend fun updateCommunity(kind: CommunityKind, id: String, changes: Map<String, String>): Community =
        patch<Community>("/api/${kind.path}/$id", JsonObject(changes.mapValues { JsonPrimitive(it.value) })).copy(kind = kind)

    suspend fun setCommunityImage(kind: CommunityKind, id: String, picture: Upload) {
        multipart<JsonElement>("/api/${kind.path}/$id/image") { addPicture("image", picture) }
    }

    /** A sphere's flags: public activity (its managers), sandbox enrolment (platform admins only). */
    suspend fun setSphereFlags(id: String, isPublic: Boolean? = null, isSandbox: Boolean? = null) {
        post<JsonElement>(
            "/api/spheres/$id/governance",
            buildJsonObject {
                isPublic?.let { put("is_public", it) }
                isSandbox?.let { put("is_sandbox", it) }
            },
        )
    }

    /** Sets a member's role; approves a request (any role) or, with `remove`, declines or removes. */
    suspend fun setMemberRole(kind: CommunityKind, id: String, memberId: String, role: String) {
        post<JsonElement>("/api/${kind.path}/$id/members/$memberId/role", buildJsonObject { put("role", role) })
    }

    // ── Governance ──────────────────────────────────────────────────────────

    suspend fun governance(kind: CommunityKind, id: String): GroupGovernance = get("/api/${kind.path}/$id/governance")

    suspend fun propose(kind: CommunityKind, id: String, proposal: NewProposal) {
        post<JsonElement>(
            "/api/${kind.path}/$id/proposals",
            buildJsonObject {
                put("kind", proposal.kind)
                put("title", proposal.title.trim())
                put("description", proposal.description.trim())
                put("days", proposal.days)
                if (proposal.kind == "policy") {
                    put("policy_key", proposal.policyKey)
                    put("policy_value", proposal.policyValue)
                }
            },
        )
    }

    /** yes, no or abstain; voting again changes your vote. */
    suspend fun vote(kind: CommunityKind, id: String, proposalId: String, choice: String) {
        post<JsonElement>("/api/${kind.path}/$id/proposals/$proposalId/vote", buildJsonObject { put("choice", choice) })
    }

    /** A manager counts the votes now instead of waiting for the closing date. */
    suspend fun closeProposal(kind: CommunityKind, id: String, proposalId: String) {
        post<JsonElement>("/api/${kind.path}/$id/proposals/$proposalId/close", JsonObject(emptyMap()))
    }

    suspend fun withdrawProposal(kind: CommunityKind, id: String, proposalId: String) {
        post<JsonElement>("/api/${kind.path}/$id/proposals/$proposalId/withdraw", JsonObject(emptyMap()))
    }

    /** Lends your vote to [delegateId]; null votes for yourself again. */
    suspend fun delegateVote(kind: CommunityKind, id: String, delegateId: String?) {
        post<JsonElement>(
            "/api/${kind.path}/$id/delegation",
            buildJsonObject { put("delegate_id", delegateId?.let { JsonPrimitive(it) } ?: JsonNull) },
        )
    }

    // ── Platform administration (platform admins only) ───────────────────────

    suspend fun adminOverview(): AdminOverview = get("/api/admin/overview")

    suspend fun adminUsers(): List<AdminUser> = get<AdminUsers>("/api/admin/users").users

    /** Grants or revokes the administrator flag, or marks someone an AI persona (or a person again). */
    suspend fun adminSetUserFlags(id: String, isPlatformAdmin: Boolean? = null, isAgent: Boolean? = null) {
        patch<JsonElement>(
            "/api/admin/users/$id",
            buildJsonObject {
                isPlatformAdmin?.let { put("is_platform_admin", it) }
                isAgent?.let { put("is_agent", it) }
            },
        )
    }

    suspend fun adminEditUser(id: String, name: String, surname: String, location: String) {
        patch<JsonElement>(
            "/api/admin/users/$id",
            buildJsonObject {
                put("name", name.trim())
                put("surname", surname.trim())
                put("location", location.trim())
            },
        )
    }

    suspend fun adminDeleteUser(id: String) {
        delete<JsonElement>("/api/admin/users/$id")
    }

    /** A one-time password reset link for a member who forgot theirs (24 hours, used once). */
    suspend fun adminResetLink(id: String): ResetLink =
        post("/api/admin/users/$id/reset_link", JsonObject(emptyMap()))

    suspend fun adminGroups(kind: CommunityKind): List<AdminGroup> = get<AdminGroups>("/api/admin/${kind.path}").items

    suspend fun adminDeleteGroup(kind: CommunityKind, id: String) {
        delete<JsonElement>("/api/admin/${kind.path}/$id")
    }

    /** A demo sphere: its members are AI personas, and it and everything in it is labelled Demo. */
    suspend fun adminSetDemo(sphereId: String, isDemo: Boolean) {
        patch<JsonElement>("/api/admin/spheres/$sphereId", buildJsonObject { put("is_demo", isDemo) })
    }

    suspend fun adminOpenings(): List<AdminOpening> = get<AdminOpenings>("/api/admin/openings").items

    /** Only an opening no exchange came from can be deleted; others are withdrawn instead. */
    suspend fun adminDeleteOpening(id: String) {
        delete<JsonElement>("/api/admin/openings/$id")
    }

    // ── Notifications ───────────────────────────────────────────────────────

    suspend fun notifications(): NotificationInbox = get("/api/notifications")

    // ── The demonstration ────────────────────────────────────────────────────
    /** The demo spheres (AI personas play everyday neighbours there) and whether you're in each. */
    suspend fun demo(): DemoStatus = get("/api/demo")

    /** Join every demo sphere at once. */
    suspend fun joinDemo(): DemoStatus = post("/api/demo/join", JsonObject(emptyMap()))

    suspend fun markRead(notification: AppNotification) {
        post<JsonElement>(
            "/api/notifications/read",
            buildJsonObject {
                put("created_at", notification.createdAt)
                put("notification_id", notification.id)
            },
        )
    }

    suspend fun markAllRead() {
        post<JsonElement>("/api/notifications/read_all", JsonObject(emptyMap()))
    }

    // ── Search ──────────────────────────────────────────────────────────────

    /** Plain text search over names, titles, descriptions and value cards (two characters or more). */
    suspend fun search(query: String, kind: String? = null): SearchResults =
        get(url("/api/search") {
            addQueryParameter("q", query)
            if (kind != null) addQueryParameter("kinds", kind)
            addQueryParameter("limit", "12")
        })

    /** Ranks by closeness to the values described — or, with no query, to the viewer's own cards. */
    suspend fun searchNearValues(query: String?, kind: String? = null): SearchResults =
        get(url("/api/search/vicinity") {
            if (!query.isNullOrBlank()) addQueryParameter("q", query)
            if (kind != null) addQueryParameter("kinds", kind)
            addQueryParameter("limit", "12")
        })

    // ── Images (loaded by the image loader through the same client) ─────────

    /** A member's avatar; [side] asks for a smaller copy (one of [PICTURE_SIDES]) where it's shown small. */
    fun avatarUrl(userId: String, side: Int? = null): String =
        url("/api/users/$userId/avatar") { side?.let { addQueryParameter("size", it.toString()) } }.toString()
    fun communityImageUrl(kind: CommunityKind, id: String): String = url("/api/${kind.path}/$id/image").toString()
    fun openingImageUrl(id: String): String = url("/api/openings/$id/image").toString()
    fun exchangeImageUrl(id: String): String = url("/api/exchange/$id/image").toString()
    fun receiptPhotoUrl(exchangeId: String, index: Int): String =
        url("/api/exchange/$exchangeId/receipt_photo/$index").toString()

    /** A page of the web app, for what the phone leaves to the web (management, editing…). */
    fun webUrl(path: String): String = server().resolve(path)?.toString() ?: server().toString()

    // ── Plumbing ────────────────────────────────────────────────────────────

    private fun url(path: String, build: HttpUrl.Builder.() -> Unit = {}): HttpUrl {
        val base = server()
        return base.newBuilder().encodedPath(path).apply(build).build()
    }

    private suspend inline fun <reified T> get(path: String): T = get(url(path))

    private fun said(body: JsonObject, otherwise: String): String = body["message"]?.jsonPrimitive?.content ?: otherwise

    private suspend inline fun <reified T> get(url: HttpUrl): T =
        execute(Request.Builder().url(url).get().build())

    /** A GET whose body is kept as text (a file to save), not decoded. */
    private suspend fun text(url: HttpUrl): String = withContext(Dispatchers.IO) {
        send(Request.Builder().url(url).get().build())
    }

    private fun json(body: JsonElement): RequestBody =
        LogoSphereJson.encodeToString(JsonElement.serializer(), body).toRequestBody(jsonType)

    private suspend inline fun <reified T> post(path: String, body: JsonElement): T =
        execute(Request.Builder().url(url(path)).post(json(body)).build())

    /** AI answers take longer than anything else here does. */
    private val patientClient: OkHttpClient by lazy { client.newBuilder().readTimeout(70, TimeUnit.SECONDS).build() }

    private suspend inline fun <reified T> postSlowly(path: String, body: JsonElement): T =
        execute(Request.Builder().url(url(path)).post(json(body)).build(), patientClient)

    private suspend inline fun <reified T> patch(path: String, body: JsonElement): T =
        execute(Request.Builder().url(url(path)).patch(json(body)).build())

    private suspend inline fun <reified T> delete(path: String): T =
        execute(Request.Builder().url(url(path)).delete().build())

    /** A `multipart/form-data` POST: text fields and picture files (uploads). */
    private suspend inline fun <reified T> multipart(path: String, parts: MultipartBody.Builder.() -> Unit): T =
        execute(
            Request.Builder()
                .url(url(path))
                .post(MultipartBody.Builder().setType(MultipartBody.FORM).apply(parts).build())
                .build(),
        )

    private fun MultipartBody.Builder.addPicture(name: String, upload: Upload) {
        addFormDataPart(name, upload.fileName, upload.bytes.toRequestBody(upload.mimeType.toMediaType()))
    }

    private fun ValueCardDraft.toJson(): JsonObject = buildJsonObject {
        put("title", title.trim())
        put("care_about", careAbout.trim())
        put("because", because.trim())
        put("looks_like", buildJsonArray { looksLikeLines.forEach { add(JsonPrimitive(it)) } })
        put("drift_looks_like", driftLooksLike.trim())
        put("in_conflict", inConflict.trim())
        put("never_do", neverDo.trim())
        put("frankl_mode", franklMode)
        put("color_key", colorKey)
    }

    /**
     * Runs the call, then reads and decodes the body on [Dispatchers.IO]: OkHttp hands back the
     * response once the headers arrive, and reading the body is network I/O — Android forbids
     * that on the main thread (it threw NetworkOnMainThreadException there). Decoding a large
     * list off the main thread keeps scrolling smooth as well.
     */
    private suspend inline fun <reified T> execute(request: Request, via: OkHttpClient = client): T = withContext(Dispatchers.IO) {
        val text = send(request, via)
        LogoSphereJson.decodeFromString<T>(text.ifBlank { "{}" })
    }

    /** Returns the body of a 2xx response or throws. Call on [Dispatchers.IO]. */
    private suspend fun send(request: Request, via: OkHttpClient = client): String {
        val response = via.newCall(request).await()
        response.use {
            val body = it.body?.string().orEmpty()
            if (it.isSuccessful) return body
            val message = errorMessage(body) ?: defaultMessage(it.code)
            if (it.code == 401) {
                // A 401 on a call that carried a session means the session is gone. A 401 from
                // the sign-in call itself is just a wrong password.
                if (it.request.header("Authorization") != null) onUnauthorized()
                throw UnauthorizedException(message)
            }
            throw ApiException(it.code, message)
        }
    }

    private fun errorMessage(body: String): String? = try {
        val obj = LogoSphereJson.parseToJsonElement(body) as? JsonObject
        (obj?.get("message") ?: obj?.get("error"))?.jsonPrimitive?.content?.takeIf { it.isNotBlank() }
    } catch (e: Exception) {
        null
    }

    private fun defaultMessage(code: Int): String = when (code) {
        401 -> "Please sign in again."
        403 -> "You're not allowed to do that."
        404 -> "That no longer exists."
        409 -> "That changed in the meantime — refresh and try again."
        in 500..599 -> "LogoSphere had a problem. Please try again in a moment."
        else -> "Request failed ($code)."
    }

    companion object {
        fun serverUrl(value: String): HttpUrl = value.trim().trimEnd('/').toHttpUrl()
    }
}

/** Suspends until OkHttp delivers the response; cancelling the coroutine cancels the call. */
private suspend fun Call.await(): Response = suspendCancellableCoroutine { continuation ->
    continuation.invokeOnCancellation { cancel() }
    enqueue(object : Callback {
        override fun onResponse(call: Call, response: Response) {
            continuation.resume(response)
        }

        override fun onFailure(call: Call, e: IOException) {
            if (!continuation.isCancelled) continuation.resumeWithException(e)
        }
    })
}
