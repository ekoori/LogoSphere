package com.krbavcic.logosphere.data

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.first

/** The signed-in member, as the app remembers them between launches. */
data class SessionUser(val id: String, val name: String, val isPlatformAdmin: Boolean) {
    val firstName: String get() = name.trim().substringBefore(' ').ifEmpty { name }
}

data class SavedSession(val token: String, val user: SessionUser)

private val Context.sessionPrefs by preferencesDataStore(name = "session")

/**
 * The session token and the signed-in member, in app-private storage (backups are off, so it
 * never leaves the device), plus the server a debug build was pointed at. [token] and [server]
 * are mirrored in memory because the HTTP layer reads them on every request.
 */
class SessionStore(private val context: Context, private val defaultServer: String) {
    @Volatile var token: String? = null
        private set

    @Volatile var server: String = defaultServer
        private set

    suspend fun load(): SavedSession? {
        val prefs = context.sessionPrefs.data.first()
        server = prefs[SERVER] ?: defaultServer
        val saved = prefs[TOKEN]?.let { token ->
            val id = prefs[USER_ID] ?: return@let null
            SavedSession(token, SessionUser(id, prefs[USER_NAME].orEmpty(), prefs[USER_ADMIN] ?: false))
        }
        token = saved?.token
        return saved
    }

    suspend fun save(session: SavedSession) {
        context.sessionPrefs.edit {
            it[TOKEN] = session.token
            it[USER_ID] = session.user.id
            it[USER_NAME] = session.user.name
            it[USER_ADMIN] = session.user.isPlatformAdmin
        }
        token = session.token
    }

    suspend fun updateUser(user: SessionUser) {
        context.sessionPrefs.edit {
            it[USER_ID] = user.id
            it[USER_NAME] = user.name
            it[USER_ADMIN] = user.isPlatformAdmin
        }
    }

    suspend fun clear() {
        token = null
        context.sessionPrefs.edit {
            it.remove(TOKEN)
            it.remove(USER_ID)
            it.remove(USER_NAME)
            it.remove(USER_ADMIN)
        }
    }

    /** Debug builds only: talk to another LogoSphere server (e.g. a local backend). */
    suspend fun setServer(url: String) {
        server = url
        context.sessionPrefs.edit { prefs ->
            if (url == defaultServer) prefs.remove(SERVER) else prefs[SERVER] = url
        }
    }

    private companion object {
        val TOKEN = stringPreferencesKey("token")
        val USER_ID = stringPreferencesKey("user_id")
        val USER_NAME = stringPreferencesKey("user_name")
        val USER_ADMIN = booleanPreferencesKey("user_is_platform_admin")
        val SERVER = stringPreferencesKey("server")
    }
}
