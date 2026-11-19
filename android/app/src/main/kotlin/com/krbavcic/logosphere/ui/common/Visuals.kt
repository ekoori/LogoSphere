package com.krbavcic.logosphere.ui.common

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.SubcomposeAsyncImage
import com.krbavcic.logosphere.core.logic.Dates
import com.krbavcic.logosphere.core.logic.Progress
import com.krbavcic.logosphere.core.model.CommunityKind
import com.krbavcic.logosphere.core.model.FranklMode
import com.krbavcic.logosphere.core.model.ValueCard
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.theme.FrauncesDisplay
import com.krbavcic.logosphere.ui.theme.Palette
import com.krbavcic.logosphere.ui.theme.kindGradient
import com.krbavcic.logosphere.ui.theme.valueCardAccent

private fun initials(name: String?): String =
    name.orEmpty().split(' ').filter { it.isNotBlank() }.take(2).joinToString("") { it.first().uppercase() }.ifEmpty { "·" }

/** A member's avatar: their photo, or the server's initials image; initials while it loads. */
@Composable
fun Avatar(userId: String?, name: String?, size: Dp = 40.dp, modifier: Modifier = Modifier) {
    val api = LocalAppContainer.current.api
    val placeholder = @Composable {
        Box(
            Modifier
                .fillMaxSize()
                .background(MaterialTheme.colorScheme.primaryContainer),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                initials(name),
                color = MaterialTheme.colorScheme.onPrimaryContainer,
                fontSize = (size.value * 0.38f).sp,
                fontWeight = FontWeight.SemiBold,
            )
        }
    }
    Box(modifier.size(size).clip(CircleShape)) {
        if (userId == null) {
            placeholder()
        } else {
            SubcomposeAsyncImage(
                model = api.avatarUrl(userId),
                contentDescription = null,
                contentScale = ContentScale.Crop,
                modifier = Modifier.fillMaxSize(),
                loading = { placeholder() },
                error = { placeholder() },
            )
        }
    }
}

/** A sphere, alliance or project in an avatar's place: its glyph on its gradient. */
@Composable
fun GroupAvatar(kind: CommunityKind, size: Dp = 40.dp, modifier: Modifier = Modifier) {
    Box(
        modifier
            .size(size)
            .clip(RoundedCornerShape(size * 0.28f))
            .background(kindGradient(kind)),
        contentAlignment = Alignment.Center,
    ) {
        Text(kind.glyph, color = Color(0xFFF7F4E8), fontSize = (size.value * 0.45f).sp)
    }
}

/**
 * A banner image, or — like the web's EntityBanner — the kind's gradient with its glyph when
 * there's no photo. [kind] null means an opening. Overlaid [content] sits on a darkening scrim.
 */
@Composable
fun Banner(
    imageUrl: String?,
    kind: CommunityKind?,
    modifier: Modifier = Modifier,
    height: Dp = 160.dp,
    content: (@Composable BoxScope.() -> Unit)? = null,
) {
    val glyph = kind?.glyph ?: "◍"
    val fallback = @Composable {
        Box(
            Modifier
                .fillMaxSize()
                .background(kindGradient(kind)),
            contentAlignment = Alignment.Center,
        ) {
            Text(glyph, color = Color(0x29F7F4E8), fontSize = (height.value * 0.7f).sp, fontFamily = FrauncesDisplay)
        }
    }
    Box(
        modifier
            .fillMaxWidth()
            .height(height),
    ) {
        if (imageUrl == null) {
            fallback()
        } else {
            SubcomposeAsyncImage(
                model = imageUrl,
                contentDescription = null,
                contentScale = ContentScale.Crop,
                modifier = Modifier.fillMaxSize(),
                loading = { fallback() },
                error = { fallback() },
            )
        }
        if (content != null) {
            Box(
                Modifier
                    .fillMaxSize()
                    .background(Brush.verticalGradient(0.3f to Color.Transparent, 1f to Color(0x9E14180E))),
            )
            content()
        }
    }
}

/** A value card as a small chip: accent dot, Frankl glyph, title. */
@Composable
fun ValueChip(card: ValueCard, onClick: () -> Unit, modifier: Modifier = Modifier, selected: Boolean = false) {
    val accent = valueCardAccent(card.colorKey)
    Surface(
        onClick = onClick,
        shape = CircleShape,
        color = if (selected) accent.copy(alpha = 0.22f) else MaterialTheme.colorScheme.surfaceContainerLow,
        modifier = modifier.border(1.dp, if (selected) accent else accent.copy(alpha = 0.45f), CircleShape),
    ) {
        Row(
            Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Text(FranklMode.of(card.franklMode)?.glyph ?: "✶", color = accent, style = MaterialTheme.typography.labelLarge)
            Text(
                card.title.ifBlank { "Untitled value" },
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            if (selected) Text("✓", color = accent, style = MaterialTheme.typography.labelLarge)
        }
    }
}

/** A wrapping row of value chips; tapping one opens the whole card. */
@OptIn(ExperimentalLayoutApi::class)
@Composable
fun ValueChips(cards: List<ValueCard>, modifier: Modifier = Modifier, subjectLabel: String = "Cares about") {
    var open by remember { mutableStateOf<ValueCard?>(null) }
    FlowRow(modifier = modifier, horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        cards.forEach { card -> ValueChip(card, onClick = { open = card }) }
    }
    open?.let { ValueCardSheet(it, subjectLabel = subjectLabel, onDismiss = { open = null }) }
}

/** The full value card — its CLEAR fields — in a bottom sheet. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ValueCardSheet(card: ValueCard, onDismiss: () -> Unit, subjectLabel: String = "Cares about") {
    val accent = valueCardAccent(card.colorKey)
    val mode = FranklMode.of(card.franklMode)
    ModalBottomSheet(onDismissRequest = onDismiss, containerColor = MaterialTheme.colorScheme.surfaceContainerLow) {
        Column(
            Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp)
                .padding(bottom = 24.dp)
                .navigationBarsPadding(),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Box(Modifier.size(10.dp).clip(CircleShape).background(accent))
                Text(
                    listOfNotNull(mode?.let { "${it.glyph} ${it.label.lowercase()}" }, "value card").joinToString(" · "),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Text(card.title, style = MaterialTheme.typography.headlineSmall, color = MaterialTheme.colorScheme.onSurface)
            val state = when {
                card.endorsed == true -> "Endorsed on reflection"
                card.needsReview -> "Due for review"
                else -> null
            }
            state?.let { QuietPill(it) }
            CardField(subjectLabel, card.careAbout)
            CardField("Because", card.because)
            if (card.looksLike.isNotEmpty()) {
                CardField("Looks like", card.looksLike.joinToString("\n") { "•  $it" })
            }
            CardField("Drift looks like", card.driftLooksLike, tint = Palette.HoneyDeep)
            CardField("When in conflict, choose", card.inConflict)
            CardField("Never do", card.neverDo, tint = MaterialTheme.colorScheme.error)
        }
    }
}

@Composable
private fun CardField(label: String, text: String?, tint: Color = MaterialTheme.colorScheme.onSurfaceVariant) {
    if (text.isNullOrBlank()) return
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(label.uppercase(), style = MaterialTheme.typography.labelSmall, color = tint)
        Text(text, style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.onSurface)
    }
}

/** A compact lifecycle bar for cards: one segment per phase, the label of the current one. */
@Composable
fun ProgressStrip(progress: Progress, modifier: Modifier = Modifier, showLabel: Boolean = true) {
    val reached = if (progress.cancelled) MaterialTheme.colorScheme.outline else MaterialTheme.colorScheme.primary
    Column(modifier, verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(4.dp), modifier = Modifier.fillMaxWidth()) {
            progress.steps.forEachIndexed { index, _ ->
                Box(
                    Modifier
                        .weight(1f)
                        .height(4.dp)
                        .clip(CircleShape)
                        .background(if (index <= progress.current) reached else MaterialTheme.colorScheme.outlineVariant),
                )
            }
        }
        if (showLabel) {
            Text(
                progress.currentLabel,
                style = MaterialTheme.typography.labelMedium,
                color = if (progress.cancelled) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary,
            )
        }
    }
}

/** The lifecycle as a vertical timeline with the date each phase was reached. */
@Composable
fun ProgressTimeline(progress: Progress, modifier: Modifier = Modifier) {
    Column(modifier) {
        progress.steps.forEachIndexed { index, step ->
            val done = index <= progress.current && !progress.cancelled
            val isCurrent = index == progress.current
            Row(verticalAlignment = Alignment.Top) {
                Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.width(20.dp)) {
                    Box(
                        Modifier
                            .padding(top = 4.dp)
                            .size(if (isCurrent) 14.dp else 10.dp)
                            .clip(CircleShape)
                            .background(
                                when {
                                    progress.cancelled && isCurrent -> MaterialTheme.colorScheme.error
                                    done -> MaterialTheme.colorScheme.primary
                                    else -> MaterialTheme.colorScheme.outlineVariant
                                },
                            ),
                    )
                    if (index < progress.steps.lastIndex) {
                        Box(
                            Modifier
                                .width(2.dp)
                                .height(22.dp)
                                .background(
                                    if (index < progress.current && !progress.cancelled) MaterialTheme.colorScheme.primary
                                    else MaterialTheme.colorScheme.outlineVariant,
                                ),
                        )
                    }
                }
                Spacer(Modifier.width(10.dp))
                Row(Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        step.label,
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = if (isCurrent) FontWeight.Bold else FontWeight.Normal,
                        color = if (done || isCurrent) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.weight(1f),
                    )
                    val day = Dates.day(step.reachedAt)
                    if (day.isNotEmpty()) MetaText(day)
                }
            }
        }
        if (progress.cancelled) {
            Text("Cancelled", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 4.dp))
        }
    }
}
