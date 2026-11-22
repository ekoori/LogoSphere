package com.krbavcic.logosphere.data

import com.krbavcic.logosphere.core.api.LogoSphereApi
import com.krbavcic.logosphere.core.model.AppNotification
import com.krbavcic.logosphere.core.model.Community
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.NotificationInbox
import com.krbavcic.logosphere.core.model.Opening
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

/** What an action changed, so screens showing it elsewhere re-fetch. */
enum class Change { Openings, Exchanges, Communities, ValueCards, Profile, Events }

class ChangeBus {
    private val flow = MutableSharedFlow<Change>(extraBufferCapacity = 16)
    val events: SharedFlow<Change> = flow.asSharedFlow()

    fun emit(change: Change) {
        flow.tryEmit(change)
    }
}

/**
 * A value fetched from the API and kept for [freshForMillis], so the several screens that need
 * the same list (the openings form, accept-as, the Me tab…) share one request — the role TanStack
 * Query plays in the web client. Mutations call [invalidate].
 */
private class Cached<T>(private val freshForMillis: Long, private val fetch: suspend () -> T) {
    private val mutex = Mutex()
    private var value: T? = null
    private var fetchedAt = 0L

    suspend fun get(force: Boolean): T = mutex.withLock {
        val current = value
        if (!force && current != null && System.currentTimeMillis() - fetchedAt < freshForMillis) return current
        fetch().also {
            value = it
            fetchedAt = System.currentTimeMillis()
        }
    }

    fun invalidate() {
        fetchedAt = 0L
    }

    fun clear() {
        value = null
        fetchedAt = 0L
    }
}

class CommunityRepository(private val api: LogoSphereApi) {
    private val lists = CommunityKind.entries.associateWith { kind -> Cached(30_000) { api.communities(kind) } }

    suspend fun list(kind: CommunityKind, force: Boolean = false): List<Community> = lists.getValue(kind).get(force)

    /** Spheres, alliances and projects together. */
    suspend fun all(force: Boolean = false): List<Community> = coroutineScope {
        CommunityKind.entries.map { async { list(it, force) } }.awaitAll().flatten()
    }

    fun invalidate(kind: CommunityKind) = lists.getValue(kind).invalidate()

    fun clear() = lists.values.forEach { it.clear() }
}

class OpeningsRepository(private val api: LogoSphereApi) {
    private val list = Cached(15_000) { api.openings() }

    suspend fun list(force: Boolean = false): List<Opening> = list.get(force)

    fun invalidate() = list.invalidate()

    fun clear() = list.clear()
}

/** The notification inbox and its unread count, which the bottom bar shows as a badge. */
class InboxRepository(private val api: LogoSphereApi) {
    private val _unread = MutableStateFlow(0)
    val unread: StateFlow<Int> = _unread.asStateFlow()

    suspend fun load(): NotificationInbox = api.notifications().also { _unread.value = it.unreadCount }

    suspend fun refreshCount() {
        runCatching { load() }
    }

    suspend fun markRead(notification: AppNotification) {
        if (notification.isRead) return
        api.markRead(notification)
        _unread.value = (_unread.value - 1).coerceAtLeast(0)
    }

    suspend fun markAllRead() {
        api.markAllRead()
        _unread.value = 0
    }

    fun clear() {
        _unread.value = 0
    }
}
