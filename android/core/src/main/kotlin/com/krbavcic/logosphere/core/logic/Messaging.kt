package com.krbavcic.logosphere.core.logic

import com.krbavcic.logosphere.core.model.DirectMessage
import com.krbavcic.logosphere.core.model.Exchange
import com.krbavcic.logosphere.core.model.Opening

/** The site's utils/thread.js, and who "Message" goes to. */
object Messaging {
    const val TEXT_MAX = 2000

    /** Pages of older messages and each poll of the newest, as one list: oldest first, each once. */
    fun merge(kept: List<DirectMessage>, fresh: List<DirectMessage>): List<DirectMessage> {
        val byId = LinkedHashMap<String, DirectMessage>()
        kept.forEach { byId[it.id] = it }
        fresh.forEach { byId[it.id] = it }
        // The server's times are all one format, so they sort as text.
        return byId.values.sortedBy { it.at }
    }

    /** The newest of theirs: how far a visit has read. */
    fun lastOfTheirs(messages: List<DirectMessage>): String? = messages.lastOrNull { !it.mine }?.id

    /** Who to write to about an opening, if that's someone else who reads messages. */
    fun openingContact(opening: Opening, viewerId: String?): String? =
        opening.contactId?.takeIf { viewerId != null && it != viewerId }

    /** The human on the other side of an exchange, for a side of it; null when that's an AI persona. */
    fun otherSide(exchange: Exchange, viewerId: String?, isInitiator: Boolean, isOther: Boolean): String? {
        val party = when {
            isInitiator -> Parties.recipient(exchange, viewerId)
            isOther -> Parties.initiator(exchange, viewerId)
            else -> null
        } ?: return null
        val person = party.actingUserId ?: party.id.takeIf { party.group == null }
        return person?.takeIf { it != viewerId }
    }
}
