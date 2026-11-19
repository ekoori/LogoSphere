package com.krbavcic.logosphere.push

import android.Manifest
import android.annotation.SuppressLint
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.google.firebase.FirebaseApp
import com.google.firebase.messaging.FirebaseMessaging
import com.krbavcic.logosphere.MainActivity
import com.krbavcic.logosphere.R
import kotlinx.coroutines.tasks.await
import kotlin.coroutines.cancellation.CancellationException

/**
 * Push notifications through Firebase Cloud Messaging. While a member is signed in, this phone's
 * Firebase token is registered with the server (backend/app/utils/push.py), which pushes every
 * in-app notification to it; signing out forgets it. A tap opens the notification's link.
 *
 * A build without the Firebase project's google-services.json has no Firebase app: everything
 * here quietly does nothing.
 */
object Push {
    /** Must match the server's `push.CHANNEL` and the manifest's default channel. */
    const val CHANNEL = "activity"

    /** The web path a notification opens (the server's `data.link`), as an intent extra. */
    const val EXTRA_LINK = "link"

    fun available(context: Context): Boolean = FirebaseApp.getApps(context).isNotEmpty()

    fun createChannel(context: Context) {
        val channel = NotificationChannel(CHANNEL, "Activity", NotificationManager.IMPORTANCE_DEFAULT).apply {
            description = "Acceptances, receipts, follows and other news from your exchanges"
        }
        context.getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
    }

    /** This phone's Firebase token, or null without Firebase (or while it can't be had). */
    suspend fun token(context: Context): String? {
        if (!available(context)) return null
        return try {
            FirebaseMessaging.getInstance().token.await()
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            null
        }
    }

    fun mayNotify(context: Context): Boolean =
        Build.VERSION.SDK_INT < 33 ||
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED

    /** Shows one notification (the app is in the foreground); a tap opens [link]. */
    @SuppressLint("MissingPermission") // checked by mayNotify
    fun show(context: Context, title: String, body: String, link: String?, key: String?) {
        if (!mayNotify(context)) return
        val id = (key?.takeIf { it.isNotEmpty() } ?: link ?: body).hashCode()
        val open = Intent(context, MainActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP)
            .apply { if (!link.isNullOrEmpty()) putExtra(EXTRA_LINK, link) }
        val tap = PendingIntent.getActivity(context, id, open, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val notification = NotificationCompat.Builder(context, CHANNEL)
            .setSmallIcon(R.drawable.ic_stat_logosphere)
            .setColor(ContextCompat.getColor(context, R.color.notification_accent))
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setAutoCancel(true)
            .setContentIntent(tap)
            .build()
        NotificationManagerCompat.from(context).notify(id, notification)
    }
}
