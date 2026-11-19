package com.krbavcic.logosphere.core.api

import com.krbavcic.logosphere.core.model.AppNotification
import com.krbavcic.logosphere.core.model.Community
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.DemoStatus
import com.krbavcic.logosphere.core.model.ConfirmResult
import com.krbavcic.logosphere.core.model.Exchange
import com.krbavcic.logosphere.core.model.ExchangeDetail
import com.krbavcic.logosphere.core.model.ExchangeLikeResult
import com.krbavcic.logosphere.core.model.JoinResult
import com.krbavcic.logosphere.core.model.LikeTarget
import com.krbavcic.logosphere.core.model.LoginResponse
import com.krbavcic.logosphere.core.model.NewComment
import com.krbavcic.logosphere.core.model.NewOpening
import com.krbavcic.logosphere.core.model.NotificationInbox
import com.krbavcic.logosphere.core.model.Opening
import com.krbavcic.logosphere.core.model.OpeningLikeResult
import com.krbavcic.logosphere.core.model.PersonRef
import com.krbavcic.logosphere.core.model.PublicUser
import com.krbavcic.logosphere.core.model.SearchResults
import com.krbavcic.logosphere.core.model.SessionStatus
import com.krbavcic.logosphere.core.model.ValueCard
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.encodeToJsonElement
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put
import kotlinx.serialization.json.JsonPrimitive
import okhttp3.Call
import okhttp3.Callback
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import java.io.IOException
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

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

    suspend fun register(name: String, email: String, password: String) {
        post<JsonElement>(
            "/api/register",
            buildJsonObject { put("name", name); put("email", email); put("password", password) },
        )
    }

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

    // ── People ──────────────────────────────────────────────────────────────

    suspend fun user(id: String): PublicUser = get("/api/users/$id")

    /** Toggles following [id]; returns whether the viewer now follows them. */
    suspend fun toggleFollow(id: String): Boolean =
        post<JsonObject>("/api/users/$id/follow", JsonObject(emptyMap()))["following"]
            ?.jsonPrimitive?.content == "true"

    suspend fun following(): List<PersonRef> = get("/api/following")

    /** The value cards on a person's, sphere's, alliance's or project's Meaning Graph. */
    suspend fun valueCards(ownerId: String): List<ValueCard> = get("/api/value_cards/$ownerId")

    // ── Meaning Trail and exchanges ─────────────────────────────────────────

    /** The signed-in member's own trail. */
    suspend fun myTrail(): List<Exchange> = get("/api/meaning_trail")

    /** Someone else's trail — a person's, or an entity's own (sphere, alliance, project). */
    suspend fun trailOf(ownerId: String): List<Exchange> =
        post("/api/meaning_trail", buildJsonObject { put("userId", ownerId) })

    /** Exchanges anyone tagged with a project. */
    suspend fun projectTrail(projectId: String): List<Exchange> = get("/api/meaning_trail/by_project/$projectId")

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

    // ── Openings ────────────────────────────────────────────────────────────

    suspend fun openings(): List<Opening> = get("/api/openings")

    suspend fun opening(id: String): Opening = get("/api/openings/$id")

    suspend fun createOpening(opening: NewOpening) {
        val body = buildJsonObject {
            put("type", opening.type)
            put("cadence", opening.cadence)
            put("title", opening.title.trim())
            put("description", opening.description.trim())
            put("sphere_id", opening.sphereId)
            put("sphere_name", opening.sphereName)
            put("project_name", opening.projectName)
            put("status", "Posted")
        }
        post<JsonElement>("/api/openings", body)
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

    private suspend inline fun <reified T> get(url: HttpUrl): T =
        execute(Request.Builder().url(url).get().build())

    private suspend inline fun <reified T> post(path: String, body: JsonElement): T =
        execute(
            Request.Builder()
                .url(url(path))
                .post(LogoSphereJson.encodeToString(JsonElement.serializer(), body).toRequestBody(jsonType))
                .build(),
        )

    /**
     * Runs the call, then reads and decodes the body on [Dispatchers.IO]: OkHttp hands back the
     * response once the headers arrive, and reading the body is network I/O — Android forbids
     * that on the main thread (it threw NetworkOnMainThreadException there). Decoding a large
     * list off the main thread keeps scrolling smooth as well.
     */
    private suspend inline fun <reified T> execute(request: Request): T = withContext(Dispatchers.IO) {
        val text = send(request)
        LogoSphereJson.decodeFromString<T>(text.ifBlank { "{}" })
    }

    /** Returns the body of a 2xx response or throws. Call on [Dispatchers.IO]. */
    private suspend fun send(request: Request): String {
        val response = client.newCall(request).await()
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
