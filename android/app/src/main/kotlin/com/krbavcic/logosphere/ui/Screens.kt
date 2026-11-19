package com.krbavcic.logosphere.ui

import android.util.Log
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.krbavcic.logosphere.AppContainer
import com.krbavcic.logosphere.BuildConfig
import com.krbavcic.logosphere.core.api.LogoSphereApi
import com.krbavcic.logosphere.core.api.UnauthorizedException
import com.krbavcic.logosphere.core.api.userMessage
import com.krbavcic.logosphere.core.model.Exchange
import com.krbavcic.logosphere.core.model.LikeInfo
import com.krbavcic.logosphere.core.model.LikeTarget
import com.krbavcic.logosphere.core.model.Opening
import com.krbavcic.logosphere.data.Change
import com.krbavcic.logosphere.data.ChangeBus
import kotlinx.coroutines.Job
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.filter
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlin.coroutines.cancellation.CancellationException

val LocalAppContainer = staticCompositionLocalOf<AppContainer> { error("No AppContainer provided") }

/** A screen's data: still coming, failed (with a message for people), or here. */
sealed interface Load<out T> {
    data object Loading : Load<Nothing>
    data class Failed(val message: String) : Load<Nothing>
    data class Ready<T>(val value: T) : Load<T>
}

/**
 * The shape every screen's ViewModel shares: one [state] fetched by [fetch], pull-to-refresh,
 * actions that report failures as [messages] (shown in a snackbar), and an [busy] flag so a
 * button can't be pressed twice.
 */
abstract class LoadViewModel<T> : ViewModel() {
    private val _state = MutableStateFlow<Load<T>>(Load.Loading)
    val state: StateFlow<Load<T>> = _state.asStateFlow()

    private val _refreshing = MutableStateFlow(false)
    val refreshing: StateFlow<Boolean> = _refreshing.asStateFlow()

    private val _busy = MutableStateFlow(false)
    val busy: StateFlow<Boolean> = _busy.asStateFlow()

    private val _messages = Channel<String>(Channel.BUFFERED)
    val messages: Flow<String> = _messages.receiveAsFlow()

    private var loadJob: Job? = null

    protected abstract suspend fun fetch(force: Boolean): T

    val current: T? get() = (state.value as? Load.Ready<T>)?.value

    /** First load, or retry after a failure. */
    fun load() {
        loadJob?.cancel()
        _state.value = Load.Loading
        loadJob = viewModelScope.launch {
            _state.value = try {
                Load.Ready(fetch(force = false))
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                logFailure("load", e)
                Load.Failed(e.userMessage())
            }
        }
    }

    /** Unexpected failures (not the server's answer, not the network) go to logcat in debug builds. */
    protected fun logFailure(what: String, e: Exception) {
        if (BuildConfig.DEBUG) Log.w("LogoSphere", "${javaClass.simpleName} $what failed", e)
    }

    /** Pull-to-refresh: keeps showing what's there and reports a failure as a message. */
    fun refresh() {
        if (_refreshing.value) return
        loadJob?.cancel()
        _refreshing.value = true
        loadJob = viewModelScope.launch {
            try {
                _state.value = Load.Ready(fetch(force = true))
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                logFailure("refresh", e)
                if (state.value is Load.Ready) say(e.userMessage()) else _state.value = Load.Failed(e.userMessage())
            } finally {
                _refreshing.value = false
            }
        }
    }

    /** Re-fetch quietly whenever another screen reports one of [kinds] changed. */
    protected fun reloadOn(bus: ChangeBus, vararg kinds: Change) {
        viewModelScope.launch {
            bus.events.filter { it in kinds }.collect { if (state.value is Load.Ready) reload() }
        }
    }

    /** Re-fetch quietly after an action changed something. */
    protected suspend fun reload() {
        try {
            _state.value = Load.Ready(fetch(force = true))
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            logFailure("reload", e)
            say(e.userMessage())
        }
    }

    protected fun update(transform: (T) -> T) {
        _state.update { if (it is Load.Ready) Load.Ready(transform(it.value)) else it }
    }

    protected fun say(message: String) {
        _messages.trySend(message)
    }

    /**
     * Likes or unlikes an opening at once, then settles on what the server says (or puts it back).
     * [apply] maps every opening in the screen's data through the given change.
     */
    protected fun toggleOpeningLike(api: LogoSphereApi, opening: Opening, apply: (T, (Opening) -> Opening) -> T) {
        val want = !opening.likedByMe
        fun set(liked: Boolean, likes: Int) = update { data ->
            apply(data) { if (it.id == opening.id) it.copy(likedByMe = liked, likes = likes) else it }
        }
        set(want, (opening.likes + if (want) 1 else -1).coerceAtLeast(0))
        viewModelScope.launch {
            try {
                val result = api.likeOpening(opening.id, want)
                set(result.liked, result.likes)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                set(opening.likedByMe, opening.likes)
                if (e !is UnauthorizedException) say(e.userMessage())
            }
        }
    }

    /** The same for a like on an exchange, or on its receipt, note or acknowledgement. */
    protected fun toggleExchangeLike(
        api: LogoSphereApi,
        exchange: Exchange,
        target: LikeTarget,
        apply: (T, (Exchange) -> Exchange) -> T,
    ) {
        val before = exchange.likesFor(target)
        fun set(liked: Boolean, count: Int) = update { data ->
            apply(data) {
                if (it.id == exchange.id) it.copy(likes = it.likes + (target.key to LikeInfo(count, liked, before.by))) else it
            }
        }
        set(!before.liked, (before.count + if (before.liked) -1 else 1).coerceAtLeast(0))
        viewModelScope.launch {
            try {
                val result = api.likeExchange(exchange.id, target)
                set(result.liked, result.count)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                set(before.liked, before.count)
                if (e !is UnauthorizedException) say(e.userMessage())
            }
        }
    }

    /**
     * Runs a change against the server. Failures become a message (a `401` needs none: the app is
     * already returning to sign-in).
     */
    protected fun act(onSuccess: suspend () -> Unit = {}, block: suspend () -> Unit) {
        if (_busy.value) return
        _busy.value = true
        viewModelScope.launch {
            try {
                block()
                onSuccess()
            } catch (e: CancellationException) {
                throw e
            } catch (e: UnauthorizedException) {
                // Signed out; nothing to say here.
            } catch (e: Exception) {
                logFailure("action", e)
                say(e.userMessage())
            } finally {
                _busy.value = false
            }
        }
    }
}
