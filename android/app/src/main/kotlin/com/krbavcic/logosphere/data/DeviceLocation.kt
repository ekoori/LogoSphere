package com.krbavcic.logosphere.data

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Build
import android.os.Bundle
import android.os.Looper
import androidx.core.content.ContextCompat
import com.krbavcic.logosphere.core.logic.PinPrecision
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.withTimeoutOrNull

/**
 * Where the phone is, once, when someone presses for it. Never followed, and never asked for
 * more exactly than the precision they chose needs. The platform's own LocationManager, so
 * nothing of Google's is involved.
 */
object DeviceLocation {
    private const val WAIT_MS = 12_000L
    private const val RECENT_MS = 10 * 60_000L

    fun permissionsFor(precision: PinPrecision): Array<String> =
        if (precision.needsFineLocation) {
            // Android 12+ lets people answer "approximate", and only when both are asked for.
            arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION)
        } else {
            arrayOf(Manifest.permission.ACCESS_COARSE_LOCATION)
        }

    private fun granted(context: Context, permission: String) =
        ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED

    fun mayRead(context: Context): Boolean =
        granted(context, Manifest.permission.ACCESS_FINE_LOCATION) || granted(context, Manifest.permission.ACCESS_COARSE_LOCATION)

    /** Already allowed as exactly as [precision] needs, so there's nothing to ask. */
    fun allowed(context: Context, precision: PinPrecision): Boolean =
        granted(context, Manifest.permission.ACCESS_FINE_LOCATION) ||
            (!precision.needsFineLocation && granted(context, Manifest.permission.ACCESS_COARSE_LOCATION))

    /** The first reading good enough for [precision], else the best that came in time. Call it on the main thread. */
    @SuppressLint("MissingPermission") // mayRead() is checked, and a refusal is caught
    suspend fun read(context: Context, precision: PinPrecision): Location? {
        if (!mayRead(context)) return null
        val manager = ContextCompat.getSystemService(context, LocationManager::class.java) ?: return null
        val fine = granted(context, Manifest.permission.ACCESS_FINE_LOCATION)
        val wanted = buildList {
            if (Build.VERSION.SDK_INT >= 31) add(LocationManager.FUSED_PROVIDER)
            add(LocationManager.NETWORK_PROVIDER)
            if (fine) add(LocationManager.GPS_PROVIDER)
        }
        val providers = wanted.filter { provider ->
            runCatching { provider in manager.allProviders && manager.isProviderEnabled(provider) }.getOrDefault(false)
        }
        if (providers.isEmpty()) return null

        var best: Location? = null
        val enough = CompletableDeferred<Unit>()
        val listener = object : LocationListener {
            override fun onLocationChanged(location: Location) {
                if (location.accuracyOr(Float.MAX_VALUE) <= (best?.accuracyOr(Float.MAX_VALUE) ?: Float.MAX_VALUE)) best = location
                if (location.accuracyOr(0f) <= precision.roomMetres) enough.complete(Unit)
            }

            // Abstract before Android 11: left out, they crash older phones.
            override fun onProviderEnabled(provider: String) = Unit

            override fun onProviderDisabled(provider: String) = Unit

            @Deprecated("Never called from Android 10 on")
            override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) = Unit
        }
        try {
            providers.forEach { manager.requestLocationUpdates(it, 0L, 0f, listener, Looper.getMainLooper()) }
            withTimeoutOrNull(WAIT_MS) { enough.await() }
            return best ?: providers
                .mapNotNull { manager.getLastKnownLocation(it) }
                .filter { System.currentTimeMillis() - it.time < RECENT_MS }
                .maxByOrNull { it.time }
        } catch (e: SecurityException) {
            return null // refused in the meantime
        } finally {
            manager.removeUpdates(listener)
        }
    }

    private fun Location.accuracyOr(otherwise: Float): Float = if (hasAccuracy()) accuracy else otherwise
}
