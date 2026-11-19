package com.krbavcic.logosphere.push

import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import com.krbavcic.logosphere.LogoSphereApplication

/**
 * Firebase's messages for this phone. In the background the system shows them itself (the
 * manifest's defaults); in the foreground they arrive here, and are shown the same way.
 */
class PushService : FirebaseMessagingService() {
    private val container get() = (application as LogoSphereApplication).container

    /** Firebase replaced this phone's token: tell the server, if someone is signed in. */
    override fun onNewToken(token: String) {
        container.registerPush(token)
    }

    override fun onMessageReceived(message: RemoteMessage) {
        // Signed out since: not this phone's news any more.
        if (container.session.user == null) return
        val body = message.notification?.body ?: message.data["body"] ?: return
        val title = message.notification?.title ?: message.data["title"] ?: "LogoSphere"
        Push.show(this, title, body, message.data["link"], message.data["notification_id"])
        container.refreshInbox()
    }
}
