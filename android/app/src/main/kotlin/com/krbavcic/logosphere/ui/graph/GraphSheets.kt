package com.krbavcic.logosphere.ui.graph

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.RectangleShape
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.krbavcic.logosphere.core.logic.GraphView
import com.krbavcic.logosphere.core.model.ClosenessMethod
import com.krbavcic.logosphere.core.model.FieldWeight
import com.krbavcic.logosphere.core.model.FranklMode
import com.krbavcic.logosphere.core.model.GraphEdge
import com.krbavcic.logosphere.core.model.GraphNode
import com.krbavcic.logosphere.core.model.GraphOwner
import com.krbavcic.logosphere.ui.Load
import com.krbavcic.logosphere.ui.common.DemoTag
import com.krbavcic.logosphere.ui.common.LinkText
import com.krbavcic.logosphere.ui.common.LoadContent
import com.krbavcic.logosphere.ui.common.MetaText
import com.krbavcic.logosphere.ui.common.PersonaTag
import com.krbavcic.logosphere.ui.common.SectionHeading
import com.krbavcic.logosphere.ui.theme.Brand
import com.krbavcic.logosphere.ui.common.LocalSimple

/** A node as the legend and the lists show it: its colour, a circle or a square. */
@Composable
internal fun MeaningDot(mode: FranklMode, group: Boolean, modifier: Modifier = Modifier) {
    Box(
        modifier
            .size(11.dp)
            .clip(if (group) RectangleShape else CircleShape)
            .background(Brand.colors.meaning(mode)),
    )
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
internal fun GraphLegend(modifier: Modifier = Modifier) {
    FlowRow(modifier, horizontalArrangement = Arrangement.spacedBy(12.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
        FranklMode.entries.forEach { mode ->
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                MeaningDot(mode, group = false)
                MetaText("${mode.glyph} ${mode.label}")
            }
        }
        MetaText("Circle: a person's")
        MetaText("Square: a group's")
        MetaText("Bigger: more connections")
    }
}

/** A chosen card: what it is close to, why (every part of the score), and the member's say on it. */
@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
internal fun GraphDetailsSheet(
    node: GraphNode,
    edges: List<GraphEdge>,
    byId: Map<String, GraphNode>,
    focused: Boolean,
    busy: Boolean,
    onSelect: (String) -> Unit,
    onFocus: (String?) -> Unit,
    onReadCard: () -> Unit,
    onOwner: (GraphOwner) -> Unit,
    onJudge: (GraphEdge, Boolean) -> Unit,
    onDismiss: () -> Unit,
) {
    val closest = remember(node.id, edges) { GraphView.closestTo(node.id, edges) }
    var why by remember(node.id) { mutableStateOf<String?>(null) }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = false),
        containerColor = MaterialTheme.colorScheme.surfaceContainerLow,
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp)
                .padding(bottom = 24.dp)
                .navigationBarsPadding(),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                MeaningDot(node.mode, node.owner.isGroup)
                MetaText("${node.mode.glyph} ${node.mode.label}")
            }
            Text(node.title, style = MaterialTheme.typography.headlineSmall, color = MaterialTheme.colorScheme.onSurface)
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                LinkText(node.owner.name, { onOwner(node.owner) }, Modifier.weight(1f, fill = false))
                if (node.owner.isAgent) PersonaTag(compact = true) else if (node.isDemo) DemoTag()
            }
            node.card.careAbout?.takeIf { it.isNotBlank() && it != node.title }?.let {
                Text(it, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurface)
            }
            FlowRow(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                LinkText("Read the whole card", onReadCard)
                LinkText(if (focused) "Show everything" else "Only this and its neighbours", { onFocus(if (focused) null else node.id) })
            }

            SectionHeading("Closest")
            if (closest.isEmpty()) MetaText("Nothing is this close to it yet.")
            closest.forEach { edge ->
                val otherId = edge.other(node.id)
                val other = byId[otherId] ?: return@forEach
                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(
                        Modifier
                            .weight(1f)
                            .heightIn(min = 48.dp)
                            .clickable(role = Role.Button) { onSelect(otherId) }
                            .padding(vertical = 6.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        MeaningDot(other.mode, other.owner.isGroup)
                        Column {
                            Text(other.title, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurface)
                            MetaText(other.owner.name)
                        }
                    }
                    Text(
                        GraphView.percent(edge.closeness),
                        style = MaterialTheme.typography.labelLarge,
                        color = MaterialTheme.colorScheme.onSurface,
                    )
                    TextButton(onClick = { why = if (why == otherId) null else otherId }) {
                        Text(if (why == otherId) "Hide" else "Why?")
                    }
                }
                if (why == otherId) Why(edge, node, other, busy, onJudge)
            }
        }
    }
}

@Composable
private fun Part(label: String, value: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            label,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.weight(1f),
        )
        Text(value, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.SemiBold, color = MaterialTheme.colorScheme.onSurface)
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun Why(edge: GraphEdge, node: GraphNode, other: GraphNode, busy: Boolean, onJudge: (GraphEdge, Boolean) -> Unit) {
    Column(
        Modifier
            .fillMaxWidth()
            .clip(MaterialTheme.shapes.small)
            .background(MaterialTheme.colorScheme.surfaceContainerHigh)
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(5.dp),
    ) {
        Part("Same words", GraphView.percent(edge.words))
        edge.shared.forEach { word ->
            val here = if (edge.a == node.id) word.here else word.there
            val there = if (edge.a == node.id) word.there else word.here
            val family = if (word.family) " (counted as ${word.countsAs})" else ""
            // Not ↔, which phones draw as an emoji.
            MetaText("${here.joinToString(", ")} ≈ ${there.joinToString(", ")}$family", maxLines = 3)
        }
        val simple = LocalSimple.current
        if (!simple || edge.people > 0) Part("Lived together", if (edge.people > 0) "${edge.people} people" else "not yet")
        if (edge.lineage) Part("One was made from the other", "yes")
        if (!simple || edge.judges > 0) {
            Part("People's judgement", if (edge.judges > 0) "${edge.saidClose} of ${edge.judges} say close" else "fewer than 2 so far")
        }

        if (simple) return@Column
        if (node.canJudge && other.canJudge) {
            Text(
                "Do these two feel close to you?",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface,
            )
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                JudgementButton("Close", edge.myJudgement == true, busy) { onJudge(edge, true) }
                JudgementButton("Not close", edge.myJudgement == false, busy) { onJudge(edge, false) }
            }
            if (edge.myJudgement != null && edge.judges == 0) {
                MetaText("Saved. It counts once a second person has judged this pair.", maxLines = 2)
            }
        } else {
            MetaText("One of these is yours, so others judge this pair.", maxLines = 2)
        }
    }
}

@Composable
private fun JudgementButton(label: String, chosen: Boolean, busy: Boolean, onClick: () -> Unit) {
    if (chosen) {
        Button(onClick = onClick, enabled = !busy) { Text("✓ $label") }
    } else {
        OutlinedButton(onClick = onClick, enabled = !busy) { Text(label) }
    }
}

/** The whole method, as the server publishes it. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun MethodSheet(method: Load<ClosenessMethod>, onRetry: () -> Unit, onDismiss: () -> Unit) {
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
        containerColor = MaterialTheme.colorScheme.surfaceContainerLow,
    ) {
        LoadContent(method, onRetry, Modifier.heightIn(max = 280.dp)) { MethodText(it) }
    }
}

@Composable
private fun Plain(text: String) {
    Text(text, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurface)
}

@Composable
private fun MethodText(m: ClosenessMethod) {
    val uri = LocalUriHandler.current
    var families by remember { mutableStateOf(false) }
    var stopWords by remember { mutableStateOf(false) }
    Column(
        Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp)
            .padding(bottom = 24.dp)
            .navigationBarsPadding(),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text("How closeness is worked out", style = MaterialTheme.typography.headlineSmall)
        Plain(m.idea)
        SectionHeading("The whole formula")
        m.formula.forEachIndexed { i, line -> Plain("${i + 1}. $line") }
        SectionHeading("What counts")
        m.fields.forEach { Part(it.label, GraphView.percent(it.weight)) }
        MetaText(
            "Not counted: " + m.notCounted.joinToString("; ") { FieldWeight.labelOf(it).lowercase() } +
                ". Shared words there often mean disagreement.",
            maxLines = 4,
        )
        SectionHeading("What keeps it fair")
        m.rules.forEach { Plain("•  $it") }
        Plain("Never counted: ${m.neverInputs.joinToString(", ")}.")
        SectionHeading("Where it falls short")
        m.limits.forEach { Plain("•  $it") }
        LinkText("The ${m.families.size} word families (words that count as one)", { families = !families })
        if (families) m.families.forEach { (name, words) -> Plain("$name: ${words.joinToString(", ")}") }
        LinkText("The ${m.stopWords.size} words that don't count", { stopWords = !stopWords })
        if (stopWords) Plain(m.stopWords.joinToString(", "))
        SectionHeading("It builds on")
        m.sources.forEach { source -> LinkText(source.title, { uri.openUri(source.url) }) }
        MetaText("Their moral graph links wiser values and has no measure of distance, so this measure is LogoSphere's own.", maxLines = 3)
    }
}
