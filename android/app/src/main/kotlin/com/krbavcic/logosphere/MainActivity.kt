package com.krbavcic.logosphere

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.CompositionLocalProvider
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import com.krbavcic.logosphere.data.AuthState
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LogoSphereRoot
import com.krbavcic.logosphere.ui.theme.LogoSphereTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        val container = (application as LogoSphereApplication).container
        // The splash stays up only while the saved session is read — a local read, not a network call.
        installSplashScreen().setKeepOnScreenCondition { container.session.state.value is AuthState.Loading }
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        setContent {
            CompositionLocalProvider(LocalAppContainer provides container) {
                LogoSphereTheme {
                    LogoSphereRoot()
                }
            }
        }
    }
}
