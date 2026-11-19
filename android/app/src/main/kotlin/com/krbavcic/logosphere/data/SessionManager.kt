package com.krbavcic.logosphere.data

import com.krbavcic.logosphere.core.api.LogoSphereApi
import com.krbavcic.logosphere.core.api.UnauthorizedException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlin.coroutines.cancellation.CancellationException

sealed interface AuthState {
    /** Reading the saved session; the splash screen stays up. */
    data object Loading : AuthState

    /** [notice] explains why, when the app (not the person) ended the session. */
    data class SignedOut(val notice: String? = null) : AuthState

    data class SignedIn(val user: SessionUser) : AuthState
}

/**
 * Who is signed in. A saved session is trusted at once — the app opens straight onto the feed —
 * and checked with the server in the background; any request answered `401` signs out.
 */
class SessionManager(
    private val store: SessionStore,
    private val api: () -> LogoSphereApi,
    private val scope: CoroutineScope,
    private val onSignedOut: () -> Unit,
    /** Signed in, or a saved session restored: e.g. register this phone for push. */
    private val onSignedIn: () -> Unit = {},
    /** Signing out, while the session still works: e.g. forget this phone for push. */
    private val beforeSignOut: suspend () -> Unit = {},
) {
    private val _state = MutableStateFlow<AuthState>(AuthState.Loading)
    val state: StateFlow<AuthState> = _state.asStateFlow()

    val user: SessionUser? get() = (state.value as? AuthState.SignedIn)?.user

    val server: String get() = store.server

    fun restore() {
        scope.launch {
            val saved = runCatching { store.load() }.getOrNull()
            if (saved == null) {
                _state.value = AuthState.SignedOut()
                return@launch
            }
            _state.value = AuthState.SignedIn(saved.user)
            onSignedIn()
            verify()
        }
    }

    private suspend fun verify() {
        try {
            val status = api().checkSession()
            val data = status.userData
            if (status.isActive && data != null) {
                val fresh = SessionUser(data.userId, data.displayName, data.isPlatformAdmin)
                if (fresh != user) {
                    store.updateUser(fresh)
                    _state.value = AuthState.SignedIn(fresh)
                }
            } else {
                end("Your session ended. Please sign in again.")
            }
        } catch (e: UnauthorizedException) {
            // onUnauthorized already signed out.
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            // Offline, the server is down, or an answer we couldn't read: keep the saved
            // session (screens show their own errors). This runs in the app's own scope, where
            // an uncaught exception would end the process.
        }
    }

    suspend fun signIn(email: String, password: String, server: String? = null) {
        if (server != null && server != store.server) store.setServer(server)
        val response = api().login(email.trim(), password)
        val user = SessionUser(response.data.userId, response.data.displayName, response.data.isPlatformAdmin)
        store.save(SavedSession(response.sessionId, user))
        _state.value = AuthState.SignedIn(user)
        onSignedIn()
    }

    suspend fun register(name: String, email: String, password: String, server: String? = null) {
        if (server != null && server != store.server) store.setServer(server)
        api().register(name.trim(), email.trim(), password)
        signIn(email, password)
    }

    fun signOut() {
        scope.launch {
            runCatching { beforeSignOut() }
            // Revoke it on the server too; if that fails the session still ends here.
            runCatching { api().logout() }
            end(null)
        }
    }

    /** Called by the HTTP layer, from any thread, when the server rejects the session. */
    fun onUnauthorized() {
        if (state.value !is AuthState.SignedIn) return
        scope.launch { end("Your session ended. Please sign in again.") }
    }

    private suspend fun end(notice: String?) {
        store.clear()
        onSignedOut()
        _state.value = AuthState.SignedOut(notice)
    }
}
