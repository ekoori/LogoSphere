package com.krbavcic.logosphere.ui.common

import android.annotation.SuppressLint
import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.os.Handler
import android.os.Looper
import android.view.ViewGroup
import android.webkit.JavascriptInterface
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.krbavcic.logosphere.core.logic.PinPrecision
import com.krbavcic.logosphere.core.logic.Places
import com.krbavcic.logosphere.core.model.Place
import com.krbavcic.logosphere.ui.LocalAppContainer
import java.io.ByteArrayInputStream

private const val TILE_HOST = "tile.openstreetmap.org"
private const val PAGE = "/map-picker"

/** All the map page can do to the app: hand it a point on Earth. */
internal class MapBridge(private val onPicked: (Double, Double) -> Unit) {
    private val main = Handler(Looper.getMainLooper())

    @JavascriptInterface
    fun picked(lat: Double, lon: Double) {
        if (!lat.isFinite() || !lon.isFinite() || lat !in -90.0..90.0 || lon !in -180.0..180.0) return
        main.post { onPicked(lat, lon) }
    }
}

/**
 * The site's map-only page, full screen, for putting a pin. The web view is shut in: it loads
 * LogoSphere's own page and OpenStreetMap's tiles and nothing else (not even web fonts), has no
 * session, files or location, and any link it has opens in the browser.
 */
@Composable
fun MapPickerDialog(near: Place?, precision: PinPrecision, onPick: (Double, Double) -> Unit, onDismiss: () -> Unit) {
    val api = LocalAppContainer.current.api
    val picked by rememberUpdatedState(onPick)
    var failed by remember { mutableStateOf(false) }
    // Where to start travels in the fragment, which never reaches a server.
    val start = remember {
        val lat = near?.lat
        val lon = near?.lon
        val km = precision.km?.toInt()?.toString().orEmpty()
        api.webUrl(if (lat != null && lon != null) "$PAGE#$lat,$lon,$km" else "$PAGE#,,$km")
    }

    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(usePlatformDefaultWidth = false, decorFitsSystemWindows = false),
    ) {
        Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
            Column(Modifier.safeDrawingPadding()) {
                BackTopBar("Put a pin", onDismiss)
                Box(Modifier.fillMaxWidth().weight(1f)) {
                    if (failed) {
                        EmptyNote("The map didn't load. Check you're connected, or use where you are now.")
                    } else {
                        LockedMap(start, onPicked = { lat, lon -> picked(lat, lon) }, onFailed = { failed = true })
                    }
                }
            }
        }
    }
}

@SuppressLint("SetJavaScriptEnabled") // our own page is the only one it can load
@Composable
private fun LockedMap(start: String, onPicked: (Double, Double) -> Unit, onFailed: () -> Unit) {
    val home = remember(start) { Uri.parse(start) }
    AndroidView(
        modifier = Modifier.fillMaxSize(),
        onRelease = { it.destroy() },
        factory = { context ->
            fun ours(uri: Uri) = uri.scheme == home.scheme && uri.host == home.host && uri.port == home.port

            WebView(context).apply {
                // Without this the page's full-height map measures as nothing.
                layoutParams = ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
                settings.javaScriptEnabled = true
                settings.domStorageEnabled = true // the site's theme choice
                settings.allowFileAccess = false
                settings.allowContentAccess = false
                settings.setGeolocationEnabled(false)
                settings.mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
                addJavascriptInterface(MapBridge(onPicked), "LogoSphereMap")
                webViewClient = object : WebViewClient() {
                    override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse? {
                        val uri = request.url
                        val allowed = ours(uri) || (uri.scheme == "https" && uri.host == TILE_HOST) || uri.scheme == "data"
                        return if (allowed) null else WebResourceResponse("text/plain", "utf-8", ByteArrayInputStream(ByteArray(0)))
                    }

                    override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                        val uri = request.url
                        if (ours(uri) && uri.path == PAGE) return false
                        if (uri.scheme == "https" && request.hasGesture()) {
                            try {
                                view.context.startActivity(Intent(Intent.ACTION_VIEW, uri).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                            } catch (e: ActivityNotFoundException) {
                                // No browser: nothing to open it with.
                            }
                        }
                        return true
                    }

                    override fun onReceivedError(view: WebView, request: WebResourceRequest, error: WebResourceError) {
                        if (request.isForMainFrame) onFailed()
                    }
                }
                loadUrl(start)
            }
        },
    )
}
