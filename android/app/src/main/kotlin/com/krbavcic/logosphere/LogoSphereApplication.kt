package com.krbavcic.logosphere

import android.app.Application
import android.content.Context
import coil.ImageLoader
import coil.ImageLoaderFactory
import coil.decode.SvgDecoder
import coil.disk.DiskCache
import com.krbavcic.logosphere.core.api.BearerAuthInterceptor
import com.krbavcic.logosphere.core.api.LogoSphereApi
import com.krbavcic.logosphere.data.ChangeBus
import com.krbavcic.logosphere.data.CommunityRepository
import com.krbavcic.logosphere.data.InboxRepository
import com.krbavcic.logosphere.data.OpeningsRepository
import com.krbavcic.logosphere.data.SessionManager
import com.krbavcic.logosphere.data.SessionStore
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.Dispatchers
import okhttp3.OkHttpClient
import java.util.concurrent.TimeUnit

/** Everything the screens share, built once per process. */
class AppContainer(context: Context) {
    private val appScope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)

    val sessionStore = SessionStore(context, BuildConfig.DEFAULT_SERVER_URL)

    private fun serverUrl() = LogoSphereApi.serverUrl(sessionStore.server)

    /** One HTTP client for the API and for images, so authenticated images load too. */
    val http: OkHttpClient = OkHttpClient.Builder()
        .addInterceptor(BearerAuthInterceptor(server = ::serverUrl, token = { sessionStore.token }))
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    val api = LogoSphereApi(http, server = ::serverUrl, onUnauthorized = { session.onUnauthorized() })

    val communities = CommunityRepository(api)
    val openings = OpeningsRepository(api)
    val inbox = InboxRepository(api)
    val changes = ChangeBus()

    val session: SessionManager = SessionManager(
        store = sessionStore,
        api = { api },
        scope = appScope,
        // Nothing of one member's may show to the next.
        onSignedOut = {
            communities.clear()
            openings.clear()
            inbox.clear()
        },
    )
}

class LogoSphereApplication : Application(), ImageLoaderFactory {
    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)
        container.session.restore()
    }

    override fun newImageLoader(): ImageLoader = ImageLoader.Builder(this)
        .okHttpClient(container.http)
        // The server draws initials avatars as SVG for members without a photo.
        .components { add(SvgDecoder.Factory()) }
        .diskCache {
            DiskCache.Builder().directory(cacheDir.resolve("images")).maxSizeBytes(64L * 1024 * 1024).build()
        }
        .crossfade(true)
        .build()
}
