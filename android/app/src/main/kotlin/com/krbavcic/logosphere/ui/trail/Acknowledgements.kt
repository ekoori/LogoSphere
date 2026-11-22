package com.krbavcic.logosphere.ui.trail

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.listSaver
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.runtime.toMutableStateList
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.krbavcic.logosphere.core.logic.Dates
import com.krbavcic.logosphere.core.model.Acknowledgement
import com.krbavcic.logosphere.core.model.Exchange
import com.krbavcic.logosphere.core.model.MeaningTrail
import com.krbavcic.logosphere.core.model.ValueCard
import com.krbavcic.logosphere.core.model.ReportOf
import com.krbavcic.logosphere.ui.common.ReportLink
import com.krbavcic.logosphere.ui.LocalAppContainer
import com.krbavcic.logosphere.ui.LocalNavigator
import com.krbavcic.logosphere.ui.common.Avatar
import com.krbavcic.logosphere.ui.common.EmptyNote
import com.krbavcic.logosphere.ui.common.ExchangeCard
import com.krbavcic.logosphere.ui.common.LikeControl
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.PersonaTag
import com.krbavcic.logosphere.ui.common.ValueChip
import com.krbavcic.logosphere.ui.common.ValueChips
import com.krbavcic.logosphere.ui.theme.Brand
import kotlin.coroutines.cancellation.CancellationException

private const val MAX_WORDS = 1000

/** What a screen's ViewModel does with acknowledgements (LoadViewModel makes one). */
interface AcknowledgementActions {
    fun add(trailId: String, text: String, cardIds: List<String>, onDone: () -> Unit)
    fun like(ack: Acknowledgement)
    fun highlight(ack: Acknowledgement)
    fun remove(ack: Acknowledgement)
}

/** Whose cards an acknowledgement may also name: their id, and a label for the group of chips. */
data class CardOwner(val id: String, val label: String)

/** A whole Meaning Trail: the button, then exchanges and runs of acknowledgements as they happened. */
fun LazyListScope.trailItems(
    trail: MeaningTrail,
    viewerId: String?,
    actions: AcknowledgementActions,
    busy: Boolean,
    empty: String,
    onExchange: (Exchange) -> Unit,
    onLike: (Exchange) -> Unit,
    modifier: Modifier = Modifier,
) {
    if (trail.canAcknowledge) {
        item(key = "ack-add-${trail.id}") {
            val others = if (trail.id == viewerId) emptyList() else listOf(CardOwner(trail.id, "${trail.name}'s values"))
            AcknowledgeButton(trail.id, others, actions, busy, modifier)
        }
    }
    if (trail.entries.isEmpty()) item(key = "trail-empty") { EmptyNote(empty) }
    items(trail.entries, key = { "${it.type}-${it.id}" }) { entry ->
        val exchange = entry.exchange
        if (exchange != null) {
            ExchangeCard(exchange, viewerId, onClick = { onExchange(exchange) }, onLike = { onLike(exchange) }, modifier = modifier)
        } else {
            AcknowledgementRun(entry.items, viewerId, actions, busy, modifier)
        }
    }
}

/** Consecutive acknowledgements: three or more fold to the highlighted ones (else the newest). */
@Composable
fun AcknowledgementRun(
    items: List<Acknowledgement>,
    viewerId: String?,
    actions: AcknowledgementActions,
    busy: Boolean,
    modifier: Modifier = Modifier,
) {
    var open by rememberSaveable { mutableStateOf(false) }
    val hidden = items.count { !it.shown }
    val visible = if (open) items else items.filter { it.shown }
    val honey = Brand.colors.acknowledgementAccent
    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.medium,
        color = honey.copy(alpha = 0.07f),
        border = BorderStroke(1.dp, honey.copy(alpha = 0.35f)),
    ) {
        Column {
            visible.forEachIndexed { index, ack ->
                if (index > 0) HorizontalDivider(color = honey.copy(alpha = 0.25f))
                AcknowledgementRow(ack, viewerId, actions, busy)
            }
            if (hidden > 0) {
                HorizontalDivider(color = honey.copy(alpha = 0.25f))
                TextButton(onClick = { open = !open }, modifier = Modifier.padding(horizontal = 6.dp)) {
                    Text(if (open) "Show fewer" else "$hidden more acknowledgement${if (hidden == 1) "" else "s"}")
                }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun AcknowledgementRow(ack: Acknowledgement, viewerId: String?, actions: AcknowledgementActions, busy: Boolean) {
    val navigator = LocalNavigator.current
    var confirmRemove by remember { mutableStateOf(false) }
    val mine = ack.authorId != null && ack.authorId == viewerId
    val author = if (mine) "You" else ack.authorName ?: "A member"
    Surface(color = Brand.colors.acknowledgementAccent.copy(alpha = if (ack.highlighted) 0.17f else 0f)) {
        Row(
            Modifier.fillMaxWidth().padding(start = 12.dp, end = 12.dp, top = 12.dp, bottom = 4.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Avatar(ack.authorId, ack.authorName, size = 32.dp)
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(
                        author,
                        style = MaterialTheme.typography.titleSmall,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier
                            .weight(1f, fill = false)
                            .clickable(enabled = ack.authorId != null) { ack.authorId?.let(navigator::person) },
                    )
                    if (ack.authorIsAgent) PersonaTag(compact = true)
                    MetaText(Dates.day(ack.createdAt))
                }
                if (ack.highlighted) {
                    Text("★ Highlighted", style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
                }
                Text(ack.text, style = MaterialTheme.typography.bodyLarge)
                if (ack.cards.isNotEmpty()) ValueChips(ack.cards)
                FlowRow(horizontalArrangement = Arrangement.spacedBy(2.dp)) {
                    LikeControl(ack.likes, { actions.like(ack) })
                    if (ack.canHighlight) {
                        TextButton(onClick = { actions.highlight(ack) }, enabled = !busy) {
                            Text(if (ack.highlighted) "Remove highlight" else "☆ Highlight")
                        }
                    }
                    if (ack.canRemove) TextButton(onClick = { confirmRemove = true }, enabled = !busy) { Text("Remove") }
                    if (!mine && ack.authorId != null) ReportLink(ReportOf.acknowledgement(ack.id, ack.trailId))
                }
            }
        }
    }
    if (confirmRemove) {
        AlertDialog(
            onDismissRequest = { confirmRemove = false },
            title = { Text("Remove this acknowledgement?") },
            text = { Text("It goes for everyone, with its appreciations.") },
            confirmButton = { TextButton(onClick = { confirmRemove = false; actions.remove(ack) }) { Text("Remove") } },
            dismissButton = { TextButton(onClick = { confirmRemove = false }) { Text("Keep it") } },
        )
    }
}

/** The button that opens the form: a few words, and the value cards they express. */
@OptIn(ExperimentalLayoutApi::class)
@Composable
fun AcknowledgeButton(
    trailId: String,
    others: List<CardOwner>,
    actions: AcknowledgementActions,
    busy: Boolean,
    modifier: Modifier = Modifier,
) {
    var open by rememberSaveable(trailId) { mutableStateOf(false) }
    if (!open) {
        OutlinedButton(onClick = { open = true }, modifier = modifier.fillMaxWidth()) { Text("+ Add acknowledgement") }
        return
    }
    val app = LocalAppContainer.current
    val me = app.session.user?.id
    var text by rememberSaveable(trailId) { mutableStateOf("") }
    val selected = rememberSaveable(
        trailId,
        saver = listSaver(save = { it.toList() }, restore = { it.toMutableStateList() }),
    ) { mutableStateListOf<String>() }
    var groups by remember(trailId) { mutableStateOf(emptyList<Pair<String, List<ValueCard>>>()) }
    LaunchedEffect(trailId) {
        val owners = listOfNotNull(me?.let { CardOwner(it, "Your values") }) + others.filter { it.id != me }
        val found = mutableListOf<Pair<String, List<ValueCard>>>()
        for (owner in owners.distinctBy { it.id }) {
            val cards = try {
                app.api.valueCards(owner.id)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                emptyList() // their cards aren't to be seen, or didn't load: the words still can be sent
            }
            if (cards.isNotEmpty()) found += owner.label to cards
        }
        groups = found
    }

    Column(modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        OutlinedTextField(
            value = text,
            onValueChange = { text = it.take(MAX_WORDS) },
            placeholder = { Text("What do you want to acknowledge?") },
            keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences),
            modifier = Modifier.fillMaxWidth().heightIn(min = 110.dp),
        )
        if (groups.isNotEmpty()) Text("Which values does it express?", style = MaterialTheme.typography.labelLarge)
        groups.forEach { (label, cards) ->
            MetaText(label)
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                cards.forEach { card ->
                    val id = card.id ?: return@forEach
                    ValueChip(card, selected = id in selected, onClick = {
                        if (id in selected) selected.remove(id) else selected.add(id)
                    })
                }
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(
                onClick = {
                    actions.add(trailId, text, selected.toList()) {
                        text = ""
                        selected.clear()
                        open = false
                    }
                },
                enabled = text.isNotBlank() && !busy,
            ) { Text("Acknowledge") }
            TextButton(onClick = { open = false }) { Text("Cancel") }
        }
    }
}
