package com.krbavcic.logosphere

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.CompositionLocalProvider
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import com.krbavcic.logosphere.core.logic.Links
import com.krbavcic.logosphere.data.AuthState
import com.krbavcic.logosphere.push.Push
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LogoSphereRoot
import com.krbavcic.logosphere.ui.theme.LogoSphereTheme

class MainActivity : ComponentActivity() {
    private val container get() = (application as LogoSphereApplication).container

    override fun onCreate(savedInstanceState: Bundle?) {
        val container = container
        // The splash stays up only while the saved session is read — a local read, not a network call.
        installSplashScreen().setKeepOnScreenCondition { container.session.state.value is AuthState.Loading }
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        if (savedInstanceState == null) openLink(intent)
        setContent {
            CompositionLocalProvider(LocalAppContainer provides container) {
                LogoSphereTheme {
                    LogoSphereRoot()
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        openLink(intent)
    }

    /** A tapped notification's link (ours, or the system's while we were in the background). */
    private fun openLink(intent: Intent?) {
        val link = intent?.getStringExtra(Push.EXTRA_LINK)?.takeIf { it.isNotEmpty() } ?: return
        intent.removeExtra(Push.EXTRA_LINK)
        Links.parse(link)?.let { container.pendingLink.value = it }
    }
}
