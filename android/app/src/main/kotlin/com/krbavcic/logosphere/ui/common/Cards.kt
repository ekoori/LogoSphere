package com.krbavcic.logosphere.ui.common

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.krbavcic.logosphere.core.logic.Dates
import com.krbavcic.logosphere.core.logic.ExchangeRules
import com.krbavcic.logosphere.core.logic.OpeningRules
import com.krbavcic.logosphere.core.logic.Parties
import com.krbavcic.logosphere.core.logic.Party
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.Exchange
import com.krbavcic.logosphere.core.model.LikeTarget
import com.krbavcic.logosphere.core.model.Opening
import com.krbavcic.logosphere.ui.theme.Brand

/** A person or group, small: avatar and name. */
@Composable
fun PartyTag(party: Party, modifier: Modifier = Modifier) {
    Row(modifier, verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        val group = party.group
        if (group != null) GroupAvatar(group, size = 22.dp) else Avatar(party.id, party.name, size = 22.dp)
        Text(
            party.label,
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.onSurface,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f, fill = false),
        )
        if (party.personaByName) PersonaTag(compact = true)
    }
}

/** A quoted line with an accent bar: a receipt (leaf) or an acknowledgement (honey). */
@Composable
fun QuoteLine(author: String, text: String, accent: Color, modifier: Modifier = Modifier, maxLines: Int = 2) {
    Row(modifier.height(IntrinsicSize.Min)) {
        Box(
            Modifier
                .width(3.dp)
                .fillMaxHeight()
                .clip(CircleShape)
                .background(accent),
        )
        Spacer(Modifier.width(10.dp))
        Column {
            Text(author, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(
                text,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = maxLines,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

@Composable
fun ExchangeStatusPill(exchange: Exchange) {
    when {
        ExchangeRules.isCancelled(exchange) -> Pill("Cancelled", MaterialTheme.colorScheme.errorContainer, MaterialTheme.colorScheme.onErrorContainer)
        ExchangeRules.isCompleted(exchange) -> DonePill(text = ExchangeRules.status(exchange).let { if (it == ExchangeRules.FOLLOW_UP) "Followed up" else it })
        else -> Pill(ExchangeRules.status(exchange), Brand.colors.offerWash, Brand.colors.onOfferWash)
    }
}

/** One exchange in a Meaning Trail. */
@Composable
fun ExchangeCard(
    exchange: Exchange,
    viewerId: String?,
    onClick: () -> Unit,
    onLike: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val initiator = Parties.initiator(exchange, viewerId)
    val recipient = Parties.recipient(exchange, viewerId)
    val likes = exchange.likesFor(LikeTarget.Exchange)
    BrandCard(modifier = modifier.fillMaxWidth(), onClick = onClick) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                ExchangeStatusPill(exchange)
                if (exchange.isDemo) DemoTag()
                Spacer(Modifier.weight(1f))
                MetaText(Dates.day(exchange.startedAt))
            }
            Text(
                exchange.title ?: "An exchange of trust",
                style = MaterialTheme.typography.titleMedium,
                maxLines = 3,
                overflow = TextOverflow.Ellipsis,
            )
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                PartyTag(initiator, Modifier.weight(1f, fill = false))
                if (recipient != null) {
                    Icon(
                        Icons.AutoMirrored.Filled.ArrowForward,
                        contentDescription = "with",
                        tint = MaterialTheme.colorScheme.outline,
                        modifier = Modifier.padding(horizontal = 2.dp).width(16.dp),
                    )
                    PartyTag(recipient, Modifier.weight(1f, fill = false))
                }
            }
            exchange.projectName?.let { QuietPill("${CommunityKind.Project.glyph} $it") }
            exchange.receipt?.let {
                QuoteLine(
                    author = "Receipt · ${recipient?.label ?: "Recipient"}",
                    text = it,
                    accent = Brand.colors.receiptAccent,
                )
            }
            exchange.acknowledgement?.let {
                QuoteLine(
                    author = "Acknowledgement · ${exchange.acknowledgementAuthorName ?: "A neighbour"}" +
                        if (exchange.acknowledgements.size > 1) " (+${exchange.acknowledgements.size - 1} more)" else "",
                    text = it,
                    accent = Brand.colors.acknowledgementAccent,
                )
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                // The status is already the pill at the top of the card.
                ProgressStrip(ExchangeRules.progress(exchange), Modifier.weight(1f), showLabel = false)
                Spacer(Modifier.width(8.dp))
                LikeControl(likes, onLike)
            }
        }
    }
}

/** One offer or need. */
@Composable
fun OpeningCard(
    opening: Opening,
    viewerId: String?,
    onClick: () -> Unit,
    onLike: () -> Unit,
    modifier: Modifier = Modifier,
) {
    BrandCard(modifier = modifier.fillMaxWidth(), onClick = onClick) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                OpeningTypePill(opening.isOffer)
                if (opening.isPerpetual) QuietPill("↻ Ongoing")
                if (opening.isDemo) DemoTag()
                Spacer(Modifier.weight(1f))
                // Your own opening isn't yours to appreciate (an old self-like can come off).
                if (!OpeningRules.isOwn(opening, viewerId) || opening.likedByMe) {
                    LikeButton(opening.likedByMe, opening.likes, onLike)
                } else {
                    LikeCount(opening.likes)
                }
            }
            Text(opening.title, style = MaterialTheme.typography.titleMedium, maxLines = 2, overflow = TextOverflow.Ellipsis)
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Avatar(opening.actingUserId ?: opening.providerId, opening.actingUser ?: opening.provider, size = 22.dp)
                val by = when {
                    opening.actingUser != null -> "${opening.actingUser} for ${opening.provider}"
                    OpeningRules.isOwn(opening, viewerId) -> "You"
                    else -> opening.provider ?: "A member"
                }
                if (opening.providerIsAgent && !OpeningRules.isOwn(opening, viewerId)) PersonaTag(compact = true)
                MetaText(
                    listOfNotNull(by, opening.sphereName, opening.projectName).joinToString("  ·  "),
                    modifier = Modifier.weight(1f),
                )
            }
            WhereLine(opening.location, opening.distance)
            opening.description?.takeIf { it.isNotBlank() }?.let {
                Text(
                    it,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 3,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            ProgressStrip(OpeningRules.progress(opening))
            openingNote(opening, viewerId)?.let {
                Text(it, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.tertiary)
            }
        }
    }
}

/** The one line that tells the viewer where they stand with an opening. */
fun openingNote(opening: Opening, viewerId: String?): String? {
    val mine = opening.myAcceptance
    val pending = opening.pendingAcceptances.size
    return when {
        opening.status == "Cancelled" -> "Withdrawn"
        OpeningRules.mayManage(opening, viewerId) && pending > 0 ->
            if (pending == 1) "1 acceptance awaits your confirmation" else "$pending acceptances await your confirmation"
        mine?.status == "pending" -> "You accepted — awaiting ${opening.provider ?: "the provider"}"
        mine?.status == "confirmed" -> "Confirmed — see your exchange"
        else -> null
    }
}
