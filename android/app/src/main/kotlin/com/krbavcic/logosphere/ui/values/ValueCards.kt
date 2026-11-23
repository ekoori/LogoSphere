package com.krbavcic.logosphere.ui.values

import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.Edit
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.krbavcic.logosphere.core.logic.Dates
import com.krbavcic.logosphere.core.model.FranklMode
import com.krbavcic.logosphere.core.model.ValueCard
import com.krbavcic.logosphere.ui.common.BrandCard
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.Pill
import com.krbavcic.logosphere.ui.common.QuietPill
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.LinkText
import com.krbavcic.logosphere.ui.theme.Brand
import com.krbavcic.logosphere.ui.theme.Palette
import com.krbavcic.logosphere.ui.theme.valueCardAccent
import com.krbavcic.logosphere.ui.common.LocalSimple

/** What a value card's owner may do with it from a list; null when the viewer only reads it. */
class ValueCardActions(
    val onEdit: (ValueCard) -> Unit,
    val onDelete: (ValueCard) -> Unit,
    val onEndorse: (ValueCard) -> Unit,
    val onReview: (ValueCard) -> Unit,
)

/**
 * One value card, the web's `vc-card`: its Frankl mode, title and what it cares about, the rest
 * on tap. With [actions], its owner (or a group's manager) can edit, remove, endorse and review it.
 * [subject] is "I care about" on a person's graph, "We care about" on a group's.
 */
@Composable
fun ValueCardItem(
    card: ValueCard,
    subject: String,
    actions: ValueCardActions?,
    busy: Boolean,
    modifier: Modifier = Modifier,
) {
    val accent = valueCardAccent(card.colorKey)
    val mode = FranklMode.of(card.franklMode) ?: FranklMode.Creative
    var expanded by rememberSaveable(card.id) { mutableStateOf(false) }
    var confirmDelete by rememberSaveable(card.id) { mutableStateOf(false) }
    val simple = LocalSimple.current

    BrandCard(modifier.fillMaxWidth(), onClick = { expanded = !expanded }) {
        // The accent edge is drawn, not laid out: sizing the card by its intrinsic height made the
        // state row (a FlowRow, which drops what doesn't fit) lose its wrapped buttons.
        Column(
            Modifier
                .fillMaxWidth()
                .drawBehind { drawRect(accent, size = Size(5.dp.toPx(), size.height)) }
                .animateContentSize()
                .padding(start = 17.dp, end = 8.dp, top = 12.dp, bottom = 12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(10.dp).clip(CircleShape).background(accent))
                Text(
                    if (simple) "" else "  ${mode.glyph} ${mode.label}",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.weight(1f),
                )
                if (actions != null) {
                    IconButton(onClick = { actions.onEdit(card) }, enabled = !busy, modifier = Modifier.size(36.dp)) {
                        Icon(Icons.Outlined.Edit, contentDescription = "Edit this card", modifier = Modifier.size(18.dp))
                    }
                    IconButton(onClick = { confirmDelete = true }, enabled = !busy, modifier = Modifier.size(36.dp)) {
                        Icon(Icons.Outlined.Delete, contentDescription = "Remove this card", modifier = Modifier.size(18.dp))
                    }
                }
            }
            Text(card.title.ifBlank { "Untitled value" }, style = MaterialTheme.typography.titleMedium)
            Field(subject, card.careAbout)
            if (expanded) {
                Field("Because", card.because)
                if (card.looksLike.isNotEmpty()) Field("Looks like", card.looksLike.joinToString("\n") { "•  $it" })
                Field("Drift looks like", card.driftLooksLike, Palette.HoneyDeep)
                Field(if (subject.startsWith("We")) "In conflict, we prioritise" else "In conflict, I prioritise", card.inConflict)
                Field("Never", card.neverDo, MaterialTheme.colorScheme.error)
            }
            ValueCardStateRow(card, actions, busy)
            if (expanded) {
                card.id?.let { id ->
                    val navigator = LocalNavigator.current
                    LinkText("See it on the Meaning Graph", { navigator.meaningGraph(card = id) })
                }
            }
            MetaText(if (expanded) "▲ Less" else "▼ More")
        }
    }

    if (confirmDelete && actions != null) {
        AlertDialog(
            onDismissRequest = { confirmDelete = false },
            title = { Text("Remove this card?") },
            text = { Text("“${card.title.ifBlank { "Untitled value" }}” leaves the Meaning Graph. Receipts that named it keep their copy.") },
            confirmButton = { TextButton(onClick = { confirmDelete = false; actions.onDelete(card) }) { Text("Remove") } },
            dismissButton = { TextButton(onClick = { confirmDelete = false }) { Text("Keep") } },
        )
    }
}

/**
 * CLEAR's E and R: a card is endorsed by a deliberate, reflective step apart from writing it, and
 * reviewed on a cadence (the server flags it after 90 days). Buttons only for whoever may act.
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
fun ValueCardStateRow(card: ValueCard, actions: ValueCardActions?, busy: Boolean) {
    // Draft, endorsed and due-for-review are Advanced's.
    if (LocalSimple.current) return
    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        if (card.endorsed == true) {
            val on = Dates.monthYear(card.endorsedAt)
            Pill("✓ Endorsed" + if (on.isNotEmpty()) " · $on" else "", Brand.colors.doneWash, Brand.colors.onDoneWash)
        } else if (card.endorsed == false) {
            QuietPill("Draft")
        }
        if (card.needsReview) Pill("Due for review", Brand.colors.needWash, Brand.colors.onNeedWash)
        if (actions != null && card.endorsed == false) {
            OutlinedButton(onClick = { actions.onEndorse(card) }, enabled = !busy) { Text("Endorse on reflection") }
        }
        if (actions != null && card.endorsed == true && card.needsReview) {
            OutlinedButton(onClick = { actions.onReview(card) }, enabled = !busy) { Text("Still holds — mark reviewed") }
        }
        if (actions != null && card.endorsed == true && !card.needsReview) {
            val on = Dates.monthYear(card.reviewedAt)
            if (on.isNotEmpty()) QuietPill("Reviewed $on")
        }
    }
}

/** What Frankl's three modes mean, under a graph. */
@Composable
fun FranklLegend(modifier: Modifier = Modifier) {
    Column(modifier, verticalArrangement = Arrangement.spacedBy(2.dp)) {
        MetaText("✶ Creative — what you make & give")
        MetaText("❍ Experiential — what you receive & encounter")
        MetaText("△ Attitudinal — the stance you take under constraint")
    }
}

@Composable
private fun Field(label: String, text: String?, tint: Color = MaterialTheme.colorScheme.onSurfaceVariant) {
    if (text.isNullOrBlank()) return
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Text(label.uppercase(), style = MaterialTheme.typography.labelSmall, color = tint)
        Text(text, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurface)
    }
}
